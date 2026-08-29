"""Prints raw retrieval.search() scores, with NO threshold applied, so RETRIEVAL_CONFIDENCE_THRESHOLD can be set by hand.

Covered questions are natural customer phrasing that the policy aliases are meant to catch --
they intentionally do NOT reuse the alias wording verbatim.

Uncovered questions are the two deliberate coverage gaps: pricing-match requests and
post-shipment address changes. They are close to existing policy content (returns,
shipping) which is exactly what makes them hard to separate from a real match.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import retrieval

COVERED_QUESTIONS = [
    "is it too late to send this back",
    "bought it months ago, can I still return it",
    "why was I charged for delivery",
    "my parcel hasn't moved in days",
    "the book arrived with a torn cover",
    "I can't log in",
    "still waiting for the credit on my card",
]

UNCOVERED_QUESTIONS = [
    "can you match a competitor price",
    "your competitor sells it cheaper, will you refund the difference",
    "send order 4455 to my work address instead",
    "can I change the delivery address, it already shipped",
]


def top_match(question):
    """Return (policy_id, score) for the single best-scoring policy, or (None, 0.0) if nothing matched at all."""
    results = retrieval.search(question)
    if not results:
        return None, 0.0
    return results[0]["policy_id"], results[0]["score"]


def print_block(title, questions):
    scored = [(question, *top_match(question)) for question in questions]
    scored.sort(key=lambda row: row[2], reverse=True)
    print(f"\n=== {title} ===")
    for question, policy_id, score in scored:
        print(f"  {score:.3f}  {policy_id or '(no match)':<24} {question!r}")


def main():
    print_block("Covered questions (natural phrasing, not alias wording)", COVERED_QUESTIONS)
    print_block("Uncovered questions (deliberate coverage gaps)", UNCOVERED_QUESTIONS)


if __name__ == "__main__":
    main()
