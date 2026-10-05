"""Populate DBeeApp's local pure-Python runtime library directory from wheels."""

import argparse
from pathlib import Path, PurePosixPath
import shutil
import zipfile


PACKAGES = {
    "asn1crypto": ("asn1crypto",),
    "pg8000": ("pg8000",),
    "python-dateutil": ("dateutil",),
    "PyYAML": ("yaml",),
    "scramp": ("scramp",),
    "six": ("six.py",),
}
NATIVE_SUFFIXES = (".so", ".pyd", ".dylib")


def _source_bytes(data):
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    lines = [line.rstrip(" \t\r") for line in text.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    return ("\n".join(lines) + "\n").encode("utf-8")


def _metadata_bytes(data):
    """Keep only standard identity headers needed by importlib.metadata.version."""
    text = data.decode("utf-8")
    headers = []
    for line in text.splitlines():
        if not line:
            break
        if line.startswith(("Name:", "Version:")):
            headers.append(line.rstrip(" \t\r"))
    if len(headers) != 2:
        raise ValueError("wheel metadata is missing Name or Version")
    return ("\n".join(headers) + "\n\n").encode("utf-8")


def _wheel_for(wheelhouse, distribution, version):
    pattern = "{}-{}-*.whl".format(distribution.replace("-", "_"), version)
    matches = sorted(wheelhouse.glob(pattern))
    if len(matches) != 1:
        raise ValueError("expected exactly one local wheel matching {}, found {}".format(pattern, len(matches)))
    return matches[0]


def _safe_member(name):
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts


def vendor_runtime(wheelhouse, destination, replace=False):
    """Copy package Python files and license texts from exact local wheels."""
    wheelhouse = Path(wheelhouse).resolve()
    destination = Path(destination).resolve()
    if not wheelhouse.is_dir():
        raise ValueError("wheelhouse directory does not exist: {}".format(wheelhouse))
    if destination.exists() and not replace:
        raise ValueError("vendor destination already exists; pass --replace to regenerate it")
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    license_dir = destination / "licenses"
    license_dir.mkdir()
    versions = {
        "asn1crypto": "1.5.1",
        "pg8000": "1.31.5",
        "python-dateutil": "2.9.0.post0",
        "PyYAML": "6.0.2",
        "scramp": "1.4.6",
        "six": "1.17.0",
    }

    for distribution, roots in PACKAGES.items():
        wheel = _wheel_for(wheelhouse, distribution, versions[distribution])
        with zipfile.ZipFile(wheel) as archive:
            names = archive.namelist()
            package_members = []
            for name in names:
                path = PurePosixPath(name)
                if not _safe_member(name):
                    raise ValueError("unsafe wheel member path in {}".format(wheel.name))
                if (
                    any(name.endswith(suffix) for suffix in NATIVE_SUFFIXES)
                    or "__pycache__" in path.parts
                    or name.endswith(".pyc")
                ):
                    continue
                for root in roots:
                    if root.endswith(".py"):
                        matched = name == root
                    else:
                        matched = name.startswith(root + "/")
                    if matched and not name.endswith("/"):
                        package_members.append(name)
                        break
            for name in package_members:
                target = destination.joinpath(*PurePosixPath(name).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(_source_bytes(archive.read(name)))

            metadata_members = [
                name for name in names
                if ".dist-info/" in name and not name.endswith("/")
                and PurePosixPath(name).name != "RECORD"
            ]
            for name in metadata_members:
                if not _safe_member(name):
                    raise ValueError("unsafe wheel metadata path in {}".format(wheel.name))
                target = destination.joinpath(*PurePosixPath(name).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                data = archive.read(name)
                if PurePosixPath(name).name == "METADATA":
                    data = _metadata_bytes(data)
                target.write_bytes(_source_bytes(data))

            license_names = [
                name for name in names
                if "license" in PurePosixPath(name).name.lower()
                and ".dist-info/" in name
                and not name.endswith("/")
            ]
            if not license_names:
                raise ValueError("wheel has no license file: {}".format(wheel.name))
            for license_index, name in enumerate(license_names, 1):
                suffix = "-{}".format(license_index) if len(license_names) > 1 else ""
                target = license_dir / "{}-{}{}.txt".format(distribution, versions[distribution], suffix)
                target.write_bytes(_source_bytes(archive.read(name)))

    return destination


def main(argv=None):
    repo = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheelhouse", type=Path, default=repo / "wheelhouse")
    parser.add_argument("--destination", type=Path, default=repo / "dbeeapp" / "_vendor")
    parser.add_argument("--replace", action="store_true", help="replace an existing vendor destination")
    args = parser.parse_args(argv)
    try:
        target = vendor_runtime(args.wheelhouse, args.destination, replace=args.replace)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        parser.error(str(error))
    print("Vendored runtime libraries into {}".format(target))


if __name__ == "__main__":
    main()