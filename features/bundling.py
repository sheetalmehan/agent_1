"""
Bundle detector — Jupiter World product data.
Updated for 20-product catalogue with new fan/cooling cluster.
Excludes services category. Handles fan-fan, massager-massager groupings.
"""
from itertools import combinations
from graph.state import AgentState

# Never bundle these categories
EXCLUDED_CATEGORIES = {"services"}

# Cross-category pairs that make sense
CROSS = {
    frozenset(["home_decor", "gadgets"]):   "Smart home bundle",
    frozenset(["health", "gadgets"]):       "Smart health bundle",
    frozenset(["kitchen", "gadgets"]):      "Smart kitchen combo",
    frozenset(["cleaning", "kitchen"]):     "Home care bundle",
    frozenset(["cleaning", "home_decor"]):  "Home essentials bundle",
    frozenset(["cleaning", "health"]):      "Personal care bundle",
}

# Keyword groups — products sharing keywords get bundled within or across categories
KEYWORD_GROUPS = [
    (["massager", "massage", "relief", "relaxwave", "bionic", "airthera", "handheld massager"],
     "Complete wellness kit"),
    (["fan", "cooler", "misting", "cooling", "turbo fan", "handheld fan", "air cooler"],
     "Beat-the-heat bundle"),
    (["kettle", "freshblend", "blender", "warming mat", "wine"],
     "Kitchen essentials combo"),
    (["lamp", "smartmemory", "bear alarm", "frame"],
     "Home decor duo"),
]

def _text(p: dict) -> str:
    return (p.get("title", "") + " " + p.get("category", "")).lower()

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

def _is_excluded(p: dict) -> bool:
    return p.get("category", "") in EXCLUDED_CATEGORIES

def _are_compatible(p1: dict, p2: dict) -> tuple[bool, str]:
    if _is_excluded(p1) or _is_excluded(p2):
        return False, ""

    c1 = p1.get("category", "")
    c2 = p2.get("category", "")
    t1 = _text(p1)
    t2 = _text(p2)

    # Same category — always compatible (except cleaning alone)
    if c1 == c2 and c1 not in ("", "cleaning"):
        labels = {
            "health":     "Complete wellness kit",
            "kitchen":    "Kitchen essentials combo",
            "home_decor": "Home decor duo",
            "gadgets":    "Smart gadget bundle",
        }
        return True, labels.get(c1, "Product bundle")

    # Cross-category rules
    key = frozenset([c1, c2])
    if key in CROSS:
        return True, CROSS[key]

    # Keyword group matching
    for keywords, label in KEYWORD_GROUPS:
        t1_match = any(kw in t1 for kw in keywords)
        t2_match = any(kw in t2 for kw in keywords)
        if t1_match and t2_match:
            return True, label

    return False, ""

def bundle_agent(state: AgentState) -> AgentState:
    # Filter out service products before processing
    products = [p for p in state["products"] if not _is_excluded(p)]

    bundles = []
    seen    = set()

    for p1, p2 in combinations(products, 2):
        compatible, label = _are_compatible(p1, p2)
        if not compatible:
            continue

        key = tuple(sorted([p1["title"], p2["title"]]))
        if key in seen:
            continue
        seen.add(key)

        price1 = _price(p1)
        price2 = _price(p2)
        total  = price1 + price2

        bundle_price  = round(total * 0.90)
        saving        = round(total - bundle_price)
        orig_total    = _orig_price(p1) + _orig_price(p2)
        saving_vs_mrp = round(orig_total - bundle_price)

        bundles.append({
            "bundle_type":    label,
            "product_1":      p1["title"],
            "product_2":      p2["title"],
            "price_1":        price1,
            "price_2":        price2,
            "combined_price": total,
            "bundle_price":   bundle_price,
            "saving":         saving,
            "saving_vs_mrp":  saving_vs_mrp,
            "pitch": (
                f"Get both for ₹{int(bundle_price)} "
                f"— save ₹{int(saving_vs_mrp)} vs buying separately at MRP"
            ),
        })

    bundles.sort(key=lambda x: x["saving_vs_mrp"], reverse=True)
    return {**state, "bundle_findings": bundles[:10]}