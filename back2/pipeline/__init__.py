"""Three-phase pipeline: analyze → search → fill.

`DocumentFirstWorkflow` runs all three back-to-back; the individual phases
are exposed too so the API can drive them step-by-step.
"""

from back2.pipeline.analyzer import DocumentAnalyzer
from back2.pipeline.searcher import ContextSearcher
from back2.pipeline.workflow import DocumentFirstWorkflow, main_workflow

__all__ = [
    "ContextSearcher",
    "DocumentAnalyzer",
    "DocumentFirstWorkflow",
    "main_workflow",
]
