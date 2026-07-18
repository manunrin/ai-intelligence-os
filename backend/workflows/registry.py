"""Pipeline registry — direct imports of compiled LangGraph builders.

Replaces the previous string-based PIPELINE_MAP + importlib resolution
so that typos are caught at import time rather than runtime.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    PipelineFactory = Callable[..., Any]

from .graph.builder import compile_intelligence_graph
from .autonomous_intelligence import compile_autonomous_intelligence

PIPELINE_REGISTRY: dict[str, "PipelineFactory"] = {
    "intelligence": compile_intelligence_graph,
    "autonomous": compile_autonomous_intelligence,
}
