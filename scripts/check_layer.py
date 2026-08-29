"""Exercises config, procedures, retrieval, and tools without needing an API key. Plain prints, not a test framework."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, procedures, retrieval, tools


def section(title):
    print(f"\n=== {title} ===")


def main():
    section("config")
    print("MAX_TOOL_TURNS:", config.MAX_TOOL_TURNS)
    print("MAX_CLARIFICATIONS:", config.MAX_CLARIFICATIONS)
    print("RETRIEVAL_CONFIDENCE_THRESHOLD:", config.RETRIEVAL_CONFIDENCE_THRESHOLD)
    print("RETRIEVAL_TOP_K:", config.RETRIEVAL_TOP_K)
    print("KNOWN_TOOLS:", config.KNOWN_TOOLS)

    section("procedures.list_intents")
    intents = procedures.list_intents()
    print(intents)

    section("procedures.load_procedure (valid)")
    for intent in intents:
        proc = procedures.load_procedure(intent)
        print(f"{intent}: tools_allowed={proc['tools_allowed']} policy_refs={proc['policy_refs']}")

    section("procedures.load_procedure (unknown intent -- validation error)")
    try:
        procedures.load_procedure("not_a_real_intent")
    except ValueError as e:
        print("Raised ValueError as expected:")
        print(" ", e)

    section("retrieval.search")
    queries = [
        "is it too late to send this back",
        "the book arrived with a torn cover",
        "can you match a competitor price",
    ]
    for q in queries:
        results = retrieval.search(q)
        print(f"\n{q!r} -> is_confident={retrieval.is_confident(results)}")
        for r in results:
            print(f"    {r['policy_id']:<24} score={r['score']:.3f}  {r['excerpt'][:70]}...")

    section("tools.lookup_order")
    print("owner CUST-1004, order ORD-4501:", tools.lookup_order("ORD-4501", "CUST-1004"))
    print("wrong customer CUST-9999:", tools.lookup_order("ORD-4501", "CUST-9999"))
    print("nonexistent order:", tools.lookup_order("ORD-0000", "CUST-1004"))

    section("tools.create_return")
    order = tools.lookup_order("ORD-4501", "CUST-1004")
    sku = order["items"][0]["sku"]
    print("happy path:", tools.create_return("ORD-4501", sku, "changed my mind", "CUST-1004"))
    print("wrong customer:", tools.create_return("ORD-4501", sku, "changed my mind", "CUST-9999"))
    print("wrong sku on real order:", tools.create_return("ORD-4501", "BK-NOT-IN-ORDER", "changed my mind", "CUST-1004"))

    section("tools.get_schemas")
    proc = procedures.load_procedure("return_request")
    schemas = tools.get_schemas(proc["tools_allowed"])
    print("return_request tools_allowed ->", [s["name"] for s in schemas])


if __name__ == "__main__":
    main()
