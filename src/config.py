"""Tunable constants for the deterministic layer. Nothing here talks to a model or the network."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Model names only -- no client is constructed in this module or session.
CLASSIFIER_MODEL = "claude-haiku-4-5-20251001"  # cheap/fast pass that decides intent and tools_allowed
AGENT_MODEL = "claude-sonnet-5"  # reasoning pass that talks to the customer and calls tools

MAX_TOOL_TURNS = 5  # hard cap on tool round-trips per turn, matches the one-agent-loop invariant
MAX_CLARIFICATIONS = 2  # how many times the agent may ask the customer to disambiguate before escalating

RETRIEVAL_CONFIDENCE_THRESHOLD = 1.5  # Tuned against measured scores, not guessed. Covered questions score
# at or above 2.524; the two deliberate coverage gaps top out at 0.775 (retrieval.py's IDF weighting).
# 1.5 sits in that band with margin on both sides. When the band closes,
# the fix is a new alias in the policy file, not a new threshold here.
RETRIEVAL_TOP_K = 3  # max number of policy matches returned per search
ALIAS_MATCH_WEIGHT = 2.0  # a query token found in a policy's aliases counts for this much more than a body/title hit

# Names of the tools functions define in tools.py. Kept here, not imported from tools.py,
# so procedures.py can validate against this list without importing tools.py.
KNOWN_TOOLS = ["lookup_order", "create_return", "search_policies"]

# Kept deliberately small: articles, pronouns, prepositions, auxiliaries only.
# Deliberately does NOT include "how" or "much" -- several policy aliases
# (e.g. "how long do I have", "how soon") depend on those words for matching.
STOPWORDS = {
    # articles
    "a", "an", "the",
    # pronouns
    "i", "me", "my", "mine", "you", "your", "yours", "it", "its",
    "this", "that", "these", "those",
    "we", "us", "our", "they", "them", "their",
    "he", "him", "his", "she", "her",
    # prepositions
    "of", "to", "in", "on", "at", "for", "with", "about", "from", "into", "over", "before", "after",
    # auxiliaries
    "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "will", "would", "can", "could", "should",
    "have", "has", "had",
}

DATA_DIR = REPO_ROOT / "data"
POLICIES_DIR = DATA_DIR / "policies"
PROCEDURES_DIR = REPO_ROOT / "procedures"
LOGS_DIR = REPO_ROOT / "logs"
