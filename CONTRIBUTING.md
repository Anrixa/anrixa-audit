# Contributing

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev]'
python -m pytest
```

## Rules

- Keep the runtime dependency-free unless a dependency is clearly justified.
- Add focused tests for every behavior change.
- Preserve backwards compatibility for published v1 evidence schemas within a major version.
- Avoid automatic network activity.
- Treat path handling as security-sensitive.
- Update `CHANGELOG.md` for externally visible behavior.
- Do not include credentials, private data, or customer data in tests, issues, or commits.

Before opening a pull request:

```bash
python -m pytest
python -m build
python -m twine check dist/*
```
