import datetime
from typing import Any, Dict
from django.db.models import Q

# Expected rules tree shape:
# {
#   "type": "group",
#   "combinator": "AND" | "OR",
#   "rules": [
#       {"type": "rule", "field": "title", "op": "contains", "value": "foo"},
#       {"type": "group", "combinator": "OR", "rules": [ ... ]}
#   ]
# }
#
# field_map: name -> {"lookup": "title", "type": "string"} (lookup can be dotted related lookup)

def _coerce_value(v, field_type):
    if v is None:
        return None
    if field_type == "number":
        if isinstance(v, list):
            return [float(x) for x in v]
        try:
            return float(v)
        except (ValueError, TypeError):
            return None
    if field_type == "boolean":
        if isinstance(v, bool): return v
        if isinstance(v, str): return v.lower() == "true"
        return bool(v)
    if field_type == "date":
        def parse_date(s):
            if not s: return None
            try:
                return datetime.date.fromisoformat(s)
            except Exception:
                return None
        if isinstance(v, list):
            return [parse_date(x) for x in v]
        return parse_date(v)
    # strings & arrays pass-through
    return v

def _op_to_lookup(lookup_base: str, op: str, field_type: str, value):
    # Return (Q, used) where used indicates if value was used
    if op == "eq":
        return Q(**{lookup_base: value}), True
    if op == "neq":
        return ~Q(**{lookup_base: value}), True
    if op == "contains":
        return Q(**{f"{lookup_base}__icontains": value}), True
    if op == "startswith":
        return Q(**{f"{lookup_base}__istartswith": value}), True
    if op == "endswith":
        return Q(**{f"{lookup_base}__iendswith": value}), True
    if op == "lt":
        return Q(**{f"{lookup_base}__lt": value}), True
    if op == "lte":
        return Q(**{f"{lookup_base}__lte": value}), True
    if op == "gt":
        return Q(**{f"{lookup_base}__gt": value}), True
    if op == "gte":
        return Q(**{f"{lookup_base}__gte": value}), True
    if op == "in":
        arr = value if isinstance(value, list) else [value]
        return Q(**{f"{lookup_base}__in": arr}), True
    if op == "isnull":
        return Q(**{f"{lookup_base}__isnull": True}), False
    if op == "notnull":
        return Q(**{f"{lookup_base}__isnull": False}), False
    if op == "istrue":
        return Q(**{lookup_base: True}), False
    if op == "isfalse":
        return Q(**{lookup_base: False}), False
    if op == "between" and field_type == "date":
        a, b = (value or [None, None])[:2]
        q = Q()
        if a: q &= Q(**{f"{lookup_base}__gte": a})
        if b: q &= Q(**{f"{lookup_base}__lte": b})
        return q, True
    # Fallback (no-op)
    return Q(), False

def rules_to_q(tree: Dict[str, Any], field_map: Dict[str, Dict[str, Any]]) -> Q:
    """
    Convert rules tree to a Django Q object using field_map.

    field_map example:
        {
          "title": {"lookup": "title", "type": "string"},
          "author": {"lookup": "author__name", "type": "string"},
          "price": {"lookup": "price", "type": "number"},
          "published": {"lookup": "published", "type": "date"},
          "in_print": {"lookup": "in_print", "type": "boolean"}
        }
    """
    def build(node):
        if not node:
            return Q()
        if node.get("type") == "rule":
            name = node.get("field")
            op = node.get("op")
            conf = field_map.get(name, {"lookup": name, "type": "string"})
            lookup = conf.get("lookup", name)
            ftype = conf.get("type", "string")
            value = _coerce_value(node.get("value"), ftype)
            q, _ = _op_to_lookup(lookup, op, ftype, value)
            return q
        # group
        combinator = (node.get("combinator") or "AND").upper()
        sub = node.get("rules") or []
        if not sub:
            return Q()
        partials = [build(r) for r in sub]
        if combinator == "OR":
            q = Q()
            for p in partials: q |= p
            return q
        else:
            q = Q()
            for p in partials: q &= p
            return q

    if not tree:
        return Q()
    if tree.get("type") != "group":
        tree = {"type": "group", "combinator": "AND", "rules": [tree]}
    return build(tree)
