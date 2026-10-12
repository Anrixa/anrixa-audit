# First release: exact procedure

The repository is designed to be published as `Anrixa/anrixa-audit` and the PyPI project as `anrixa-audit`.

## 1. Create and push the GitHub repository

On Windows PowerShell 5.1, from the extracted project directory:

```powershell
Get-FileHash .\scripts\bootstrap-github.ps1 -Algorithm SHA256
Unblock-File .\scripts\bootstrap-github.ps1
& .\scripts\bootstrap-github.ps1
```

The script:

- verifies GitHub CLI authentication;
- initializes `main` if needed;
- commits the complete repository;
- creates `Anrixa/anrixa-audit` as a public repository when it does not exist;
- refuses to silently replace an unexpected existing `origin`;
- pushes `main`.

## 2. Verify GitHub CI

Open the repository Actions page and require the `ci` workflow to pass.

The workflow tests Python 3.10, 3.13, and 3.14 and separately builds the wheel/sdist and checks their package metadata.

Do not create the first release if CI is red.

## 3. Create the PyPI Trusted Publisher

Use PyPI's Trusted Publisher configuration. For a project that does not yet exist, create a **pending publisher** with:

| Field | Value |
|---|---|
| PyPI project | `anrixa-audit` |
| GitHub owner | `Anrixa` |
| Repository | `anrixa-audit` |
| Workflow filename | `release.yml` |
| Environment | `pypi` |

The repository workflow requests `id-token: write` only for the publishing job. No PyPI API token is stored in GitHub.

## 4. Configure the GitHub `pypi` environment

In `Anrixa/anrixa-audit`:

**Settings → Environments → New environment → `pypi`**

For the first release, add a required reviewer if you want a manual approval gate immediately before upload.

## 5. Create the v0.1.0 release

After CI is green:

```powershell
git status --short
git pull --ff-only origin main
git tag -a v0.1.0 -m "anrixa-audit 0.1.0"
git push origin v0.1.0
```

Then create a GitHub Release for the exact `v0.1.0` tag.

Publishing happens only when the GitHub Release is published. The release workflow re-runs the tests, verifies `v0.1.0` matches `project.version = "0.1.0"`, builds and inspects the distributions, then sends the verified artifacts to PyPI through OIDC.

## 6. Verify PyPI

After the workflow is green:

```powershell
py -3.13 -m venv "$env:TEMP\anrixa-audit-pypi-test"
& "$env:TEMP\anrixa-audit-pypi-test\Scripts\python.exe" -m pip install --upgrade pip
& "$env:TEMP\anrixa-audit-pypi-test\Scripts\python.exe" -m pip install anrixa-audit==0.1.0
& "$env:TEMP\anrixa-audit-pypi-test\Scripts\anrixa-audit.exe" --version
```

Expected final line:

```text
anrixa-audit 0.1.0
```
