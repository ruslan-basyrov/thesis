.PHONY: preview render update print fclean

DOCUMENT=index.qmd

QUARTO = uv run quarto

BUILD_ARTIFACTS = _acuity _extensions .quarto .venv build index_files \
	site_libs $(DOCUMENT:.qmd=.typ)

render: setup
	$(QUARTO) render $(DOCUMENT)
preview: setup
	$(QUARTO) preview $(DOCUMENT)

setup:
	uv sync
	mv _quarto.yml quarto.yml
	uv run quarto add ruslan-basyrov/acuity --no-prompt
	mv quarto.yml _quarto.yml

update:
	$(QUARTO) update ruslan-basyrov/acuity --no-prompt

fclean:
	rm -rf build $(BUILD_ARTIFACTS)
