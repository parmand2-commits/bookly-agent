"""Replays every case in evals/cases.yaml through agent.run_turn and reports pass/fail.

Only checks the fields a case's `expect` block actually declares -- a missing field
means "not checked", never "must be empty". Full results are written to
evals/results.json in addition to the printed report.
"""

import json
import statistics
import sys
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import agent, session
from src import logging as turn_log

CASES_PATH = Path(__file__).resolve().parent / "cases.yaml"
RESULTS_PATH = Path(__file__).resolve().parent / "results.json"


def load_cases():
    with CASES_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def expand_instances(cases):
    """Turn each case into one run instance per variant, plus the base case itself.

    A variant string replaces turn 1's message only; every current variants case is
    single-turn, so this is exact, not an approximation.
    """
    instances = []
    for case in cases:
        base_messages = [t["user"] for t in case["turns"]]
        instances.append({"case": case, "label": case["id"], "messages": base_messages})
        for i, variant in enumerate(case.get("variants") or [], start=1):
            messages = [variant] + base_messages[1:]
            instances.append({"case": case, "label": f"{case['id']}[variant:{i}]", "messages": messages})
    return instances


def run_instance(instance):
    """Replay one instance's messages through agent.run_turn with a fresh session and state."""
    customer_id = instance["case"]["session"]["customer_id"]
    sess = session.load_session(customer_id)
    state = {}
    conversation_id = f"eval-{instance['label']}"
    turn_results = []
    for i, message in enumerate(instance["messages"], start=1):
        result = agent.run_turn(message, sess, state, conversation_id, i)
        state = result["state"]
        turn_results.append(result)
    return turn_results, conversation_id


def evaluate_expect(expect, turns, prefix=""):
    """Check every field `expect` declares against `turns` (in scope), return a list of failures.

    Last-turn scoped: intent, procedure, escalated, escalation_reason_contains.
    Union-scoped (any/all turn in scope): tools_called, tools_not_called, tool_errors,
    tool_args, must_cite, must_contain (any turn), must_not_contain (every turn --
    deliberately asymmetric: a forbidden string on any turn is a failure even if later
    turns are clean).
    """
    failures = []
    last = turns[-1]

    def fail(field, expected, actual):
        failures.append({"field": prefix + field, "expected": expected, "actual": actual})

    if "intent" in expect and last["intent"] != expect["intent"]:
        fail("intent", expect["intent"], last["intent"])

    if "procedure" in expect:
        # cases.yaml writes "none" (a bare YAML scalar, parsed as the string "none" --
        # YAML's null tokens are null/Null/NULL/~, not "none") to mean "no procedure
        # loaded", which run_turn represents as Python None. Normalize before comparing.
        expected_procedure = None if expect["procedure"] == "none" else expect["procedure"]
        if last["procedure"] != expected_procedure:
            fail("procedure", expect["procedure"], last["procedure"])

    if "escalated" in expect and last["escalated"] != expect["escalated"]:
        fail("escalated", expect["escalated"], last["escalated"])

    if "escalation_reason_contains" in expect:
        reason = last["escalation_reason"] or ""
        if expect["escalation_reason_contains"].lower() not in reason.lower():
            fail("escalation_reason_contains", expect["escalation_reason_contains"], last["escalation_reason"])

    all_calls = [c for t in turns for c in t["tools_called"]]
    called_names = {c["name"] for c in all_calls}

    if "tools_called" in expect:
        missing = [n for n in expect["tools_called"] if n not in called_names]
        if missing:
            fail("tools_called", expect["tools_called"], sorted(called_names))

    if "tools_not_called" in expect:
        offenders = [n for n in expect["tools_not_called"] if n in called_names]
        if offenders:
            fail("tools_not_called", expect["tools_not_called"], offenders)

    if "tool_errors" in expect:
        for tool_name, substring in expect["tool_errors"].items():
            matches = [c for c in all_calls if c["name"] == tool_name and not c["ok"]]
            if not any(substring.lower() in (c.get("error") or "").lower() for c in matches):
                actual = [c.get("error") for c in matches] if matches else "tool never called with an error"
                fail(f"tool_errors[{tool_name}]", substring, actual)

    if "tool_args" in expect:
        for tool_name, expected_kv in expect["tool_args"].items():
            matches = [c for c in all_calls if c["name"] == tool_name]
            if not any(all(c["input"].get(k) == v for k, v in expected_kv.items()) for c in matches):
                actual = [c["input"] for c in matches] if matches else "tool never called"
                fail(f"tool_args[{tool_name}]", expected_kv, actual)

    if "must_cite" in expect:
        cited = {r["policy_id"] for t in turns for r in t["retrieval"]}
        missing = [p for p in expect["must_cite"] if p not in cited]
        if missing:
            fail("must_cite", expect["must_cite"], sorted(cited))

    if "must_contain" in expect:
        replies = [t["reply"] for t in turns]
        missing = [s for s in expect["must_contain"] if not any(s.lower() in r.lower() for r in replies)]
        if missing:
            fail("must_contain", expect["must_contain"], replies)

    if "must_not_contain" in expect:
        replies = [t["reply"] for t in turns]
        found = [s for s in expect["must_not_contain"] if any(s.lower() in r.lower() for r in replies)]
        if found:
            fail("must_not_contain", expect["must_not_contain"], {"found": found, "replies": replies})

    if "turn_count" in expect and len(turns) != expect["turn_count"]:
        fail("turn_count", expect["turn_count"], len(turns))

    return failures


