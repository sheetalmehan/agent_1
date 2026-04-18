"""
Dead stock / pricing health detector — Jupiter World data.
Since we have no sales data, we use:
  - discount depth (high discount = might be stuck)
  - price vs original (no original_price = might be new/untested)
  - category spread (single-category store is riskier per product)
  
  Key changes from v1:
  - Excludes services category (Jupiter Care+)
  - Adjusted discount thresholds: some products genuinely have 60-70% off as
    a marketing strategy (Misting Fan, Turbo Fan) — we flag but explain context
  - Added ultra-low price + COD risk flag (Rs499 products will lose money on RTO)
  - No-original-price handling for Foldable Kettle
"""
from graph.state import AgentState

EXCLUDED_CATEGORIES = {"services"}

def _price(p: dict) -> float:
    try:
        return float(p.get("price", 0))
    except (ValueError, TypeError):
        return 0.0

def _orig(p: dict) -> float:
    try:
        v = p.get("original_price")
        return float(v) if v else 0.0
    except (ValueError, TypeError):
        return 0.0

def _discount_pct(p: dict) -> int:
    price = _price(p)
    orig  = _orig(p)
    if orig > price > 0:
        return int(((orig - price) / orig) * 100)
    return 0    

def dead_stock_agent(state: AgentState) -> AgentState:
    findings = []
 
    for product in state["products"]:
        # Skip service products entirely
        if product.get("category") in EXCLUDED_CATEGORIES:
            continue
 
        title    = product.get("title", "Unknown")
        price    = _price(product)
        orig     = _orig(product)
        category = product.get("category", "")
        score    = 0
        signals  = []
 
        # ── No original price ─────────────────────────────────────────────────
        if orig == 0:
            score += 1
            signals.append("no MRP listed — hard to show value to customer")
 
        # ── Discount depth ────────────────────────────────────────────────────
        elif orig > 0:
            pct = _discount_pct(product)
 
            if pct >= 60:
                # Very heavy — flag but note it may be intentional
                score += 2
                signals.append(
                    f"{pct}% off MRP — extreme discount. "
                    "Check if this is intentional positioning or a pricing error."
                )
            elif pct >= 40:
                score += 2
                signals.append(f"{pct}% off MRP — heavy discount, monitor sales closely")
            elif pct >= 25:
                score += 1
                signals.append(f"{pct}% off MRP — moderate discount")
 
        # ── Ultra-low price COD risk ──────────────────────────────────────────
        # At Rs499 or below, a single COD RTO (forward + return shipping ~Rs160)
        # wipes out nearly all margin. Flag these specifically.
        if price <= 499:
            score += 3
            signals.append(
                f"₹{int(price)} — CRITICAL: one COD return wipes margin. "
                "Force prepaid or add COD surcharge."
            )
        elif price <= 799:
            score += 2
            signals.append(
                f"₹{int(price)} — low price. COD RTO is high risk. "
                "Consider prepaid-only or minimum order for COD."
            )
        elif price < 1500:
            score += 1
            signals.append(f"₹{int(price)} — thin margin, verify RTO economics")
 
        # ── High price in impulse category ───────────────────────────────────
        if price > 4000 and category in ("gadgets", "health"):
            score += 1
            signals.append(f"₹{int(price)} — high for impulse gadget category, needs strong social proof")
 
        if score < 2:
            continue
 
        # ── Recommendation ────────────────────────────────────────────────────
        if price <= 499:
            urgency = "high"
            recommendation = (
                "Switch to prepaid-only for this product OR add ₹50–80 COD surcharge. "
                "A single return at this price point is a net loss."
            )
        elif score >= 5:
            urgency = "high"
            recommendation = "Review pricing and COD policy urgently. Bundle with higher-margin product."
        elif score >= 3:
            urgency = "medium"
            recommendation = "Monitor sales velocity. If slow, bundle with a top seller."
        else:
            urgency = "low"
            recommendation = "No immediate action. Keep watching."
 
        findings.append({
            "title":          title,
            "price":          price,
            "original_price": orig,
            "category":       category,
            "discount_pct":   _discount_pct(product),
            "risk_score":     score,
            "signals":        signals,
            "recommendation": recommendation,
            "urgency":        urgency,
        })
 
    findings.sort(key=lambda x: x["risk_score"], reverse=True)
    return {**state, "dead_stock_findings": findings}