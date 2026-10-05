"""Command-line interface for DBeeApp."""

import argparse
import sys
from pathlib import Path

from dbeeapp import __version__
from dbeeapp.config import load_config
from dbeeapp.errors import DBeeAppError, ConfigurationError
from dbeeapp.template_loader import load_yaml
from dbeeapp.validator import describe_template, validate_template


def _parser():
    parser = argparse.ArgumentParser(prog="dbeeapp", description="Declarative PostgreSQL workflow runner")
    parser.add_argument("--config", help="application configuration YAML")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("version", help="show version")
    for name in ("validate", "describe"):
        command = commands.add_parser(name, help="validate or summarize a workflow template")
        command.add_argument("template", type=Path)
    run = commands.add_parser("run", help="execute a validated workflow")
    run.add_argument("template", type=Path)
    run.add_argument("--dry-run", action="store_true", help="validate and describe without side effects")
    run.add_argument("--log-level", choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"))
    return parser


def _read_template(path, config):
    try:
        document = load_yaml(path)
        return validate_template(document, path, config=config)
    except DBeeAppError:
        raise
    except OSError:
        raise ConfigurationError("cannot read template: {}".format(path)) from None


def main(argv=None):
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        if args.command == "version":
            print("DBeeApp {}".format(__version__))
            return 0
        document = _read_template(args.template, config)
        if args.command == "validate":
            print("Validation: OK")
            return 0
        if args.command == "describe":
            print(describe_template(document, config))
            return 0
        if args.dry_run:
            print(describe_template(document, config))
            print("Dry run: no providers, database connections, SQL, or outputs were executed.")
            print("SQL correctness and database-side safety were not tested.")
            return 0
        from dbeeapp.engine import run_job

        return run_job(document, args.template, config, log_level=args.log_level)
    except DBeeAppError as error:
        print("DBeeApp error [{}]: {}".format(error.category, error.public_message), file=sys.stderr)
        return error.exit_code
    except KeyboardInterrupt:
        print("DBeeApp interrupted", file=sys.stderr)
        return 130
    except Exception:
        print("DBeeApp error [internal]: unexpected internal failure", file=sys.stderr)
        return 8