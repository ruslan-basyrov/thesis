import subprocess

from pipeline.filepaths import PRERENDER, QUARTO_YML, ROOT


def quarto(*args):
    subprocess.run(["quarto", *args], cwd=ROOT, check=True)


def install_extension():
    # the installation fails if _quarto.yml file is present —
    # thus, the renaming of the file
    hidden = QUARTO_YML.with_name("quarto.yml")
    QUARTO_YML.rename(hidden)
    try:
        quarto("add", "ruslan-basyrov/acuity", "--no-prompt")
    finally:
        hidden.rename(QUARTO_YML)


def prerender_figures():
    quarto("run", PRERENDER)


def render_document():
    quarto("render")
