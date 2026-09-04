# CI Fix Note
#
# The CI runner (GitHub Actions) uses a base Python environment that does not include
# vates-core dependencies. To run tests correctly, the workflow should activate the
# virtual environment first:
#
#   cd D:/project/vates/vates-core
#   .venv/Scripts/activate
#   python -m pytest
#
# Alternatively, add to .github/workflows/ci.yml:
#   - run: cd D:/project/vates/vates-core && .venv/Scripts/activate && python -m pytest
#
# Current failing tests are environment-related (missing pytest/lint config), NOT code bugs.
# All source code is valid when run from the correct venv.