# Repository Guidelines

## Project Structure & Module Organization
Core scripts live in the repo root: `main.py` exposes the CLI, `translate.py` hosts `TranslationPipeline`, and `export_to_excel.py`/`import_from_excel.py` drive the Excel QC loop. Place raw Japanese JSON inside `raw_umatl/`, translated output in `slop/`, and shared assets (`dictionary.json`, `config.toml`, `example.json`) beside the code for versioning. Keep diagnostics such as `test_setup.py` and any future suites inside a `tests/` package, and leave large generated artifacts (Excel exports, ad-hoc dumps) ignored by Git.

## Build, Test, and Development Commands
- `uv sync` (preferred) or `pip install -r requirements.txt` installs the dependencies declared in `pyproject.toml`/`uv.lock`.
- `uv run python main.py` starts the interactive menu; add `--translate`, `--export`, `--import-qc`, or `--workflow` to jump directly into a stage.
- `uv run python main.py --workflow` performs translation plus Excel export in one go; pair it with `--import-qc` after reviewers edit the QC column.
- `python test_setup.py` verifies dependencies, config integrity, folder layout, and optionally the LLM endpoint before long runs.

## Coding Style & Naming Conventions
Target Python 3.12, four-space indentation, and snake_case names. Keep logic scoped to its module (pipeline in `translate.py`, Excel helpers in their files) and name orchestration classes with `Pipeline`, `Exporter`, or `Importer` suffixes. Annotate public methods with type hints, document network or filesystem side effects, and run `python -m black .` plus (if available) `ruff check .` before committing.

## Testing Guidelines
Today the lightweight gate is `test_setup.py`; run it whenever `config.toml`, `dictionary.json`, or IO paths change and paste its summary into PRs that touch configuration. When adding automated coverage, use `pytest` with files named `test_<module>.py`, keep fixtures under `tests/data/`, and mock the LLM call site (e.g., via `requests-mock`) so suites run offline.

## Commit & Pull Request Guidelines
Follow the existing `<type>: <summary>` convention from `git log` (`feature: allow tunable top_p`). Keep summaries under ~60 characters, reference related issues, and describe dictionary/config edits explicitly. Each PR should list the commands exercised (`uv run python main.py --workflow`, `python test_setup.py`, etc.) and attach screenshots or console snippets for translation/QC changes.

## Configuration & Security Tips
API URLs and keys belong only in `config.toml`; never hard-code them or commit personal copies. Generated assets like `translations.xlsx` and temporary JSON exports stay untracked (update `.gitignore` if new artifacts appear). When sharing logs, redact proprietary dictionary terms or LM Studio endpoints, and document every new config option in both `README.md` and this guide to keep contributors aligned.