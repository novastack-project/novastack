from contextvars import ContextVar
from typing import Optional

from novastack_instrumentation.span.base import BaseSpan, Span

# ContextVar for managing active spans
active_span_id: ContextVar[Optional[str]] = ContextVar("active_span_id", default=None)
active_span_id.set(None)

__all__ = ["BaseSpan", "Span", "active_span_id"]
