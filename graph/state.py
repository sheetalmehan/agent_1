from typing import TypedDict, Any

class AgentState(TypedDict):
    products: list[dict]          # raw scraped / shopify products
    bundle_findings: list[dict]   # output from bundle agent
    inventory_findings: list[dict]
    dead_stock_findings: list[dict]
    competitive_findings: list[dict]
    selected_product: str         # for competitive agent — set by UI
    errors: list[str]