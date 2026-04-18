"""
app.py — Jupiter World AI Business Ops Demo
Run: streamlit run app.py
"""
import streamlit as st
import pandas as pd
from pipeline import run_pipeline, load_products

st.set_page_config(
    page_title="Jupiter World — AI Ops",
    page_icon="",
    layout="wide"
)

# ── Header ───────────────────────────────────────────────────────────────────
st.title("Jupiter World — AI Business Ops")
st.caption("Phase 1 · Built on scraped product data  ·  Shopify API ready")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Controls")

    st.markdown("**Data source**")
    st.success("Scraped JSON — jupiterworld.in", icon="✅")
    st.divider()
    products_raw = load_products()
    titles = [p["title"] for p in products_raw]
    selected = st.selectbox(
        "Product for competitive analysis",
        titles,
        index=0
    )

    st.divider()
    run_btn = st.button("Run all agents", type="primary", use_container_width=True)

    st.divider()
    st.caption("Phase 2 upgrade")
    st.info(
    "Connect Shopify API to get live stock, order history, and real sales velocity.",
    icon="🔗"
)
# ── Run agents ────────────────────────────────────────────────────────────────
if run_btn or "state" not in st.session_state:
    with st.spinner("Running AI agents across Jupiter World catalogue..."):
        try:
            st.session_state.state = run_pipeline(selected_product=selected)
        except Exception as e:
            st.error(f"Pipeline error: {e}")
            st.stop()

state = st.session_state.get("state", {})
if not state:
    st.stop()

products       = state["products"]
bundles        = state["bundle_findings"]
inventory      = state["inventory_findings"]
dead           = state["dead_stock_findings"]
competitive    = state["competitive_findings"]

# ── Metric strip ──────────────────────────────────────────────────────────────
def _p(p):
    try:
        price = float(p.get("price",0))
        orig  = float(p.get("original_price") or price)
        return int(((orig-price)/orig)*100) if orig > price > 0 else 0
    except:
        return 0
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Products", len(products))
m2.metric("Bundle opportunities", len(bundles))
m3.metric("Needs attention", len([x for x in inventory if x["urgency"] in ("critical","warning")]))
m4.metric("Pricing risk", len([x for x in dead if x["urgency"] in ("high","medium")]))
m5.metric("Avg discount", f"{int(sum(_p(p) for p in products)/len(products))}%" if products else "—")


st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    " Bundle Detector",
    " Inventory & Pricing",
    " Pricing Risk",
    " Competitive Edge"
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — BUNDLES
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Bundle opportunities")
    st.caption("Products from your catalogue that should be sold together to increase average order value")

    if not bundles:
        st.info("No bundles detected. Try adding more products with category tags.")
    else:
        for b in bundles:
            with st.container(border=True):
                col_l, col_r = st.columns([3, 2])
                with col_l:
                    st.markdown(f"**{b['bundle_type']}**")
                    st.markdown(f"{b['product_1']}  +  {b['product_2']}")
                    st.caption(b["pitch"])
                with col_r:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Combined", f"₹{int(b['combined_price'])}")
                    c2.metric("Bundle price", f"₹{int(b['bundle_price'])}")
                    c3.metric("Customer saves", f"₹{int(b['saving_vs_mrp'])}", delta="vs MRP", delta_color="normal")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — INVENTORY
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Inventory & discount health")

    has_live = any(f.get("data_source") == "live" for f in inventory)
    if not has_live:
        st.info(
            "**Phase 1:** No live stock counts yet — showing discount depth analysis as proxy signal.  \n"
            "**Phase 2:** Connect Shopify API → get real stock levels, days-to-stockout, and auto reorder messages.",
            icon="📊"
        )

    # Summary table
    rows = []
    for f in inventory:
        disc = f.get("discount", 0)
        rows.append({
            "Product":   f["title"],
            "Price":     f"₹{int(f['price'])}",
            "Discount":  f"{disc}%" if disc else "—",
            "Stock":     f["stock"],
            "Status":    f["status"],
            "Action":    f["action"],
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("**Products needing attention**")
    for f in inventory:
        if f["urgency"] in ("warning", "critical"):
            with st.container(border=True):
                st.markdown(f"**{f['title']}** — `{f['status']}`")
                st.warning(f["action"])

                if f["data_source"] == "live" and f.get("reorder_qty", 0) > 0:
                    wa = f"Hi, please send *{f['reorder_qty']} units* of *{f['title']}* urgently."
                    st.code(wa, language=None)
                    st.caption("Copy → send to supplier on WhatsApp")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — DEAD STOCK / PRICING RISK
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Pricing risk detector")
    st.caption("Products where current pricing strategy could be hurting profit or conversions")

    if not dead:
        st.success("All products look healthy from a pricing perspective.")
    else:
        ICON = {"high": "", "medium": "", "low": ""}
        for d in dead:
            icon = ICON.get(d["urgency"], "")
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 1, 1])
                with c1:
                    st.markdown(f"{icon} **{d['title']}**")
                    st.caption("Signals: " + " · ".join(d["signals"]))
                with c2:
                    st.metric("Price", f"₹{int(d['price'])}")
                with c3:
                    orig = d.get("original_price", 0)
                    st.metric("MRP", f"₹{int(orig)}" if orig else "—")

                if d["urgency"] == "high":
                    st.error(f"Recommendation: {d['recommendation']}")
                elif d["urgency"] == "medium":
                    st.warning(f"Recommendation: {d['recommendation']}")
                else:
                    st.info(f"Recommendation: {d['recommendation']}")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — COMPETITIVE EDGE
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("Competitive edge analysis")
    st.caption("AI strategy to beat competitors — powered by Claude · Select a product in the sidebar")

    if not competitive:
        st.info("Select a product and click Run all agents.")
    else:
        finding = competitive[0]
        if "error" in finding:
            st.error(f"Claude API error: {finding['error']}")
            st.code("export ANTHROPIC_API_KEY=sk-ant-xxxx", language="bash")
            st.caption("Set the key above then re-run.")
        else:
            col1, col2 = st.columns([1, 1])
            with col1:
                st.metric("Product", finding["title"])
            with col2:
                orig = finding.get("orig")
                if orig:
                    pct = int(((float(orig) - float(finding["price"])) / float(orig)) * 100)
                    st.metric("Listed price", f"₹{finding['price']}", delta=f"{pct}% off MRP", delta_color="normal")
                else:
                    st.metric("Listed price", f"₹{finding['price']}")

            st.divider()
            st.markdown(finding["strategy"])