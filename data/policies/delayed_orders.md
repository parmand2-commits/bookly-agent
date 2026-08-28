---
id: delayed_orders
title: Late orders
aliases: [hasn't moved in days, stuck, tracking says nothing, way past the estimate, never showed up]
scope: Orders that have shipped but not arrived within the published estimate
owner: CX Policy
last_updated: 2026-08-15
---

# Late orders

An order is officially considered late once it has been in transit for **more than 5 business days beyond the upper bound of the estimate** for its delivery zone in shipping_times. An order that has not yet shipped is not late; it is simply unshipped, and no delivery estimate should be quoted for it.

Once an order meets this threshold, Bookly opens a carrier trace and, if the trace does not locate the parcel within a reasonable time, offers the customer a reshipment or a refund at the discretion of the logistics team.

Support agents should not offer a reshipment or refund for a late order themselves; confirm the order meets the threshold, then escalate.

For the delivery estimates this threshold is measured against, see shipping_times.

## Escalate if
- The order meets the lateness threshold defined in this file
- The customer requests to cancel a late order (see order_cancellation)
- Tracking has shown no movement at all since dispatch
- The customer disputes the dispatch date used to calculate lateness

## Related
- shipping_times
- order_cancellation
