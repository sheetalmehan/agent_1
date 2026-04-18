"""
Inventory risk agent — Jupiter World data.

Phase 1 (scraped data): No live stock counts available.
We use discount depth as a proxy signal — heavy discounts often mean
the owner is trying to clear stock, which could mean overstock OR
it could be a pricing strategy. We flag these for manual review.

Phase 2 (Shopify API): swap _get_stock() body to call inventory_levels.json
Everything else stays identical.

Changes from v1:
  - Excludes services category
  - Groups fan/cooling products — flags seasonal risk (summer products, demand drops Oct-Feb)
  - Handles null original_price for Foldable Kettle
  - Rs499 products get a special COD margin warning alongside discount signal
"""
from graph.state import AgentState

EXCLUDED_CATEGORIES = {"services"}
 
# Products/keywords that are seasonal — flag if it's off-season
SEASONAL_KEYWORDS = ["fan", "cooler", "misting", "cooling"]

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

def _is_seasonal(p: dict) -> bool:
    t = p.get("title", "").lower()
    return any(kw in t for kw in SEASONAL_KEYWORDS)

def _discount_pct(p: dict) -> int:
    price = _price(p)
    orig  = _orig_price(p)
    if orig > price > 0:
        return int(((orig - price) / orig) * 100)
    return 0

def inventory_agent(state: AgentState) -> AgentState:
    findings = []
 
    for product in state["products"]:
        if product.get("category") in EXCLUDED_CATEGORIES:
            continue
 
        stock    = _get_stock(product)
        price    = _price(product)
        orig     = _orig_price(product)
        discount = _discount_pct(product)
        title    = product.get("title", "Unknown")
        seasonal = _is_seasonal(product)
 
        if stock != -1:
            # Phase 2 — real stock data available
            LEAD, BUFFER = 3, 2
            daily = 1.0
            days_left = round(stock / daily, 1) if daily else 999
 
            if stock == 0:
                urgency, status = "critical", "OUT OF STOCK"
                action = "Reorder immediately. Suggest 20 units."
            elif days_left <= LEAD:
                urgency, status = "critical", "CRITICAL"
                action = f"Order today. Only {days_left} days left."
            elif days_left <= LEAD + BUFFER:
                urgency, status = "warning", "WARNING"
                action = f"Reorder within 2 days. {days_left} days left."
            else:
                urgency, status = "ok", "OK"
                action = "No action needed."
 
            if seasonal:
                action += " [SEASONAL product — check demand before reordering in Oct–Feb]"
 
            findings.append({
                "title": title, "stock": stock, "days_left": days_left,
                "status": status, "urgency": urgency, "action": action,
                "discount": discount, "price": price,
                "seasonal": seasonal, "data_source": "live",
            })
 
        else:
            # Phase 1 — no stock data, use discount + price as proxy signals
            if price <= 499:
                urgency, status = "warning", "MARGIN RISK"
                action = (
                    f"₹{int(price)} with {discount}% discount. "
                    "COD return at this price = net loss. "
                    "Enforce prepaid or add COD surcharge before stocking more."
                )
            elif discount >= 60:
                urgency, status = "warning", "HEAVY DISCOUNT"
                action = (
                    f"{discount}% off MRP. Verify this is intentional. "
                    "If not selling, don't restock until pricing is reviewed."
                )
            elif discount >= 35:
                urgency, status = "low", "DISCOUNTED"
                action = f"{discount}% off MRP — monitor sales before reordering."
            elif orig == price:
                urgency, status = "no_data", "NO DISCOUNT DATA"
                action = "No MRP set. Hard to show value. Consider adding original price."
            else:
                urgency, status = "ok", "NORMAL"
                action = "Standard pricing. No action needed."
 
            if seasonal and urgency in ("ok", "low"):
                action += " [SEASONAL — check month before reordering]"
                urgency = "low"
                status  = "SEASONAL — monitor"
 
            findings.append({
                "title": title, "stock": "unknown", "days_left": "—",
                "status": status, "urgency": urgency, "action": action,
                "discount": discount, "price": price,
                "seasonal": seasonal, "data_source": "scraped",
            })
 
    order = {"critical": 0, "warning": 1, "low": 2, "ok": 3, "no_data": 4}
    findings.sort(key=lambda x: order.get(x["urgency"], 5))
    return {**state, "inventory_findings": findings}