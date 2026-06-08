import inspect
import threading
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional

from pydantic import Field, PrivateAttr
from treelib.tree import Tree

from novastack_telemetry.events import BaseEvent
from novastack_telemetry.observability.base import BaseObservability
from novastack_telemetry.span import Span


class NovastackDebugObservability(BaseObservability):
    """Novastack observability to track debug information (in-memory)."""

    model_config = {"arbitrary_types_allowed": True}
    open_spans: dict[str, Span] = Field(
        default_factory=dict, description="Dictionary of open spans."
    )
    completed_spans: list[Span] = Field(
        default_factory=list, description="List of completed spans."
    )
    dropped_spans: list[Span] = Field(
        default_factory=list, description="List of dropped spans."
    )
    events: list[BaseEvent] = Field(default_factory=list, description="List of events.")
    _lock: Optional[threading.Lock] = PrivateAttr(default=None)

    print_span_on_end: bool = Field(
        default=True,
        description="Automatically print trace tree when a root span completes.",
    )

    @property
    def lock(self) -> threading.Lock:
        if self._lock is None:
            self._lock = threading.Lock()
        return self._lock

    @classmethod
    def class_name(cls) -> str:
        return "NovastackDebugObservability"

    def on_event(self, event: BaseEvent, **kwargs: Any) -> None:
        """Handle an event."""
        with self.lock:
            self.events.append(event)

    def on_span_start(
        self,
        id_: str,
        bound_args: inspect.BoundArguments,
        instance: Any | None = None,
        parent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle span start."""
        span = Span(id_=id_, parent_id=parent_id, metadata=metadata or {})
        with self.lock:
            self.open_spans[id_] = span

    def on_span_end(
        self,
        id_: str,
        bound_args: inspect.BoundArguments,
        instance: Any | None = None,
        result: Any | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle span end."""
        with self.lock:
            span = self.open_spans.pop(id_, None)
            if span:
                span.end_time = datetime.now()
                span.duration = (span.end_time - span.start_time).total_seconds()
                self.completed_spans.append(span)

                # Auto-print trace tree if enabled and this is a root span
                if self.print_span_on_end and span.parent_id is None:
                    self.print_trace_trees(include_events=True)

    def on_span_exception(
        self,
        id_: str,
        bound_args: inspect.BoundArguments,
        instance: Any | None = None,
        err: BaseException | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle span exception."""
        with self.lock:
            span = self.open_spans.pop(id_, None)
            if span:
                span.metadata["error"] = str(err)
                self.dropped_spans.append(span)

    def _get_parents(self) -> list[Span]:
        """Extract root spans from completed and dropped span collections."""
        all_spans = self.completed_spans + self.dropped_spans
        return [s for s in all_spans if s.parent_id is None]

    def _build_spans_by_parent_index(
        self, spans: list[Span]
    ) -> dict[str | None, list[Span]]:
        """Build optimized parent-to-children span index for O(1) hierarchy traversal."""
        spans_by_parent: dict[str | None, list[Span]] = defaultdict(list)
        for span in spans:
            spans_by_parent[span.parent_id].append(span)
        return spans_by_parent

    def _build_tree_by_parent(
        self, parent: Span, spans_by_parent: dict[str | None, list[Span]]
    ) -> list[Span]:
        """Recursively construct flattened span hierarchy using depth-first traversal."""
        result = [parent]
        children = spans_by_parent.get(parent.id_, [])

        for child in children:
            result.extend(self._build_tree_by_parent(child, spans_by_parent))

        return result

    def _get_trace_trees(self, include_events: bool = True) -> list[Tree]:
        """Generate hierarchical tree structures representing execution traces with span durations."""
        all_spans = self.completed_spans + self.dropped_spans
        for s in all_spans:
            if s.parent_id is None:
                continue
            if not any(ns.id_ == s.parent_id for ns in all_spans):
                s.parent_id += "-missing"
                all_spans.append(Span(id_=s.parent_id, parent_id=None))

        # Build index once for O(n) tree building
        spans_by_parent = self._build_spans_by_parent_index(all_spans)

        parents = self._get_parents()
        span_groups = []
        for p in parents:
            this_span_group = self._build_tree_by_parent(
                parent=p, spans_by_parent=spans_by_parent
            )
            sorted_span_group = sorted(this_span_group, key=lambda x: x.start_time)
            span_groups.append(sorted_span_group)

        trees = []
        tree = Tree()
        for grp in span_groups:
            for span in grp:
                if span.parent_id is None:
                    if tree.all_nodes():
                        trees.append(tree)
                        tree = Tree()

                duration_str = f"{span.duration:.6f}s" if span.duration else ""
                tree.create_node(
                    tag=f"{span.id_} (SPAN) - {duration_str}",
                    identifier=span.id_,
                    parent=span.parent_id,
                    data=span.start_time,
                )

                # Add events that belong to this span if requested
                if include_events:
                    span_events = [e for e in self.events if e.span_id == span.id_]
                    for event in sorted(span_events, key=lambda e: e.timestamp):
                        event_id = f"event-{event.id_}"
                        tree.create_node(
                            tag=event.class_name(),
                            identifier=event_id,
                            parent=span.id_,
                            data=event.timestamp,
                        )

        trees.append(tree)
        return trees

    def _get_event_trees(self) -> list["Tree"]:
        """Generate event-centric tree structures with spans as roots and events as children."""
        try:
            from treelib.tree import Tree
        except ImportError as e:
            raise ImportError(
                "`treelib` package is missing. Please install it by using "
                "`pip install treelib`."
            )

        # Group events by span_id
        events_by_span: dict[str, list[BaseEvent]] = defaultdict(list)
        for event in self.events:
            if event.span_id:
                events_by_span[event.span_id].append(event)

        trees = []
        for span_id, span_events in events_by_span.items():
            tree = Tree()
            # Create root node for the span
            tree.create_node(
                tag=f"{span_id} (SPAN)",
                identifier=span_id,
                parent=None,
                data=min(e.timestamp for e in span_events) if span_events else None,
            )

            # Add events as children
            for event in sorted(span_events, key=lambda e: e.timestamp):
                event_id = f"event-{event.id_}"
                tree.create_node(
                    tag=f"{event.class_name()}: {event.id_}",
                    identifier=event_id,
                    parent=span_id,
                    data=event.timestamp,
                )

            trees.append(tree)

        return trees

    def print_trace_trees(self, include_events: bool = True) -> None:
        """Display formatted execution traces with chronologically sorted span hierarchies."""
        trees = self._get_trace_trees(include_events=include_events)
        for tree in trees:
            print(tree.show(stdout=False, sorting=True, key=lambda node: node.data))
            print("")

    def print_event_trees(self) -> None:
        """Display event sequences grouped by parent span for focused event analysis."""
        trees = self._get_event_trees()
        for tree in trees:
            print(tree.show(stdout=False, sorting=True, key=lambda node: node.data))
            print("")
