"""Keyword search over data/policies/*.md. No vector database, no embeddings -- an in-memory index built once at import time."""

import math
import re

import yaml

from src import config

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text):
    """Lowercase text, drop apostrophes, and split it into a list of alphanumeric tokens."""
    return _WORD_RE.findall(text.lower().replace("'", ""))


def _load_policy_file(path):
    """Split one policy markdown file into its parsed frontmatter dict and its body text."""
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"Policy file {path} is missing '---' frontmatter delimiters")
    frontmatter = yaml.safe_load(parts[1]) or {}
    body = parts[2].strip()
    return frontmatter, body


def _build_index():
    """Parse every data/policies/*.md file once into a list of searchable entries with precomputed token sets."""
    index = []
    for path in sorted(config.POLICIES_DIR.glob("*.md")):
        frontmatter, body = _load_policy_file(path)
        title = frontmatter.get("title", "")
        aliases = frontmatter.get("aliases", [])
        excerpt = " ".join(body.split())[:200]
        index.append(
            {
                "id": frontmatter["id"],
                "title_tokens": set(_tokenize(title)),
                "alias_tokens": set(_tokenize(" ".join(aliases))),
                "body_tokens": set(_tokenize(body)),
                "excerpt": excerpt,
            }
        )
    return index


_INDEX = _build_index()


def _document_frequency(index):
    """Count, for every token in the corpus, how many policy entries contain it at all (title, alias, or body)."""
    df = {}
    for entry in index:
        for token in entry["title_tokens"] | entry["alias_tokens"] | entry["body_tokens"]:
            df[token] = df.get(token, 0) + 1
    return df


_DOC_FREQUENCY = _document_frequency(_INDEX)
_NUM_POLICIES = len(_INDEX)


def _idf(token):
    """Inverse document frequency: how much signal one occurrence of token carries, given how many of the corpus's policies contain it."""
    df = _DOC_FREQUENCY.get(token, 0)
    if df == 0:
        return 0.0
    return math.log(_NUM_POLICIES / df)


def search(query):
    """Score every policy against the query's significant tokens, weighting each hit by the token's rarity across the corpus, and return up to RETRIEVAL_TOP_K matches, highest score first."""
    significant_tokens = [t for t in _tokenize(query) if t not in config.STOPWORDS]
    if not significant_tokens:
        return []

    token_idf = {token: _idf(token) for token in significant_tokens}

    results = []
    for entry in _INDEX:
        total = 0.0
        for token in significant_tokens:
            if token in entry["alias_tokens"]:
                total += config.ALIAS_MATCH_WEIGHT * token_idf[token]
            elif token in entry["title_tokens"] or token in entry["body_tokens"]:
                total += token_idf[token]
        score = total / len(significant_tokens)
        if score > 0:
            results.append({"policy_id": entry["id"], "score": score, "excerpt": entry["excerpt"]})

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[: config.RETRIEVAL_TOP_K]


def is_confident(results):
    """Return True only if there is at least one result and its top score meets RETRIEVAL_CONFIDENCE_THRESHOLD."""
    return bool(results) and results[0]["score"] >= config.RETRIEVAL_CONFIDENCE_THRESHOLD
