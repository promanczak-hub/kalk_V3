"""Generate markdown field-by-field instructions from a Pydantic schema.

Single source of truth = `Field(description=...)`. Edit a description in
`extractor_models.py` → prompt auto-updates on next call. No second copy
to drift out of sync.

Output format (per field):

  - **name** (string, required) — The name of the thing.
  - **price** (float, optional, default=None) — Price in PLN, null if unknown.
"""

from __future__ import annotations

import inspect
from typing import Any, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo


def _format_type(annotation: Any) -> str:
    """Render a Python type annotation as a short human-readable string."""
    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is None:
        # Direct type
        if annotation is type(None):
            return "null"
        name = getattr(annotation, "__name__", None)
        if name:
            return name
        return str(annotation)

    # Unions (Optional[X] is Union[X, None])
    if hasattr(annotation, "__class__") and origin.__name__ == "UnionType":
        return " | ".join(_format_type(a) for a in args)
    if str(origin).endswith("Union"):
        return " | ".join(_format_type(a) for a in args)

    # Containers
    if origin in (list, tuple, set, frozenset):
        inner = ", ".join(_format_type(a) for a in args)
        return f"{origin.__name__}[{inner}]"
    if origin is dict:
        return "dict"

    # Generic alias
    name = getattr(origin, "__name__", str(origin))
    if args:
        inner = ", ".join(_format_type(a) for a in args)
        return f"{name}[{inner}]"
    return name


def _required_marker(field: FieldInfo) -> str:
    """Render '(required)' or '(optional, default=…)'."""
    if field.is_required():
        return "required"
    default = field.default
    if default is None:
        return "optional, default=null"
    try:
        repr_default = repr(default)
        # Truncate ugly default_factory output
        if len(repr_default) > 40:
            repr_default = repr_default[:37] + "..."
    except Exception:
        repr_default = "..."
    return f"optional, default={repr_default}"


def _build_one_field_line(name: str, field: FieldInfo) -> str:
    type_str = _format_type(field.annotation)
    marker = _required_marker(field)
    desc = (field.description or "").strip()
    return f"- **{name}** ({type_str}, {marker}) — {desc}"


def build_field_instructions(
    schema: type[BaseModel],
    *,
    recurse_depth: int = 1,
    _visited: set[type] | None = None,
) -> str:
    """Render a Pydantic schema as markdown bullet list of fields.

    Args:
        schema: Pydantic BaseModel subclass.
        recurse_depth: How many levels of nested BaseModel to expand inline.
            0 = top-level only (nested models shown as their class name).
            1 = one level deep (default).
            2+ = deeper.

    Returns:
        Markdown string starting with '## Pola wyciągane (schema={Name})'.
    """
    if _visited is None:
        _visited = set()
    if schema in _visited:
        return f"## (cyklicznie zagnieżdżone — patrz powyżej: {schema.__name__})\n"
    _visited = _visited | {schema}

    lines: list[str] = [f"## Pola wyciągane (schema={schema.__name__})", ""]

    for name, field in schema.model_fields.items():
        lines.append(_build_one_field_line(name, field))
        # Recurse into nested BaseModel
        if recurse_depth > 0:
            nested = _nested_model(field.annotation)
            if nested is not None and nested not in _visited:
                inner = build_field_instructions(
                    nested,
                    recurse_depth=recurse_depth - 1,
                    _visited=_visited,
                )
                # Indent the nested block under the parent bullet
                indented = "\n".join(f"  {ln}" for ln in inner.splitlines())
                lines.append(indented)

    lines.append("")
    return "\n".join(lines)


def _nested_model(annotation: Any) -> type[BaseModel] | None:
    """If the annotation is (or contains) a Pydantic BaseModel, return it.

    Handles Optional[Model], list[Model], Model.
    """
    candidates = [annotation, *get_args(annotation)]
    for c in candidates:
        if inspect.isclass(c) and issubclass(c, BaseModel):
            return c
        # Recurse one level for list[Optional[Model]] etc.
        nested_args = get_args(c)
        for n in nested_args:
            if inspect.isclass(n) and issubclass(n, BaseModel):
                return n
    return None
