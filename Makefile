.PHONY: dev extension render preview word_count publish fclean

DOCUMENT = index.qmd

QUARTO = uv run quarto

EXTENSION = _extensions/ruslan-basyrov

WORDCOUNT = $(EXTENSION)/acuity/wordcount.lua

WORDS_MIN ?= 20000
WORDS_MAX ?= 30000
WORDS_FILE ?= build/wordcount.txt

SITE = _acuity
SITE_TAR = build/site.tar.gz
RELEASE = site

export DAGSTER_HOME := $(CURDIR)/.dagster

MATERIALIZE = uv run dagster asset materialize -m pipeline.definitions --select

$(DAGSTER_HOME):
	mkdir -p $@

dev: | $(DAGSTER_HOME)
	uv run dagster dev -m pipeline.definitions

extension: | $(DAGSTER_HOME)
	$(MATERIALIZE) extension

$(EXTENSION): | $(DAGSTER_HOME)
	$(MATERIALIZE) extension

render: | $(DAGSTER_HOME)
	$(MATERIALIZE) extension,ess_clean,tertiary_difference,figures,document

preview: | $(EXTENSION)
	$(QUARTO) preview $(DOCUMENT)

# Plain `html`, not `acuity-html`: the Acuity filters move captions and
# references into the margin, which would count them as margin text.
word_count: | $(EXTENSION)
	@mkdir -p $(dir $(WORDS_FILE))
	@$(QUARTO) render $(DOCUMENT) --to html --quiet \
		-M "filters:[$(WORDCOUNT)]" \
		-M "wordcount-min:$(WORDS_MIN)" \
		-M "wordcount-max:$(WORDS_MAX)" \
		-M "wordcount-report:$(WORDS_FILE)" \
		-o wordcount.html
	@cat $(WORDS_FILE)

# The site is rendered here and handed to the workflow that deploys it, so
# the data it is built from stays off GitHub. One release asset, replaced
# every time.
publish: render
	@mkdir -p $(dir $(SITE_TAR))
	tar -czf $(SITE_TAR) -C $(SITE) .
	@gh release view $(RELEASE) >/dev/null 2>&1 || \
		gh release create $(RELEASE) --title "Built site" \
			--notes "The rendered site, replaced by every publish."
	gh release upload $(RELEASE) $(SITE_TAR) --clobber
	gh workflow run publish.yml

BUILD_ARTIFACTS = _acuity _extensions .quarto .venv build index_files \
	site_libs $(DOCUMENT:.qmd=.typ)

fclean:
	rm -rf $(BUILD_ARTIFACTS)
