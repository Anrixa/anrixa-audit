# Release procedure

## Preconditions

- `main` is clean and CI is green.
- `pyproject.toml` and `src/anrixa_audit/__init__.py` contain the same version.
- `CHANGELOG.md` contains the release entry.
- PyPI Trusted Publishing is configured for the `Anrixa/anrixa-audit` repository, `release.yml` workflow, and `pypi` environment.

## Local release gate

```bash
python -m pytest
rm -rf dist build src/*.egg-info
python -m build
python -m twine check dist/*
```

Do not upload local artifacts to PyPI. The authoritative publication path is GitHub Actions Trusted Publishing.

## Publish

1. Merge the release commit to `main`.
2. Create an annotated tag matching the package version, for example `v0.1.0`.
3. Push the tag.
4. Create a GitHub Release from that exact tag.
5. The `publish-pypi` workflow:
   - checks out the release tag;
   - verifies the tag matches `project.version`;
   - runs the test suite;
   - builds wheel and source distribution;
   - validates the distributions;
   - publishes to PyPI through OIDC Trusted Publishing.
6. Verify the PyPI project page, provenance/attestation, wheel, sdist, and installation from a clean environment.

## PyPI Trusted Publisher

Configure:

- PyPI project: `anrixa-audit`
- Owner: `Anrixa`
- Repository: `anrixa-audit`
- Workflow: `release.yml`
- Environment: `pypi`

For the first publication, PyPI supports a pending Trusted Publisher when the project does not yet exist.
