"""Minimal command-line chat for the Bookly support agent.

Loads the session once, then loops on input(), calling agent.run_turn with a
persistent state dict. After each reply, prints a side panel showing the
agent's reasoning for that turn -- that panel is the demo.
"""

import json
import sys
import uuid

from src import agent, config, session
from src import logging as turn_log


def _find_log_record(conversation_id, turn):
    """Read logs/turns.jsonl and return the record for (conversation_id, turn), or None.

    log_turn() runs synchronously inside run_turn before it returns, so the record for
    this turn is guaranteed to be on disk already. Only the tail is scanned, newest first.
    """
    try:
        lines = turn_log.TURNS_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in reversed(lines[-20:]):
        record = json.loads(line)
        if record["conversation_id"] == conversation_id and record["turn"] == turn:
            return record
    return None


def _format_tool(call):
    """One compact 'name✓' or 'name✗ (error)' fragment for a tools_called entry."""
    if call["ok"]:
        return f"{call['name']}✓"
    return f"{call['name']}✗ ({call.get('error')})"


def _print_panel(result, log_record):
    print("-" * 60)
    print(f"intent: {result['intent']}   procedure: {result['procedure']}")

    tools_str = ", ".join(_format_tool(c) for c in result["tools_called"]) or "none"
    print(f"tools called: {tools_str}")

    if result["retrieval"]:
        print("retrieval:")
        for entry in result["retrieval"]:
            confident = entry["score"] >= config.RETRIEVAL_CONFIDENCE_THRESHOLD
            print(
                f'  "{entry["query"]}" -> {entry["policy_id"]} '
                f'score={entry["score"]:.2f} confident={confident}'
            )

    triggers = log_record["escalation_triggers"] if log_record else []
    print(f"escalated: {result['escalated']}   reason: {result['escalation_reason']}")
    print(f"escalation_triggers: {triggers}")
    print("-" * 60)


def main():
    if len(sys.argv) != 2:
        print("usage: python cli.py <customer_id>")
        sys.exit(1)
    customer_id = sys.argv[1]

    sess = session.load_session(customer_id)
    if sess["customer"] is None:
        print(f"warning: no customer record found for {customer_id!r}; every turn will escalate.")

    state = {}
    conversation_id = str(uuid.uuid4())
    turn = 0

    print(f"Bookly support chat -- customer {customer_id}. Ctrl-D to quit.")
    while True:
        try:
            message = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not message:
            continue

        turn += 1
        result = agent.run_turn(message, sess, state, conversation_id, turn)
        state = result["state"]

        print(f"bookly> {result['reply']}")
        _print_panel(result, _find_log_record(conversation_id, turn))


if __name__ == "__main__":
    main()
