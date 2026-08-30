"""Throwaway smoke test: runs three single-turn conversations through agent.run_turn and prints the result. Not the eval runner."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import agent, session

CONVERSATIONS = [
    ("smoke-1", "CUST-1004", "where is my order 4501"),
    ("smoke-2", "CUST-1001", "where is my stuff"),
    ("smoke-3", "CUST-1002", "I want to return Strategy: A History from order 4310"),
]


def main():
    for conversation_id, customer_id, message in CONVERSATIONS:
        print(f"\n=== {conversation_id}: {customer_id} says {message!r} ===")

        sess = session.load_session(customer_id)
        result = agent.run_turn(message, sess, state={}, conversation_id=conversation_id, turn=1)

        print("reply:", result["reply"])
        print("intent:", result["intent"])
        print("tools_called:", result["tools_called"])
        print("retrieval:", result["retrieval"])
        print("escalated:", result["escalated"], "-- reason:", result["escalation_reason"])


if __name__ == "__main__":
    main()
