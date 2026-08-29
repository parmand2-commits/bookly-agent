"""Keyword search over data/policies/*.md. No vector database, no embeddings -- an in-memory index built once at import time."""

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


def search(query):
    """Score every policy against the query's significant tokens and return up to RETRIEVAL_TOP_K matches, highest score first."""
    significant_tokens = [t for t in _tokenize(query) if t not in config.STOPWORDS]
    if not significant_tokens:
        return []

    results = []
    for entry in _INDEX:
        total = 0.0
        for token in significant_tokens:
            if token in entry["alias_tokens"]:
                total += config.ALIAS_MATCH_WEIGHT
            elif token in entry["title_tokens"] or token in entry["body_tokens"]:
                total += 1.0
        score = total / len(significant_tokens)
        if score > 0:
            results.append({"policy_id": entry["id"], "score": score, "excerpt": entry["excerpt"]})

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[: config.RETRIEVAL_TOP_K]


def is_confident(results):
    """Return True only if there is at least one result and its top score meets RETRIEVAL_CONFIDENCE_THRESHOLD."""
    return bool(results) and results[0]["score"] >= config.RETRIEVAL_CONFIDENCE_THRESHOLD
