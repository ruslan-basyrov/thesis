.PHONY: dev extension render preview word_count fclean

DOCUMENT = index.qmd

QUARTO = uv run quarto

EXTENSION = _extensions/ruslan-basyrov

WORDCOUNT = $(EXTENSION)/acuity/wordcount.lua

WORDS_MIN ?= 20000
WORDS_MAX ?= 30000
WORDS_FILE ?= build/wordcount.txt

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

BUILD_ARTIFACTS = _acuity _extensions .quarto .venv build index_files \
	site_libs $(DOCUMENT:.qmd=.typ)

fclean:
	rm -rf $(BUILD_ARTIFACTS)
