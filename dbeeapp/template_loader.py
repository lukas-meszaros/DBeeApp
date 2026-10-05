"""Safe YAML loading for application configuration and job templates."""

from pathlib import Path

import yaml

from dbeeapp.errors import ValidationError

MAX_YAML_BYTES = 1024 * 1024


class _UniqueKeySafeLoader(yaml.SafeLoader):
    def compose_node(self, parent, index):
        if self.check_event(yaml.events.AliasEvent):
            event = self.peek_event()
            raise yaml.constructor.ConstructorError(
                None,
                None,
                "YAML aliases are not supported",
                event.start_mark,
            )
        return super().compose_node(parent, index)

    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        keys = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                duplicate = key in keys
                keys.add(key)
            except TypeError:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "mapping keys must be scalar values",
                    key_node.start_mark,
                )
            if duplicate:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "duplicate mapping key",
                    key_node.start_mark,
                )
        return super().construct_mapping(node, deep=deep)


def load_yaml(path, max_bytes=MAX_YAML_BYTES):
    """Load exactly one safe YAML document, rejecting duplicate keys."""
    source = Path(path)
    try:
        raw = source.read_bytes()
    except OSError:
        raise ValidationError("cannot read YAML file: {}".format(source)) from None
    if len(raw) > max_bytes:
        raise ValidationError("YAML file exceeds the {} byte limit".format(max_bytes))
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ValidationError("YAML file must be UTF-8: {}".format(source)) from None
    try:
        return yaml.load(text, Loader=_UniqueKeySafeLoader)
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        location = ""
        if mark is not None:
            location = " at line {}, column {}".format(mark.line + 1, mark.column + 1)
        problem = getattr(error, "problem", "invalid YAML")
        if problem not in (
            "duplicate mapping key",
            "mapping keys must be scalar values",
            "YAML aliases are not supported",
        ):
            problem = "invalid or unsupported YAML"
        raise ValidationError("{}:{}{}: {}".format(source, location, "", problem)) from None