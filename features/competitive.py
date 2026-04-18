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

    prompt = f"""You are a competitive strategy expert for Indian D2C and dropshipping stores.

{STORE_CONTEXT}

Product to analyse:
- Title: {title}
- Category: {category}
- {discount_line}
- Product URL: {link}

Give a sharp, India-specific competitive strategy. Be concrete — not generic.

Format exactly as follows:

BETTER PRODUCT TITLE
Write one improved title (under 80 chars) that is more searchable and conversion-friendly for Indian buyers.

TOP 3 COMPETITOR WEAKNESSES TO EXPLOIT
(Common pain points Indian customers have with similar products on Amazon/Flipkart)
1. [specific, India-relevant weakness]
2. [specific, India-relevant weakness]
3. [specific, India-relevant weakness]

YOUR UNIQUE ANGLE
One specific claim Jupiter World can make for this product that most competitors cannot. Make it concrete.

PRICING VERDICT
Is ₹{price} the right price for this product in the Indian market? Should it go higher, lower, or stay? One paragraph, specific reasoning including COD and RTO risk.

3 LISTING BULLET POINTS TO ADD
Bullet points that directly address competitor weaknesses. Ready to copy-paste into the product page.

GIFT ANGLE
This store sells premium gifts. Write one gift-positioning line for this product (for Diwali / birthday / anniversary).

WHATSAPP MESSAGE TO SUPPLIER
A short message asking the supplier to confirm 2 quality points that differentiate this product from cheap alternatives."""

    try:
        strategy = call_llm(prompt, max_tokens=900)
        findings = [{"title": title, "price": price, "orig": orig,
                     "category": category, "strategy": strategy}]
    except Exception as e:
        findings = [{"error": str(e), "title": title, "strategy": ""}]

    return {**state, "competitive_findings": findings}