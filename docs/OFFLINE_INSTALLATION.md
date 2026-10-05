# Offline Installation

## Dependency Policy

Production dependencies are pinned exactly in `requirements-runtime.txt` and include the full transitive closure. Development/test tools are separate. The release wheelhouse is generated for the target RHEL architecture and Python minor version; Python wheels are not assumed portable across every ABI/platform. The install set is hashed and transferred through the organization's approved artifact channel. Production installation never contacts PyPI.

Runtime pins are pg8000 1.31.5, PyYAML 6.0.2, scramp 1.4.6, asn1crypto 1.5.1, python-dateutil 2.9.0.post0, and six 1.17.0. The scramp pin is deliberately 1.4.6 because 1.4.17 requires Python 3.10+, while this package declares Python >=3.9. A CPython 3.9 `manylinux2014_x86_64` wheel resolution succeeded; the RHEL runtime itself has not yet been exercised.

## Connected Staging Host

Use a Python interpreter matching the target RHEL version/architecture and a clean virtual environment. Download exact pinned requirements and all dependencies:

```sh
python3 -m venv .venv
.venv/bin/python -m pip download --only-binary=:all: --dest wheelhouse -r requirements-runtime.txt
.venv/bin/python -m pip download --only-binary=:all: --dest wheelhouse -r requirements-dev.txt
shasum -a 256 wheelhouse/* > SHA256SUMS
```

Create a SHA-256 manifest for every artifact and verify package metadata/dependency closure. Transfer `SHA256SUMS` alongside the wheelhouse, then verify with `shasum -a 256 -c SHA256SUMS` from the directory containing the downloaded wheels. If a dependency has no compatible wheel for the target, build/wheel it on a compatible staging host; do not fall back to runtime downloads. Do not mix development dependencies into production's install command.

## Transfer and Install

Transfer the source release, runtime wheelhouse, and manifest using approved media. Verify the manifest before installation. Install with network access disabled and dependency resolution constrained to local artifacts:

```sh
shasum -a 256 -c SHA256SUMS
python3 -m venv /opt/dbeeapp/venv
/opt/dbeeapp/venv/bin/python -m pip install --no-index --find-links ./wheelhouse --requirement requirements-runtime.txt
/opt/dbeeapp/venv/bin/python -m pip install --no-index --no-deps ./DBeeApp-*.whl
```

Verify installed versions using `pip list --format=freeze` and a CLI version invocation. Do not copy a virtual environment from another host; recreate it on the target interpreter.

For an offline developer build, stage the pinned development closure too, install `requirements-dev.txt` from the local wheelhouse, then run `.venv/bin/python -m build --no-isolation`. The production wheelhouse does not contain build/test dependencies.

## Verify and Operate

Test the installation with `dbeeapp version`, `validate`, and `describe` against test templates, then run a controlled test database workflow. Verify TLS trust files, provider directory permissions, and no-network operation. Keep the manifest, interpreter/platform identity, and source release checksum with deployment records.
