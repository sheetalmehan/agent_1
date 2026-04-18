"""
Competitive edge finder — Jupiter World specific.
Knows the store sells premium lifestyle gadgets.
Calls Claude API with real product context.
"""
from graph.state import AgentState
from utils.llms import call_llm

STORE_CONTEXT = """
Store: Jupiter World (jupiterworld.in)
Niche: Premium lifestyle gadgets and home products for Indian market
Price range: ₹999 – ₹4999
Positioning: Innovative, gift-worthy products with heavy discounts vs MRP
Competitors: Amazon India, Flipkart, AliExpress resellers, Instagram gadget stores
Customer profile: Urban Indian, 25–40 age group, buys gifts and home upgrades
Main challenge: Standing out in a crowded gadget dropshipping market
"""

def competitive_agent(state: AgentState) -> AgentState:
    selected_title = state.get("selected_product", "")
    products       = state["products"]

    product = next(
        (p for p in products if p["title"] == selected_title),
        products[0] if products else None
    )
    if not product:
        return {**state, "competitive_findings": [{"error": "No product found"}]}

    title    = product.get("title", "")
    price    = product.get("price", "N/A")
    orig     = product.get("original_price", None)
    category = product.get("category", "")
    link     = product.get("link", "")

    discount_line = ""
    if orig:
        pct = int(((float(orig) - float(price)) / float(orig)) * 100)
        discount_line = f"Currently listed at ₹{price} vs MRP ₹{orig} ({pct}% off)"
    else:
        discount_line = f"Listed at ₹{price} (no MRP set)"

    prompt = f"""
You are a ruthless Indian D2C growth strategist who understands dropshipping deeply.

{STORE_CONTEXT}

REAL COMPETITOR LANDSCAPE (IMPORTANT CONTEXT):

1. Marketplaces:
- Amazon India, Flipkart, Banggood
(cheap listings, fake reviews, price wars)

2. Dropshipping suppliers:
- AliExpress, CJ Dropshipping, Zendrop, Spocket
(slow shipping, inconsistent quality, generic products)

3. Indian dropshipping ecosystem:
- Meesho, GlowRoad, BaapStore, IndiaMART
(COD-heavy, high RTO, low branding, fast delivery)

ASSUME:
- Customer has already seen similar products on Amazon/Instagram
- Trust issues are HIGH
- COD is preferred
- Product is NOT unique (only positioning can win)

---

Product:
- Title: {title}
- Category: {category}
- {discount_line}
- Price: ₹{price}
- URL: {link}

---

STRICT RULES:
- No generic advice
- Every point must reference REAL marketplace or dropshipping failure patterns
- Use India-specific psychology (COD hesitation, RTO, fake reviews, cheap imports)
- Be brutally honest like a founder advisor

---

BETTER PRODUCT TITLE
Rewrite using:
- High search intent keyword (Amazon-style)
- + One emotional/gifting hook

---

TOP 3 COMPETITOR WEAKNESSES TO EXPLOIT

1. Amazon/Flipkart weakness:
   (e.g. fake ratings, poor durability, misleading specs)

2. AliExpress/dropshipping weakness:
   (e.g. 15-20 day delivery, inconsistent quality)

3. Indian reseller weakness:
   (e.g. poor packaging, no branding, high RTO)

---

YOUR UNIQUE ANGLE (ONE ONLY)
Must be DEFENSIBLE vs all 3 layers above.

Bad example: “best quality”
Good example: “3-day replacement + gift-ready packaging”

---

PRICING VERDICT

Take a STRONG stand:
- Underpriced / Correct / Overpriced

Justify using:
- Amazon price band
- Dropshipping cost reality
- COD + RTO economics

---

3 LISTING BULLET POINTS

Each must:
- Remove a buying fear
- Attack a competitor weakness
- Be short (max 12 words)

---

GIFT ANGLE

Make it feel like:
- Premium gift (NOT cheap gadget)
- Indian occasion focused

---

WHATSAPP MESSAGE TO SUPPLIER

Ask for:
- 2 PROOF-based differentiators
- (materials, durability, certification, packaging)

Sound like a serious bulk buyer.
"""
    try:
        strategy = call_llm(prompt, max_tokens=900)
        findings = [{"title": title, "price": price, "orig": orig,
                     "category": category, "strategy": strategy}]
    except Exception as e:
        findings = [{"error": str(e), "title": title, "strategy": ""}]

    return {**state, "competitive_findings": findings}