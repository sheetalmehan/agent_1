"""
pipeline.py — entry point called by Streamlit.
Loads JSON, runs LangGraph, returns final state.
"""
import json
import os
from pathlib import Path
from graph.graph  import build_graph
from graph.state  import AgentState

DATA_PATH = Path(__file__).parent / "data" / "products.json"

def load_products(path: str = None) -> list[dict]:
    """
    Load products from JSON file.
    Handles both formats:
      - {"products": [...]}   (Shopify API format)
      - [...]                 (flat array from scraper)
    """
    file_path = path or DATA_PATH
    with open(file_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        # Shopify wraps in {"products": [...]}
        for key in ["products", "data", "items", "results"]:
            if key in raw:
                return raw[key]
    return []

def run_pipeline(selected_product: str = "", data_path: str = None) -> AgentState:
    products = load_products(data_path)

    if not products:
        raise ValueError("No products loaded. Check your JSON file path and structure.")

    initial_state: AgentState = {
        "products":             products,
        "bundle_findings":      [],
        "inventory_findings":   [],
        "dead_stock_findings":  [],
        "competitive_findings": [],
        "selected_product":     selected_product or (products[0]["title"] if products else ""),
        "errors":               [],
    }

    graph = build_graph()
    final_state = graph.invoke(initial_state)
    return final_state

if __name__ == "__main__":
    state = run_pipeline()
    print(f"Products loaded: {len(state['products'])}")
    print(f"Bundles found:   {len(state['bundle_findings'])}")
    print(f"Inventory flags: {len([x for x in state['inventory_findings'] if x['urgency'] != 'ok'])}")
    print(f"Dead stock:      {len(state['dead_stock_findings'])}")