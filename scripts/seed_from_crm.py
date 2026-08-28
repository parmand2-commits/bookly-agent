"""One-time seed script: turn raw CRM CSV exports into clean JSON data files.

Never repairs bad input; every rejected row is logged with its record_id and
reason in data/seed_report.txt so nothing is dropped silently.
"""

import csv
import json
from datetime import date, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
DATA_DIR = REPO_ROOT / "data"

EXPORT_CSV = RAW_DIR / "bookly_crm_export.csv"
TICKETS_CSV = RAW_DIR / "bookly_crm_tickets.csv"

# The CRM export tool is Excel FR: it writes a UTF-8 BOM, ';' as the field
# separator (',' is the decimal separator in FR locale), and CRLF line endings.
CSV_ENCODING = "utf-8-sig"
CSV_DELIMITER = ";"

VALID_STATUSES = {"processing", "shipped", "in_transit", "delivered", "cancelled"}
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y")  # ISO, and day-first FR (never month-first)


def read_csv_rows(path):
    """Read a ';'-delimited, BOM-prefixed CSV file into a list of dict rows."""
    with path.open(encoding=CSV_ENCODING, newline="") as f:
        return list(csv.DictReader(f, delimiter=CSV_DELIMITER))


def strip_row(row):
    """Return a copy of row with leading/trailing whitespace stripped from every value."""
    return {key: (value.strip() if value is not None else value) for key, value in row.items()}


def parse_date(raw):
    """Parse an ISO or day-first date string to ISO 8601, or None if blank; raises ValueError if neither format matches."""
    if not raw:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date format: {raw!r}")


def normalize_status(raw):
    """Map an order_status string onto the canonical enum, raising ValueError if it doesn't match one."""
    normalized = raw.strip().lower().replace(" ", "_")
    if normalized not in VALID_STATUSES:
        raise ValueError(f"unrecognised order_status: {raw!r}")
    return normalized


def process_export_rows(rows, customers, orders, rejects):
    """Validate and fold each export CSV row into the customers/orders dicts, or reject it."""
    for raw_row in rows:
        row = strip_row(raw_row)
        record_id = row["record_id"]

        if not row["customer_id"]:
            rejects.append((record_id, "missing customer_id"))
            continue

        try:
            order_date = parse_date(row["order_date"])
            delivery_date = parse_date(row["delivery_date"])
            customer_since = parse_date(row["customer_since"])
        except ValueError:
            rejects.append((record_id, "unparseable date"))
            continue

        if order_date and delivery_date and delivery_date < order_date:
            # ISO 8601 strings sort chronologically, so plain string comparison is correct here.
            rejects.append((record_id, "delivery_date earlier than order_date"))
            continue

        try:
            order_status = normalize_status(row["order_status"])
        except ValueError:
            rejects.append((record_id, "unknown order_status"))
            continue

        customer_id = row["customer_id"]
        # First-seen values win for repeated customer fields; cross-row consistency is not checked.
        customers.setdefault(
            customer_id,
            {
                "customer_id": customer_id,
                "name": row["customer_name"],
                "email": row["customer_email"],
                "customer_since": customer_since,
            },
        )

        order_id = row["order_id"]
        # Same first-seen-wins rule for the order-level fields repeated on every line of an order.
        order = orders.setdefault(
            order_id,
            {
                "order_id": order_id,
                "customer_id": customer_id,
                "order_date": order_date,
                "order_status": order_status,
                "delivery_date": delivery_date,
                "shipping_country": row["shipping_country"],
                "shipping_cost_eur": float(row["shipping_cost_eur"]),
                "payment_last4": row["payment_last4"],
                "channel": row["channel"],
                "notes": [],
                "items": [],
            },
        )
        order["items"].append(
            {
                "sku": row["item_sku"],
                "title": row["item_title"],
                "author": row["item_author"],
                "qty": int(row["item_qty"]),
                "price_eur": float(row["item_price_eur"]),
            }
        )
        if row["notes"]:
            order["notes"].append(row["notes"])


def compute_subtotals(orders):
    """Set each order's subtotal_eur to the rounded sum of qty * price_eur across its items."""
    for order in orders.values():
        subtotal = sum(item["qty"] * item["price_eur"] for item in order["items"])
        order["subtotal_eur"] = round(subtotal, 2)


def process_ticket_rows(rows, history):
    """Group stripped, date-normalised ticket rows into the history dict, keyed by customer_id."""
    for raw_row in rows:
        row = strip_row(raw_row)
        customer_id = row["customer_id"]
        history.setdefault(customer_id, []).append(
            {
                "ticket_id": row["ticket_id"],
                "order_id": row["order_id"] or None,
                "opened_at": parse_date(row["opened_at"]),
                "closed_at": parse_date(row["closed_at"]),
                "channel": row["channel"],
                "category": row["category"],
                "summary": row["summary"],
                "resolution": row["resolution"],
            }
        )


def write_json(path, data):
    """Write data to path as indented, UTF-8 JSON."""
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_report(path, rejects, rows_read, orders_built, customers_built):
    """Write the seed report: every rejected row with its reason, then summary counts."""
    lines = ["Rejected rows:"]
    if rejects:
        lines += [f"  {record_id}: {reason}" for record_id, reason in rejects]
    else:
        lines.append("  (none)")
    lines += [
        "",
        "Counts:",
        f"  rows read: {rows_read}",
        f"  rows rejected: {len(rejects)}",
        f"  orders built: {orders_built}",
        f"  customers built: {customers_built}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    export_rows = read_csv_rows(EXPORT_CSV)
    ticket_rows = read_csv_rows(TICKETS_CSV)

    customers = {}
    orders = {}
    rejects = []
    process_export_rows(export_rows, customers, orders, rejects)
    compute_subtotals(orders)

    history = {}
    process_ticket_rows(ticket_rows, history)

    write_json(DATA_DIR / "customers.json", customers)
    write_json(DATA_DIR / "orders.json", orders)
    write_json(DATA_DIR / "history.json", history)
    write_report(
        DATA_DIR / "seed_report.txt",
        rejects,
        rows_read=len(export_rows),
        orders_built=len(orders),
        customers_built=len(customers),
    )

    print(
        f"seeded {len(customers)} customers, {len(orders)} orders "
        f"({len(rejects)} rows rejected out of {len(export_rows)} read)"
    )


if __name__ == "__main__":
    main()
