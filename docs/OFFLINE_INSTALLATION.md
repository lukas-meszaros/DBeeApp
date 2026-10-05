# Local Runtime Libraries

## Runtime Policy

DBeeApp does not install runtime Python libraries into the interpreter, a virtual environment, or system `site-packages`. The application source includes the pure-Python modules it needs under `dbeeapp/_vendor`, plus upstream license texts and wheel metadata. `dbeeapp/__init__.py` puts that local directory first on `sys.path` before importing the CLI or database stack.

The runtime pins are pg8000 1.31.5, PyYAML 6.0.2, scramp 1.4.6, asn1crypto 1.5.1, python-dateutil 2.9.0.post0, and six 1.17.0. PyYAML's optional compiled extension is excluded; its pure-Python implementation is used. Tests run with Python's `-S` option to prove runtime imports do not depend on installed packages.

`requirements-runtime.txt` is a source-wheel acquisition manifest for maintainers. It is not an installation requirements file and must not be passed to `pip install`.

## Refresh the Vendor Tree

On a connected staging workstation, download wheels into a local wheelhouse. `pip download` only saves archives; it does not install the packages:

```sh
python3 -m pip download --only-binary=:all: --dest wheelhouse -r requirements-runtime.txt
python3 tools/vendor_runtime.py --wheelhouse wheelhouse
```

The vendor tool requires exactly one wheel for each pinned distribution, extracts only package source, `.dist-info` version metadata, and license files, and discards native extensions. It does not invoke pip or perform network access. Review the generated diff and upstream licenses after any refresh. Run:

```sh
python3 -S -m dbeeapp version
python3 -S -m unittest discover -s tests -v
```

Build/test front-end tool pins are recorded separately under `requirements-dev.txt`; they are not runtime imports and are not needed to run tests. A release builder may use its pre-provisioned packaging tools, but the target application does not install Python libraries.

## Transfer and Run

Transfer the source release (including `dbeeapp/_vendor`) through the approved channel. No wheelhouse or internet connection is required on the target. Use a supported Python interpreter and run directly from the application source directory:

```sh
python3 -S -m dbeeapp version
python3 -S -m dbeeapp validate examples/basic_query/job.yaml
python3 -S -m dbeeapp describe examples/basic_query/job.yaml
python3 -S -m dbeeapp run examples/basic_query/job.yaml
```

`-S` is optional in normal use; it disables site initialization and is useful for verifying that runtime packages are sourced only from the bundled vendor directory. Do not copy a Python virtual environment between machines. Place the application/provider files in administrator-controlled locations and configure the approved provider directory.

The vendored tree is interpreter-independent pure Python. CPython 3.9 manylinux wheel availability and local macOS Python 3.13 runtime execution have been checked; an actual RHEL host remains to be certified.