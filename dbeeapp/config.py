"""Strict application-level configuration and operational defaults."""

from pathlib import Path

from dbeeapp.errors import ConfigurationError
from dbeeapp.template_loader import load_yaml

_CONFIG_KEYS = {"provider_dir", "timeouts", "session", "postgresql", "results", "logging", "failures"}
_SECTIONS = {
    "timeouts": {"connect", "provider", "sql"},
    "session": {"mode"},
    "postgresql": {"ssl_mode", "ca_file", "allow_insecure"},
    "results": {"fetch_batch_size", "max_rows", "max_bytes", "max_output_bytes"},
    "logging": {"enabled", "file", "level"},
    "failures": {"enabled", "file", "tag"},
}


def default_config():
    """Return fresh application defaults, independent from job templates."""
    package_root = Path(__file__).resolve().parent.parent
    installed_providers = Path(__import__("sys").prefix) / "share" / "dbeeapp" / "providers"
    targeted_providers = package_root / "share" / "dbeeapp" / "providers"
    source_providers = package_root / "providers"
    provider_dir = next(
        (candidate for candidate in (installed_providers, targeted_providers, source_providers) if candidate.is_dir()),
        installed_providers,
    )
    return {
        "provider_dir": str(provider_dir),
        "timeouts": {"connect": 10.0, "provider": 20.0, "sql": 60.0},
        "session": {"mode": "reuse"},
        "postgresql": {"ssl_mode": "verify-full", "ca_file": None, "allow_insecure": False},
        "results": {"fetch_batch_size": 500, "max_rows": 10000, "max_bytes": 10485760, "max_output_bytes": 10485760},
        "logging": {"enabled": True, "file": None, "level": "INFO"},
        "failures": {"enabled": True, "file": None, "tag": "[DBeeApp_Failure]"},
    }


def load_config(path=None):
    """Load and validate application config, or return built-in defaults."""
    config = default_config()
    if path is None:
        return config
    try:
        raw = load_yaml(path)
    except Exception as error:
        if isinstance(error, ConfigurationError):
            raise
        raise ConfigurationError("cannot load application configuration") from None
    if not isinstance(raw, dict):
        raise ConfigurationError("application configuration must be a mapping")
    unknown = set(raw) - _CONFIG_KEYS
    if unknown:
        raise ConfigurationError("application config has unknown field(s): {}".format(", ".join(sorted(unknown))))
    for section, allowed in _SECTIONS.items():
        if section not in raw:
            continue
        values = raw[section]
        if not isinstance(values, dict) or any(not isinstance(key, str) for key in values):
            raise ConfigurationError("application config {} must be a mapping".format(section))
        extra = set(values) - allowed
        if extra:
            raise ConfigurationError("application config {} has unknown field(s): {}".format(section, ", ".join(sorted(extra))))
        config[section].update(values)
    if "provider_dir" in raw:
        if not isinstance(raw["provider_dir"], str) or not Path(raw["provider_dir"]).is_absolute():
            raise ConfigurationError("provider_dir must be an absolute directory path")
        config["provider_dir"] = raw["provider_dir"]
    for key, value in config["timeouts"].items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise ConfigurationError("timeouts.{} must be a positive number".format(key))
    if config["session"]["mode"] not in {"reuse", "new"}:
        raise ConfigurationError("session.mode must be reuse or new")
    if config["postgresql"]["ssl_mode"] not in {"verify-full", "disable"}:
        raise ConfigurationError("postgresql.ssl_mode must be verify-full or disable")
    if not isinstance(config["postgresql"]["allow_insecure"], bool):
        raise ConfigurationError("postgresql.allow_insecure must be boolean")
    if config["postgresql"]["ssl_mode"] == "disable" and not config["postgresql"]["allow_insecure"]:
        raise ConfigurationError("disabling PostgreSQL TLS requires postgresql.allow_insecure: true")
    if config["postgresql"]["ca_file"] is not None and not isinstance(config["postgresql"]["ca_file"], str):
        raise ConfigurationError("postgresql.ca_file must be a path string or null")
    for key, value in config["results"].items():
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ConfigurationError("results.{} must be a positive integer".format(key))
    for section in ("logging", "failures"):
        values = config[section]
        if not isinstance(values["enabled"], bool):
            raise ConfigurationError("{}.enabled must be boolean".format(section))
        for key in ("file",):
            if values[key] is not None and not isinstance(values[key], str):
                raise ConfigurationError("{}.{} must be a path string or null".format(section, key))
    if config["logging"]["level"] not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ConfigurationError("logging.level is invalid")
    if not isinstance(config["failures"]["tag"], str):
        raise ConfigurationError("failures.tag must be a string")
    return config