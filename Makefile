.PHONY: dev couples extension render preview fclean

DOCUMENT = index.qmd

QUARTO = uv run quarto

export DAGSTER_HOME := $(CURDIR)/.dagster

MATERIALIZE = uv run dagster asset materialize -m pipeline.definitions --select

$(DAGSTER_HOME):
	mkdir -p $@

dev: | $(DAGSTER_HOME)
	uv run dagster dev -m pipeline.definitions

couples: | $(DAGSTER_HOME)
	$(MATERIALIZE) couples

extension: | $(DAGSTER_HOME)
	$(MATERIALIZE) extension

render: | $(DAGSTER_HOME)
	$(MATERIALIZE) extension,document

preview: extension
	$(QUARTO) preview $(DOCUMENT)

BUILD_ARTIFACTS = _acuity _extensions .quarto .venv build index_files \
	site_libs $(DOCUMENT:.qmd=.typ)

fclean:
	rm -rf $(BUILD_ARTIFACTS)
