"""
Dead stock / pricing health detector — Jupiter World data.
Since we have no sales data, we use:
  - discount depth (high discount = might be stuck)
  - price vs original (no original_price = might be new/untested)
  - category spread (single-category store is riskier per product)
"""
from graph.state import AgentState

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

def dead_stock_agent(state: AgentState) -> AgentState:
    findings = []

    for product in state["products"]:
        title    = product.get("title", "Unknown")
        price    = _price(product)
        orig     = _orig(product)
        category = product.get("category", "")
        score    = 0
        signals  = []

        # No original price — product may be new or underpriced
        if orig == 0:
            score += 1
            signals.append("no MRP set — hard to show value")

        # Very heavy discount — may indicate stuck stock or wrong pricing
        elif orig > 0:
            pct = int(((orig - price) / orig) * 100)
            if pct >= 50:
                score += 3
                signals.append(f"{pct}% discount — very heavy, may signal stuck stock")
            elif pct >= 35:
                score += 2
                signals.append(f"{pct}% discount — high, monitor sales")
            elif pct >= 20:
                score += 1
                signals.append(f"{pct}% discount — moderate")

        # Low absolute price — thin margin, risky for COD + RTO
        if price < 1500:
            score += 2
            signals.append(f"₹{int(price)} — low price, COD RTO could wipe margin")

        # Very high price for gadget store — impulse category
        if price > 4000:
            score += 1
            signals.append(f"₹{int(price)} — high price, harder impulse buy")

        if score < 2:
            continue

        if score >= 5:
            urgency = "high"
            recommendation = "Review pricing strategy. If not selling, bundle with lower-priced item or run targeted ad."
        elif score >= 3:
            urgency = "medium"
            recommendation = "Monitor for 2 weeks. If no traction, try bundling or discounting further."
        else:
            urgency = "low"
            recommendation = "Keep an eye on it. No immediate action needed."

        findings.append({
            "title":          title,
            "price":          price,
            "original_price": orig,
            "category":       category,
            "risk_score":     score,
            "signals":        signals,
            "recommendation": recommendation,
            "urgency":        urgency,
        })

    findings.sort(key=lambda x: x["risk_score"], reverse=True)
    return {**state, "dead_stock_findings": findings}