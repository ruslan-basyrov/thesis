.PHONY: dev extension render preview fclean

DOCUMENT = index.qmd

QUARTO = uv run quarto

export DAGSTER_HOME := $(CURDIR)/.dagster

MATERIALIZE = uv run dagster asset materialize -m pipeline.definitions --select

$(DAGSTER_HOME):
	mkdir -p $@

dev: | $(DAGSTER_HOME)
	uv run dagster dev -m pipeline.definitions

extension: | $(DAGSTER_HOME)
	$(MATERIALIZE) extension

render: | $(DAGSTER_HOME)
	$(MATERIALIZE) extension,ess_clean,gradient,figures,document

preview: extension
	$(QUARTO) preview $(DOCUMENT)

BUILD_ARTIFACTS = _acuity _extensions .quarto .venv build index_files \
	site_libs $(DOCUMENT:.qmd=.typ)

fclean:
	rm -rf $(BUILD_ARTIFACTS)
