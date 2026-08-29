"""Output checks and prompt-injection defenses. Retrieved policy text and customer messages are always data, never instructions."""

import re

from src import retrieval

POLICY_OPEN, POLICY_CLOSE = "<retrieved_policy>", "</retrieved_policy>"
USER_OPEN, USER_CLOSE = "<customer_message>", "</customer_message>"

# Numbers shaped like a policy commitment: "30 days", "5 to 10 business days", "20%", "35 EUR" / "35 euros" / "35 EUR".
_POLICY_CLAIM_RE = re.compile(
    r"\b\d+(\.\d+)?\s*(day|days|%|percent|eur|euros?)\b|\b(eur|€)\s*\d+(\.\d+)?\b",
    re.IGNORECASE,
)

# Order/customer identifiers, e.g. ORD-4471, CUST-1001.
_IDENTIFIER_RE = re.compile(r"\b(ORD|CUST)-\d+\b")


def wrap_policy(text):
    """Wrap retrieved policy text in explicit delimiters so the system prompt can mark it as data, not instructions."""
    return f"{POLICY_OPEN}\n{text}\n{POLICY_CLOSE}"


def wrap_user_message(text):
    """Wrap a customer's raw message in explicit delimiters so the system prompt can mark it as data, not instructions."""
    return f"{USER_OPEN}\n{text}\n{USER_CLOSE}"


def check_output(text, retrieval_results, procedure, allowed_ids=None):
    """Return a list of violation strings for text: unsupported policy claims, and (if allowed_ids given) stray identifiers."""
    violations = []

    if _POLICY_CLAIM_RE.search(text) and not retrieval.is_confident(retrieval_results):
        violations.append("policy-shaped claim made with no confident retrieval behind it")

    # allowed_ids is optional because check_output's own signature carries no session reference;
    # agent.py passes the current customer's own order/customer ids when it wants this check enforced.
    if allowed_ids is not None:
        for m in _IDENTIFIER_RE.finditer(text):
            token = m.group(0)
            if token not in allowed_ids:
                violations.append(f"reply contains identifier {token} not belonging to this customer's session")

    return violations
