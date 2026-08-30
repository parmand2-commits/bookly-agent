"""Output checks and prompt-injection defenses. Retrieved policy text and customer messages are always data, never instructions."""

import re

from src import retrieval

POLICY_OPEN, POLICY_CLOSE = "<retrieved_policy>", "</retrieved_policy>"
USER_OPEN, USER_CLOSE = "<customer_message>", "</customer_message>"

# A day-count on its own ("delivered about 10 days ago") just restates order data, not a policy.
# It only counts as a policy claim when policy language shows up near it -- see _has_policy_context.
_DAY_COUNT_RE = re.compile(r"\b\d+(\.\d+)?\s*days?\b", re.IGNORECASE)
_POLICY_CONTEXT_WORDS = (
    "window", "policy", "eligib", "entitled", "allowed", "refund", "period", "deadline", "business",
)
_CONTEXT_RADIUS = 40  # characters on each side of a day-count to look for policy language

# Percent/currency figures are policy-shaped on their own -- Bookly has no everyday reason to quote
# a percentage or a price back at a customer outside of a policy (a discount, a fee, a refund amount).
_PERCENT_OR_CURRENCY_RE = re.compile(
    r"\b\d+(\.\d+)?\s*(%|percent|eur|euros?)\b|\b(eur|€)\s*\d+(\.\d+)?\b",
    re.IGNORECASE,
)


def _has_policy_context(text, match):
    """True if policy language appears within _CONTEXT_RADIUS characters of a day-count match."""
    start = max(0, match.start() - _CONTEXT_RADIUS)
    end = min(len(text), match.end() + _CONTEXT_RADIUS)
    window = text[start:end].lower()
    return any(word in window for word in _POLICY_CONTEXT_WORDS)


def _has_unsupported_policy_claim(text):
    """True if text makes a policy-shaped claim: a percent/currency figure, or a day-count near policy language."""
    if _PERCENT_OR_CURRENCY_RE.search(text):
        return True
    return any(_has_policy_context(text, m) for m in _DAY_COUNT_RE.finditer(text))

# Order/customer identifiers, e.g. ORD-4471, CUST-1001.
_IDENTIFIER_RE = re.compile(r"\b(ORD|CUST)-\d+\b")

# Language claiming an escalation/hand-off happened -- the same shape of problem as an unsupported
# policy claim: the reply asserts something the system did not actually do. "escalat\w*" alone
# covers escalate/escalating/escalated/escalation, which is the exact word the real failure used
# ("Your escalation has already been submitted").
_ESCALATION_CLAIM_RE = re.compile(
    r"\bescalat\w*|connect(?:ed|ing)? you with|human agent|human support|"
    r"flag(?:ged|ging)? this (?:for|to)|pass(?:ed|ing)? this (?:to|on to) a colleague|"
    r"someone will get back",
    re.IGNORECASE,
)


def _claims_escalation(text):
    """True if text uses language claiming an escalation or human hand-off (e.g. "I'll escalate this")."""
    return bool(_ESCALATION_CLAIM_RE.search(text))


def wrap_policy(text):
    """Wrap retrieved policy text in explicit delimiters so the system prompt can mark it as data, not instructions."""
    return f"{POLICY_OPEN}\n{text}\n{POLICY_CLOSE}"


def wrap_user_message(text):
    """Wrap a customer's raw message in explicit delimiters so the system prompt can mark it as data, not instructions."""
    return f"{USER_OPEN}\n{text}\n{USER_CLOSE}"


def check_output(text, retrieval_results, procedure, allowed_ids=None, escalation_confirmed=False):
    """Return a list of violation strings for text: unsupported policy claims, escalation language
    with no escalation behind it, and (if allowed_ids given) stray identifiers.

    escalation_confirmed=True means a valid <<ESCALATE>> marker was already found in this same
    reply -- pass True there so escalation language consistent with a real escalation isn't
    flagged. Default False so a caller that doesn't pass it gets the check enforced, not skipped.
    """
    violations = []

    if _has_unsupported_policy_claim(text) and not retrieval.is_confident(retrieval_results):
        violations.append("policy-shaped claim made with no confident retrieval behind it")

    if _claims_escalation(text) and not escalation_confirmed:
        violations.append("reply claims an escalation was made, but no escalation was triggered")

    # allowed_ids is optional because check_output's own signature carries no session reference;
    # agent.py passes the current customer's own order/customer ids when it wants this check enforced.
    if allowed_ids is not None:
        for m in _IDENTIFIER_RE.finditer(text):
            token = m.group(0)
            if token not in allowed_ids:
                violations.append(f"reply contains identifier {token} not belonging to this customer's session")

    return violations
