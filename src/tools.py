"""The three tools the agent may call, plus their schemas. Ownership of order_id is always checked against customer_id."""

import json

from src import config, retrieval

ORDERS_PATH = config.DATA_DIR / "orders.json"
RETURNS_PATH = config.DATA_DIR / "returns.json"


def _load_orders():
    with ORDERS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _load_returns():
    if not RETURNS_PATH.exists():
        return []
    with RETURNS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _save_returns(returns):
    with RETURNS_PATH.open("w", encoding="utf-8") as f:
        json.dump(returns, f, indent=2)


def _next_rma(returns):
    """Generate the next six-digit RMA-###### number, one greater than the highest existing RMA."""
    highest = 0
    for r in returns:
        highest = max(highest, int(r["rma"].split("-")[1]))
    return f"RMA-{highest + 1:06d}"


def lookup_order(order_id, customer_id):
    """Return the order record for order_id if it belongs to customer_id, else a not-found or not-authorized error."""
    order = _load_orders().get(order_id)
    if order is None:
        return {"error": "not found"}
    if order["customer_id"] != customer_id:
        return {"error": "not authorized"}
    return order


def create_return(order_id, item_sku, reason, customer_id):
    """Verify the order and item belong to customer_id, append a return record to data/returns.json, and return its RMA number."""
    order = lookup_order(order_id, customer_id)
    if "error" in order:
        return order

    if not any(item["sku"] == item_sku for item in order["items"]):
        return {"error": "item not in order"}

    returns = _load_returns()
    record = {
        "rma": _next_rma(returns),
        "order_id": order_id,
        "item_sku": item_sku,
        "reason": reason,
        "customer_id": customer_id,
    }
    returns.append(record)
    _save_returns(returns)
    return {"rma": record["rma"]}


def search_policies(query):
    """Search the policy index for query and return up to RETRIEVAL_TOP_K {policy_id, score, excerpt} matches."""
    return retrieval.search(query)


TOOL_SCHEMAS = {
    "lookup_order": {
        "name": "lookup_order",
        "description": "Look up an order by its order_id, scoped to the current customer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "The order identifier, e.g. ORD-4471"},
            },
            "required": ["order_id"],
        },
    },
    "create_return": {
        "name": "create_return",
        "description": "Create a return for one item on an order the customer owns and return its RMA number.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "The order identifier, e.g. ORD-4471"},
                "item_sku": {"type": "string", "description": "The SKU of the item being returned"},
                "reason": {"type": "string", "description": "The customer's stated reason for the return"},
            },
            "required": ["order_id", "item_sku", "reason"],
        },
    },
    "search_policies": {
        "name": "search_policies",
        "description": "Search Bookly's policy documents for the passage most relevant to a customer question.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The customer's question or a short paraphrase of it"},
            },
            "required": ["query"],
        },
    },
}


assert set(TOOL_SCHEMAS) == set(config.KNOWN_TOOLS), "TOOL_SCHEMAS and config.KNOWN_TOOLS have drifted apart"


def get_schemas(tools_allowed):
    """Return the TOOL_SCHEMAS entries named in tools_allowed, in that order."""
    return [TOOL_SCHEMAS[name] for name in tools_allowed]
