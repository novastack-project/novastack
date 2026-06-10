from contextvars import ContextVar
from typing import Optional

from novastack_instrumentation.span.base import BaseSpan, Span

# ContextVar for managing active spans
_active_span_id: ContextVar[Optional[str]] = ContextVar("_active_span_id", default=None)
_active_span_id.set(None)

__all__ = ["BaseSpan", "Span", "_active_span_id"]
