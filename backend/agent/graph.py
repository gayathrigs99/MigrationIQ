"""LangGraph definition of the migration workflow.

analyze -> retrieve -> convert -> validate -> (pass | retries exhausted) -> build_report
                                      |
                                      +-- failed, retries left --> convert
"""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agent.nodes import ANALYZE, CONVERT, REPORT, RETRIEVE, VALIDATE, MigrationNodes
from agent.state import MigrationState
from schemas.migration import MigrationResult


def build_migration_graph(nodes: MigrationNodes) -> CompiledStateGraph:
    graph = StateGraph(MigrationState)

    graph.add_node(ANALYZE, nodes.analyze)
    graph.add_node(RETRIEVE, nodes.retrieve)
    graph.add_node(CONVERT, nodes.convert)
    graph.add_node(VALIDATE, nodes.validate)
    graph.add_node(REPORT, nodes.build_report)

    graph.add_edge(START, ANALYZE)
    graph.add_edge(ANALYZE, RETRIEVE)
    graph.add_edge(RETRIEVE, CONVERT)
    graph.add_edge(CONVERT, VALIDATE)
    graph.add_conditional_edges(
        VALIDATE, nodes.route_after_validation, {CONVERT: CONVERT, REPORT: REPORT}
    )
    graph.add_edge(REPORT, END)

    return graph.compile()


def run_migration(graph: CompiledStateGraph, oracle_sql: str) -> MigrationResult:
    final_state = graph.invoke({"source_sql": oracle_sql, "attempts": 0})
    return final_state["result"]
