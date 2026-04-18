"""
LangGraph graph — Phase 1.
Linear flow: load → bundle → inventory → dead_stock → competitive → END
Easy to add new agent nodes later without changing existing ones.
"""
from langgraph.graph import StateGraph, END
from graph.state import AgentState
from features.bundling     import bundle_agent
from features.inventory   import inventory_agent
from features.dead_stock  import dead_stock_agent
from features.competitive import competitive_agent

def build_graph():
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("bundle_agent",      bundle_agent)
    graph.add_node("inventory_agent",   inventory_agent)
    graph.add_node("dead_stock_agent",  dead_stock_agent)
    graph.add_node("competitive_agent", competitive_agent)

    # Linear flow — each agent passes enriched state to next
    graph.set_entry_point("bundle_agent")
    graph.add_edge("bundle_agent",      "inventory_agent")
    graph.add_edge("inventory_agent",   "dead_stock_agent")
    graph.add_edge("dead_stock_agent",  "competitive_agent")
    graph.add_edge("competitive_agent", END)

    return graph.compile()

# ---------------------------------------------------------------------------
# Later when you add Shopify live data — just add one node before bundle_agent:
#
#   graph.add_node("shopify_loader", shopify_loader_node)
#   graph.set_entry_point("shopify_loader")
#   graph.add_edge("shopify_loader", "bundle_agent")
#
# Everything else stays the same.
# ---------------------------------------------------------------------------