def evaluate_instance(case, turn_results):
    """Run all of a case's declared checks (top-level + per_turn) against one instance's turn results."""
    expect = case.get("expect", {})
    top_level = {k: v for k, v in expect.items() if k != "per_turn"}
    failures = evaluate_expect(top_level, turn_results)

    for pt in expect.get("per_turn", []):
        idx = pt["turn"] - 1
        pt_expect = {k: v for k, v in pt.items() if k != "turn"}
        if not (0 <= idx < len(turn_results)):
            failures.append(
                {"field": f"turn{pt['turn']}", "expected": "turn to exist", "actual": f"only {len(turn_results)} turns ran"}
            )
            continue
        failures += evaluate_expect(pt_expect, [turn_results[idx]], prefix=f"turn{pt['turn']}.")

    # A structural defect is exactly a tools_not_called failure -- a tool the case declared
    # off-limits was reachable and got called. Never masked by wording; that's the point.
    structural_defect = any(f["field"].split(".")[-1].startswith("tools_not_called") for f in failures)
    return failures, structural_defect


def _log_line_count():
    try:
        with turn_log.TURNS_PATH.open(encoding="utf-8") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def _read_new_log_records(start_line):
    """Read logs/turns.jsonl lines appended since start_line, indexed by (conversation_id, turn)."""
    try:
        lines = turn_log.TURNS_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    index = {}
    for line in lines[start_line:]:
        record = json.loads(line)
        index[(record["conversation_id"], record["turn"])] = record
    return index


def main():
    cases = load_cases()
    instances = expand_instances(cases)

    log_start = _log_line_count()

    results = []
    for instance in instances:
        turn_results, conversation_id = run_instance(instance)
        failures, structural_defect = evaluate_instance(instance["case"], turn_results)
        results.append(
            {
                "label": instance["label"],
                "case_id": instance["case"]["id"],
                "category": instance["case"]["category"],
                "conversation_id": conversation_id,
                "turn_count": len(turn_results),
                "passed": not failures,
                "failures": failures,
                "structural_defect": structural_defect,
                "final_escalated": turn_results[-1]["escalated"],
                "final_escalation_reason": turn_results[-1]["escalation_reason"],
            }
        )

    # Per-turn latency, cost, and escalation stats all come from the log lines this run
    # just appended (matched by conversation_id+turn), since run_turn's return value
    # doesn't carry them -- escalation rate is over every turn actually run, not just
    # each case's final turn, so a mid-conversation escalation counts too.
    log_index = _read_new_log_records(log_start)
    all_latencies = []
    total_cost = 0.0
    escalated_turns = 0
    total_turns = 0
    reason_counts = Counter()
    for result in results:
        for i in range(1, result["turn_count"] + 1):
            record = log_index.get((result["conversation_id"], i))
            if record is None:
                continue
            all_latencies.append(record["latency_ms"])
            total_cost += record["cost_usd"]
            total_turns += 1
            if record["escalated"]:
                escalated_turns += 1
                reason_counts[record["escalation_reason"]] += 1

    category_stats = {}
    for result in results:
        cat = result["category"]
        stats = category_stats.setdefault(cat, {"passed": 0, "total": 0})
        stats["total"] += 1
        stats["passed"] += result["passed"]

    overall_passed = sum(r["passed"] for r in results)
    overall_total = len(results)
    structural_defect_count = sum(r["structural_defect"] for r in results)
    median_latency = statistics.median(all_latencies) if all_latencies else 0

    report = {
        "category_pass_rate": {
            cat: {"passed": s["passed"], "total": s["total"], "rate": s["passed"] / s["total"]}
            for cat, s in sorted(category_stats.items())
        },
        "overall_pass_rate": {"passed": overall_passed, "total": overall_total, "rate": overall_passed / overall_total},
        "failing_instances": [r for r in results if not r["passed"]],
        "escalation_rate": {
            "escalated_turns": escalated_turns,
            "total_turns": total_turns,
            "rate": (escalated_turns / total_turns) if total_turns else 0,
        },
        "escalation_reason_counts": dict(reason_counts),
        "structural_defect_count": structural_defect_count,
        "median_latency_ms": median_latency,
        "total_cost_usd": total_cost,
        "instances": results,
    }

    RESULTS_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print_report(report)


def print_report(report):
    print("=" * 70)
    print("PASS RATE PER CATEGORY")
    for cat, s in report["category_pass_rate"].items():
        print(f"  {cat:14s} {s['passed']}/{s['total']}  ({s['rate']:.0%})")
    o = report["overall_pass_rate"]
    print(f"  {'overall':14s} {o['passed']}/{o['total']}  ({o['rate']:.0%})")

    print("\nFAILING INSTANCES")
    if not report["failing_instances"]:
        print("  none")
    for inst in report["failing_instances"]:
        print(f"  {inst['label']} ({inst['category']})")
        for f in inst["failures"]:
            print(f"    - {f['field']}: expected={f['expected']!r} actual={f['actual']!r}")

    print("\nESCALATION")
    e = report["escalation_rate"]
    print(f"  {e['escalated_turns']}/{e['total_turns']} turns escalated ({e['rate']:.0%})")
    for reason, count in sorted(report["escalation_reason_counts"].items(), key=lambda kv: -kv[1]):
        print(f"    {count:3d}  {reason}")

    print("\nSTRUCTURAL DEFECTS")
    print(f"  {report['structural_defect_count']} instance(s) called a tool listed in tools_not_called (target: 0)")

    print("\nCOST / LATENCY")
    print(f"  median latency: {report['median_latency_ms']:.0f} ms")
    print(f"  total cost:     ${report['total_cost_usd']:.4f}")
    print("=" * 70)
    print(f"\nFull results written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
