"""
Inventory risk agent — Jupiter World data.

Phase 1 (scraped data): No live stock counts available.
We use discount depth as a proxy signal — heavy discounts often mean
the owner is trying to clear stock, which could mean overstock OR
it could be a pricing strategy. We flag these for manual review.

Phase 2 (Shopify API): swap _get_stock() body to call inventory_levels.json
Everything else stays identical.
"""
from graph.state import AgentState

def _price(p: dict) -> float:
    try:
        return float(p.get("price", 0))
    except (ValueError, TypeError):
        return 0.0

def _orig_price(p: dict) -> float:
    try:
        v = p.get("original_price")
        return float(v) if v else _price(p)
    except (ValueError, TypeError):
        return _price(p)

def _get_stock(product: dict) -> int:
    """
    Phase 1: No stock data in scraped JSON — return -1 (unknown).
    Phase 2: Replace this entire function body with:
        res = shopify_client.get(f"/inventory_levels.json?inventory_item_ids={item_id}")
        return res["inventory_levels"][0]["available"]
    """
    for field in ["inventory_quantity", "stock", "qty", "quantity", "stock_quantity"]:
        val = product.get(field)
        if val is not None:
            try:
                return int(val)
            except (ValueError, TypeError):
                continue
    for v in product.get("variants", []):
        qty = v.get("inventory_quantity")
        if qty is not None:
            try:
                return int(qty)
            except (ValueError, TypeError):
                continue
    return -1   # unknown — scraped data has no stock field

def _discount_pct(p: dict) -> int:
    price = _price(p)
    orig  = _orig_price(p)
    if orig > price > 0:
        return int(((orig - price) / orig) * 100)
    return 0

def inventory_agent(state: AgentState) -> AgentState:
    findings = []

    for product in state["products"]:
        stock       = _get_stock(product)
        price       = _price(product)
        orig        = _orig_price(product)
        discount    = _discount_pct(product)
        title       = product.get("title", "Unknown")
        category    = product.get("category", "")

        if stock != -1:
            # Real stock data available (Phase 2)
            LEAD = 3
            BUFFER = 2
            est_daily = 1.0
            days_left = round(stock / est_daily, 1) if est_daily else 999

            if stock == 0:
                urgency = "critical"
                status  = "OUT OF STOCK"
                action  = f"Reorder immediately. Suggest 20 units."
            elif days_left <= LEAD:
                urgency = "critical"
                status  = "CRITICAL"
                action  = f"Order today — only {days_left} days left."
            elif days_left <= LEAD + BUFFER:
                urgency = "warning"
                status  = "WARNING"
                action  = f"Reorder within 2 days. {days_left} days left."
            else:
                urgency = "ok"
                status  = "OK"
                action  = "No action needed."

            findings.append({
                "title":       title,
                "stock":       stock,
                "days_left":   days_left,
                "status":      status,
                "urgency":     urgency,
                "action":      action,
                "discount":    discount,
                "price":       price,
                "data_source": "live",
            })

        else:
            # Phase 1 — no stock data. Use discount as proxy signal.
            if orig == price or orig == 0:
                urgency = "no_data"
                status  = "NO STOCK DATA"
                action  = "Connect Shopify API to see live stock levels."
            elif discount >= 50:
                urgency = "warning"
                status  = "HEAVY DISCOUNT"
                action  = f"{discount}% off MRP — possible overstock or clearance. Verify with supplier."
            elif discount >= 30:
                urgency = "low"
                status  = "DISCOUNTED"
                action  = f"{discount}% off MRP — monitor sales velocity."
            else:
                urgency = "ok"
                status  = "NORMAL PRICING"
                action  = "Standard discount. No action needed."

            findings.append({
                "title":       title,
                "stock":       "unknown",
                "days_left":   "—",
                "status":      status,
                "urgency":     urgency,
                "action":      action,
                "discount":    discount,
                "price":       price,
                "data_source": "scraped",
            })

    order = {"critical": 0, "warning": 1, "low": 2, "ok": 3, "no_data": 4}
    findings.sort(key=lambda x: order.get(x["urgency"], 5))
    return {**state, "inventory_findings": findings}