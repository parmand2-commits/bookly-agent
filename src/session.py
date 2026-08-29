"""Loads everything the agent needs to know about a customer, once, before the conversation starts."""

import json

from src import config

CUSTOMERS_PATH = config.DATA_DIR / "customers.json"
ORDERS_PATH = config.DATA_DIR / "orders.json"
HISTORY_PATH = config.DATA_DIR / "history.json"

OPEN_STATUSES_EXCLUDED = {"delivered", "cancelled"}


def _load_customers():
    """Read customers.json (a list of [customer_id, record] pairs) into a dict keyed by customer_id."""
    with CUSTOMERS_PATH.open(encoding="utf-8") as f:
        return dict(json.load(f))


def _load_orders():
    """Read orders.json, a dict keyed by order_id."""
    with ORDERS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _load_history():
    """Read history.json, a dict keyed by customer_id, each value a list of past tickets."""
    with HISTORY_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def load_session(customer_id):
    """Return {customer, open_orders, recent_tickets} for customer_id, read once at conversation start."""
    customer = _load_customers().get(customer_id)

    orders = _load_orders()
    open_orders = [
        order
        for order in orders.values()
        if order["customer_id"] == customer_id and order["order_status"] not in OPEN_STATUSES_EXCLUDED
    ]

    recent_tickets = _load_history().get(customer_id, [])

    return {
        "customer": customer,
        "open_orders": open_orders,
        "recent_tickets": recent_tickets,
    }
