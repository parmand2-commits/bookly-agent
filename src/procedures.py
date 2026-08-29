"""Loads and validates procedure YAML files. Does not import tools.py -- tool names are checked against config.KNOWN_TOOLS."""

import yaml

from src import config


def list_intents():
    """Return the sorted list of intent names available, read from procedures/*.yaml, not hardcoded."""
    return sorted(p.stem for p in config.PROCEDURES_DIR.glob("*.yaml"))


def load_procedure(intent):
    """Load procedures/<intent>.yaml and raise ValueError if it references an unknown tool or a missing policy file."""
    path = config.PROCEDURES_DIR / f"{intent}.yaml"
    if not path.exists():
        raise ValueError(f"No procedure file found for intent {intent!r} at {path}")

    with path.open(encoding="utf-8") as f:
        procedure = yaml.safe_load(f)

    for tool_name in procedure.get("tools_allowed", []):
        if tool_name not in config.KNOWN_TOOLS:
            raise ValueError(
                f"Procedure {intent!r} lists unknown tool {tool_name!r} in tools_allowed "
                f"(known tools: {config.KNOWN_TOOLS})"
            )

    for policy_id in procedure.get("policy_refs", []):
        policy_path = config.POLICIES_DIR / f"{policy_id}.md"
        if not policy_path.exists():
            raise ValueError(
                f"Procedure {intent!r} references policy_ref {policy_id!r}, "
                f"but {policy_path} does not exist"
            )

    return procedure
