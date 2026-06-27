from __future__ import annotations

from typing import Any


class GroupExpr:
    """Base class for composable group-access expressions.

    Combine with &, |, ~ operators or the explicit AND / OR / NOT helpers.
    """

    def __and__(self, other: GroupExpr) -> GroupExpr:
        return _AndExpr(self, other)

    def __or__(self, other: GroupExpr) -> GroupExpr:
        return _OrExpr(self, other)

    def __invert__(self) -> GroupExpr:
        return _NotExpr(self)

    def eval(self, group_ids: frozenset[int]) -> bool:
        raise NotImplementedError


class G(GroupExpr):
    """Leaf expression: checks membership in a single group by code_name."""

    def __init__(self, code_name: str) -> None:
        self.code_name = code_name

    def eval(self, group_ids: frozenset[int]) -> bool:
        from .models import GroupProfile  # lazy — avoids circular import at module load
        group = GroupProfile.get_group_by_code_name(self.code_name)
        return bool(group and group.id in group_ids)

    def __repr__(self) -> str:
        return f"G({self.code_name!r})"


class _AndExpr(GroupExpr):
    def __init__(self, *exprs: GroupExpr) -> None:
        self.exprs = exprs

    def eval(self, group_ids: frozenset[int]) -> bool:
        return all(e.eval(group_ids) for e in self.exprs)

    def __repr__(self) -> str:
        return f"({' & '.join(repr(e) for e in self.exprs)})"


class _OrExpr(GroupExpr):
    def __init__(self, *exprs: GroupExpr) -> None:
        self.exprs = exprs

    def eval(self, group_ids: frozenset[int]) -> bool:
        return any(e.eval(group_ids) for e in self.exprs)

    def __repr__(self) -> str:
        return f"({' | '.join(repr(e) for e in self.exprs)})"


class _NotExpr(GroupExpr):
    def __init__(self, expr: GroupExpr) -> None:
        self.expr = expr

    def eval(self, group_ids: frozenset[int]) -> bool:
        return not self.expr.eval(group_ids)

    def __repr__(self) -> str:
        return f"(~{self.expr!r})"


class _ConstExpr(GroupExpr):
    def __init__(self, value: bool) -> None:
        self.value = value

    def eval(self, group_ids: frozenset[int]) -> bool:
        return self.value


# ---------------------------------------------------------------------------
# Explicit constructors — alternative to operator syntax
# ---------------------------------------------------------------------------

def AND(*exprs: GroupExpr) -> GroupExpr:
    """AND(G('a'), G('b')) — all must be True."""
    if not exprs:
        return _ConstExpr(True)
    result = exprs[0]
    for e in exprs[1:]:
        result = result & e
    return result


def OR(*exprs: GroupExpr) -> GroupExpr:
    """OR(G('a'), G('b')) — any must be True."""
    if not exprs:
        return _ConstExpr(False)
    result = exprs[0]
    for e in exprs[1:]:
        result = result | e
    return result


def NOT(expr: GroupExpr) -> GroupExpr:
    """NOT(G('a')) — negates the expression."""
    return ~expr


# ---------------------------------------------------------------------------
# Dict-tree evaluator (querybuilder-compatible format)
# ---------------------------------------------------------------------------

def eval_group_tree(tree: dict[str, Any], group_ids: frozenset[int]) -> bool:
    """Evaluate a querybuilder-compatible access tree against a set of group IDs.

    Tree format (mirrors querybuilder/utils.py rules_to_q structure):

        {
          "type": "group",
          "combinator": "AND" | "OR" | "NOT",
          "rules": [
            {"type": "rule", "group": "code_name"},
            {"type": "rule", "group": "code_name", "not": true},
            {"type": "group", "combinator": "OR", "rules": [...]}
          ]
        }

    Combinator notes:
      - "AND": all child rules must pass
      - "OR":  any child rule must pass
      - "NOT": negates the AND of all children (i.e. NAND)

    A rule with "not": true negates just that leaf check.
    Empty "rules" lists evaluate to True (no restriction imposed).
    A root node without type="group" is auto-wrapped (same behaviour as rules_to_q).
    """
    def _build(node: dict) -> GroupExpr:
        if not node:
            return _ConstExpr(True)

        node_type = node.get("type", "group")

        if node_type == "rule":
            code_name = node.get("group", "")
            expr: GroupExpr = G(code_name)
            if node.get("not"):
                expr = ~expr
            return expr

        # group node
        combinator = (node.get("combinator") or "AND").upper()
        rules = node.get("rules") or []

        if not rules:
            return _ConstExpr(True)

        child_exprs = [_build(r) for r in rules]

        if combinator == "NOT":
            return ~AND(*child_exprs)
        if combinator == "OR":
            return OR(*child_exprs)
        return AND(*child_exprs)  # "AND" or any unknown value

    if not tree:
        return True
    if tree.get("type") != "group":
        tree = {"type": "group", "combinator": "AND", "rules": [tree]}

    return _build(tree).eval(group_ids)
