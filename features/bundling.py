"""
Bundle detector — tailored for Jupiter World product data.
Uses category field + keyword matching on title.
No Shopify variants/tags needed — works purely from scraped JSON.
"""
from itertools import combinations
from graph.state import AgentState

# Which category pairs make sense as bundles
CATEGORY_AFFINITY = {
    ("health", "health"),       "Complete wellness kit",
    ("kitchen", "kitchen"),     "Kitchen essentials combo",
    ("home_decor", "gadgets"),  "Smart home bundle",
    ("home_decor", "home_decor"), "Home decor duo",
    ("health", "gadgets"),      "Smart health bundle",
    ("kitchen", "gadgets"),     "Smart kitchen combo",
    ("cleaning", "kitchen"),    "Home care bundle",
}

# Keyword pairs that always make sense together regardless of category
KEYWORD_AFFINITY = [
    (["massager", "massage", "relief", "relaxwave", "bionic"], 
     ["massager", "massage", "relief", "relaxwave", "bionic"]),
    (["kettle", "warming", "wine", "kitchen"],
     ["kettle", "warming", "wine", "kitchen"]),
    (["lamp", "frame", "decor", "bear", "alarm"],
     ["lamp", "frame", "decor", "bear", "alarm"]),
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

def _discount_pct(p: dict) -> int:
    price = _price(p)
    orig  = _orig_price(p)
    if orig > price > 0:
        return int(((orig - price) / orig) * 100)
    return 0

def _are_compatible(p1: dict, p2: dict) -> tuple[bool, str]:
    """Return (compatible, reason_label)."""
    c1 = p1.get("category", "")
    c2 = p2.get("category", "")
    t1 = _text(p1)
    t2 = _text(p2)

    # Same category (except cleaning paired alone looks odd)
    if c1 == c2 and c1 not in ("", "cleaning"):
        labels = {
            "health":     "Complete wellness kit",
            "kitchen":    "Kitchen essentials combo",
            "home_decor": "Home decor duo",
            "gadgets":    "Smart gadget bundle",
        }
        return True, labels.get(c1, "Product bundle")

    # Cross-category affinities
    cross = {
        frozenset(["home_decor", "gadgets"]): "Smart home bundle",
        frozenset(["health", "gadgets"]):     "Smart health bundle",
        frozenset(["kitchen", "gadgets"]):    "Smart kitchen combo",
        frozenset(["cleaning", "kitchen"]):   "Home care bundle",
        frozenset(["cleaning", "home_decor"]):"Home essentials bundle",
    }
    key = frozenset([c1, c2])
    if key in cross:
        return True, cross[key]

    # Keyword fallback
    for group in KEYWORD_AFFINITY:
        a_words, b_words = group
        if (any(w in t1 for w in a_words) and any(w in t2 for w in b_words)) or \
           (any(w in t2 for w in a_words) and any(w in t1 for w in b_words)):
            return True, "Complementary products"

    return False, ""

def bundle_agent(state: AgentState) -> AgentState:
    products = state["products"]
    bundles  = []
    seen     = set()

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

        # Bundle discount: 10% off combined price
        bundle_price = round(total * 0.90)
        saving       = round(total - bundle_price)

        # Show how much vs original MRP
        orig_total = _orig_price(p1) + _orig_price(p2)
        saving_vs_mrp = round(orig_total - bundle_price)

        d1 = _discount_pct(p1)
        d2 = _discount_pct(p2)
        avg_discount = round((d1 + d2) / 2)

        bundles.append({
            "bundle_type":      label,
            "product_1":        p1["title"],
            "product_2":        p2["title"],
            "price_1":          price1,
            "price_2":          price2,
            "combined_price":   total,
            "bundle_price":     bundle_price,
            "saving":           saving,
            "saving_vs_mrp":    saving_vs_mrp,
            "avg_discount":     avg_discount,
            "pitch": (
                f"Get {p1['title']} + {p2['title']} together for ₹{int(bundle_price)} "
                f"— save ₹{int(saving_vs_mrp)} vs buying separately at MRP"
            ),
        })

    bundles.sort(key=lambda x: x["saving_vs_mrp"], reverse=True)
    return {**state, "bundle_findings": bundles[:8]}