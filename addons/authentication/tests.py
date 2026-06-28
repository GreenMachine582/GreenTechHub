from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from .access import (
    G, AND, OR, NOT, GroupExpr, _ConstExpr,
    eval_group_tree,
)
from .models import GroupProfile, Role

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _Leaf(GroupExpr):
    """Test double: a GroupExpr leaf that returns a fixed value without any DB access."""
    def __init__(self, value: bool) -> None:
        self.value = value

    def eval(self, group_ids):
        return self.value


def _T():
    return _Leaf(True)


def _F():
    return _Leaf(False)


def _make_group(name: str) -> Group:
    profile = GroupProfile.createGroupAndProfile(name, "")
    return profile.group


def _make_user(username: str, *groups: Group) -> User:
    user = User.objects.create_user(username=username, password="x")
    for g in groups:
        user.groups.add(g)
    return user


# ---------------------------------------------------------------------------
# 1. Pure expression logic — no database required
# ---------------------------------------------------------------------------

class GroupExprOperatorsTest(TestCase):
    """Operator overloading and combinator logic using in-memory test leaves."""

    # --- AND ---
    def test_and_both_true(self):
        self.assertTrue((_T() & _T()).eval(frozenset()))

    def test_and_one_false(self):
        self.assertFalse((_T() & _F()).eval(frozenset()))

    def test_and_both_false(self):
        self.assertFalse((_F() & _F()).eval(frozenset()))

    # --- OR ---
    def test_or_both_true(self):
        self.assertTrue((_T() | _T()).eval(frozenset()))

    def test_or_one_true(self):
        self.assertTrue((_F() | _T()).eval(frozenset()))

    def test_or_both_false(self):
        self.assertFalse((_F() | _F()).eval(frozenset()))

    # --- NOT ---
    def test_not_true(self):
        self.assertFalse((~_T()).eval(frozenset()))

    def test_not_false(self):
        self.assertTrue((~_F()).eval(frozenset()))

    # --- Nesting ---
    def test_and_or_nested(self):
        # T & (F | T) → True
        self.assertTrue((_T() & (_F() | _T())).eval(frozenset()))

    def test_and_or_nested_false(self):
        # T & (F | F) → False
        self.assertFalse((_T() & (_F() | _F())).eval(frozenset()))

    def test_not_and(self):
        # ~(T & F) → True
        self.assertTrue((~(_T() & _F())).eval(frozenset()))

    def test_triple_and(self):
        self.assertFalse((_T() & _T() & _F()).eval(frozenset()))

    def test_double_not(self):
        self.assertTrue((~~_T()).eval(frozenset()))


class ExplicitConstructorsTest(TestCase):
    """AND() / OR() / NOT() helper functions."""

    def test_AND_all_true(self):
        self.assertTrue(AND(_T(), _T(), _T()).eval(frozenset()))

    def test_AND_with_false(self):
        self.assertFalse(AND(_T(), _F()).eval(frozenset()))

    def test_AND_single_arg(self):
        expr = AND(_T())
        self.assertTrue(expr.eval(frozenset()))

    def test_AND_no_args_returns_true(self):
        self.assertIsInstance(AND(), _ConstExpr)
        self.assertTrue(AND().eval(frozenset()))

    def test_OR_any_true(self):
        self.assertTrue(OR(_F(), _T(), _F()).eval(frozenset()))

    def test_OR_all_false(self):
        self.assertFalse(OR(_F(), _F()).eval(frozenset()))

    def test_OR_single_arg(self):
        self.assertFalse(OR(_F()).eval(frozenset()))

    def test_OR_no_args_returns_false(self):
        self.assertIsInstance(OR(), _ConstExpr)
        self.assertFalse(OR().eval(frozenset()))

    def test_NOT(self):
        self.assertTrue(NOT(_F()).eval(frozenset()))
        self.assertFalse(NOT(_T()).eval(frozenset()))

    def test_combined(self):
        # AND(T, NOT(F)) → True
        self.assertTrue(AND(_T(), NOT(_F())).eval(frozenset()))


# ---------------------------------------------------------------------------
# 2. G leaf — requires DB (GroupProfile lookup)
# ---------------------------------------------------------------------------

class GLeafTest(TestCase):

    def setUp(self):
        self.group_a = _make_group("Alpha")
        self.group_b = _make_group("Beta")
        self.ids_with_a = frozenset([self.group_a.id])
        self.ids_with_both = frozenset([self.group_a.id, self.group_b.id])
        self.empty_ids = frozenset()

    def test_member(self):
        self.assertTrue(G("alpha").eval(self.ids_with_a))

    def test_non_member(self):
        self.assertFalse(G("beta").eval(self.ids_with_a))

    def test_unknown_code_name(self):
        self.assertFalse(G("does_not_exist").eval(self.ids_with_a))

    def test_both_present(self):
        self.assertTrue(G("alpha").eval(self.ids_with_both))
        self.assertTrue(G("beta").eval(self.ids_with_both))

    def test_repr(self):
        self.assertEqual(repr(G("admin")), "G('admin')")

    def test_and_with_G(self):
        expr = G("alpha") & G("beta")
        self.assertFalse(expr.eval(self.ids_with_a))
        self.assertTrue(expr.eval(self.ids_with_both))

    def test_or_with_G(self):
        expr = G("alpha") | G("beta")
        self.assertTrue(expr.eval(self.ids_with_a))
        self.assertFalse(expr.eval(self.empty_ids))

    def test_not_with_G(self):
        self.assertFalse((~G("alpha")).eval(self.ids_with_a))
        self.assertTrue((~G("alpha")).eval(self.empty_ids))


# ---------------------------------------------------------------------------
# 3. eval_group_tree — dict tree evaluator
# ---------------------------------------------------------------------------

class EvalGroupTreeTest(TestCase):

    def setUp(self):
        self.group_a = _make_group("Alpha")
        self.group_b = _make_group("Beta")
        self.group_c = _make_group("Gamma")
        self.ids_a = frozenset([self.group_a.id])
        self.ids_ab = frozenset([self.group_a.id, self.group_b.id])
        self.ids_abc = frozenset([self.group_a.id, self.group_b.id, self.group_c.id])
        self.empty = frozenset()

    # --- edge cases ---

    def test_none_tree_returns_true(self):
        self.assertTrue(eval_group_tree(None, self.empty))

    def test_empty_dict_returns_true(self):
        self.assertTrue(eval_group_tree({}, self.empty))

    def test_empty_rules_returns_true(self):
        tree = {"type": "group", "combinator": "AND", "rules": []}
        self.assertTrue(eval_group_tree(tree, self.empty))

    def test_bare_rule_auto_wrapped(self):
        # A root node without type="group" should be auto-wrapped
        tree = {"type": "rule", "group": "alpha"}
        self.assertTrue(eval_group_tree(tree, self.ids_a))
        self.assertFalse(eval_group_tree(tree, self.empty))

    # --- simple rules ---

    def test_single_rule_member(self):
        tree = {"type": "group", "combinator": "AND", "rules": [
            {"type": "rule", "group": "alpha"},
        ]}
        self.assertTrue(eval_group_tree(tree, self.ids_a))

    def test_single_rule_non_member(self):
        tree = {"type": "group", "combinator": "AND", "rules": [
            {"type": "rule", "group": "beta"},
        ]}
        self.assertFalse(eval_group_tree(tree, self.ids_a))

    def test_rule_with_not_true(self):
        tree = {"type": "group", "combinator": "AND", "rules": [
            {"type": "rule", "group": "alpha", "not": True},
        ]}
        self.assertFalse(eval_group_tree(tree, self.ids_a))
        self.assertTrue(eval_group_tree(tree, self.empty))

    def test_rule_unknown_group(self):
        tree = {"type": "group", "combinator": "AND", "rules": [
            {"type": "rule", "group": "no_such_group"},
        ]}
        self.assertFalse(eval_group_tree(tree, self.ids_abc))

    # --- AND combinator ---

    def test_and_all_match(self):
        tree = {"type": "group", "combinator": "AND", "rules": [
            {"type": "rule", "group": "alpha"},
            {"type": "rule", "group": "beta"},
        ]}
        self.assertTrue(eval_group_tree(tree, self.ids_ab))

    def test_and_partial_match(self):
        tree = {"type": "group", "combinator": "AND", "rules": [
            {"type": "rule", "group": "alpha"},
            {"type": "rule", "group": "beta"},
        ]}
        self.assertFalse(eval_group_tree(tree, self.ids_a))

    # --- OR combinator ---

    def test_or_any_match(self):
        tree = {"type": "group", "combinator": "OR", "rules": [
            {"type": "rule", "group": "alpha"},
            {"type": "rule", "group": "beta"},
        ]}
        self.assertTrue(eval_group_tree(tree, self.ids_a))

    def test_or_none_match(self):
        tree = {"type": "group", "combinator": "OR", "rules": [
            {"type": "rule", "group": "alpha"},
            {"type": "rule", "group": "beta"},
        ]}
        self.assertFalse(eval_group_tree(tree, frozenset([self.group_c.id])))

    # --- NOT combinator ---

    def test_not_combinator_negates_all(self):
        # NOT(alpha AND beta) → True when user only has alpha
        tree = {"type": "group", "combinator": "NOT", "rules": [
            {"type": "rule", "group": "alpha"},
            {"type": "rule", "group": "beta"},
        ]}
        self.assertTrue(eval_group_tree(tree, self.ids_a))   # a only → AND fails → NOT True
        self.assertFalse(eval_group_tree(tree, self.ids_ab)) # both → AND passes → NOT False

    # --- Nested groups ---

    def test_and_with_nested_or(self):
        # alpha AND (beta OR gamma)
        tree = {
            "type": "group", "combinator": "AND",
            "rules": [
                {"type": "rule", "group": "alpha"},
                {"type": "group", "combinator": "OR", "rules": [
                    {"type": "rule", "group": "beta"},
                    {"type": "rule", "group": "gamma"},
                ]},
            ],
        }
        self.assertFalse(eval_group_tree(tree, self.ids_a))          # only alpha
        self.assertTrue(eval_group_tree(tree, self.ids_ab))          # alpha + beta
        self.assertTrue(eval_group_tree(tree, frozenset([           # alpha + gamma
            self.group_a.id, self.group_c.id
        ])))

    def test_or_with_nested_and(self):
        # (alpha AND beta) OR gamma
        tree = {
            "type": "group", "combinator": "OR",
            "rules": [
                {"type": "group", "combinator": "AND", "rules": [
                    {"type": "rule", "group": "alpha"},
                    {"type": "rule", "group": "beta"},
                ]},
                {"type": "rule", "group": "gamma"},
            ],
        }
        self.assertFalse(eval_group_tree(tree, self.ids_a))    # alpha only — neither branch
        self.assertTrue(eval_group_tree(tree, self.ids_ab))    # alpha+beta — AND branch
        self.assertTrue(eval_group_tree(tree, frozenset([self.group_c.id])))  # gamma — OR branch

    def test_and_with_not_leaf(self):
        # alpha AND NOT beta
        tree = {"type": "group", "combinator": "AND", "rules": [
            {"type": "rule", "group": "alpha"},
            {"type": "rule", "group": "beta", "not": True},
        ]}
        self.assertTrue(eval_group_tree(tree, self.ids_a))     # has alpha, no beta
        self.assertFalse(eval_group_tree(tree, self.ids_ab))   # has both → NOT beta fails


# ---------------------------------------------------------------------------
# 4. User.hasGroups() — dispatch and group resolution
# ---------------------------------------------------------------------------

class HasGroupsDispatchTest(TestCase):
    """Tests for string, GroupExpr, and dict dispatch paths."""

    def setUp(self):
        self.group_a = _make_group("Alpha")
        self.group_b = _make_group("Beta")
        self.user = _make_user("testuser", self.group_a)

    # --- string path (backward compat) ---

    def test_string_single_member(self):
        self.assertTrue(self.user.hasGroups("alpha"))

    def test_string_single_non_member(self):
        self.assertFalse(self.user.hasGroups("beta"))

    def test_string_or_first_matches(self):
        self.assertTrue(self.user.hasGroups("alpha", "beta"))

    def test_string_or_second_matches(self):
        self.user.groups.add(self.group_b)
        self.user.groups.remove(self.group_a)
        self.assertTrue(self.user.hasGroups("alpha", "beta"))

    def test_string_or_none_match(self):
        self.assertFalse(self.user.hasGroups("beta"))

    def test_string_no_args(self):
        self.assertFalse(self.user.hasGroups())

    def test_string_unknown_code_name(self):
        self.assertFalse(self.user.hasGroups("no_such_group"))

    # --- GroupExpr dispatch ---

    def test_expr_G_member(self):
        self.assertTrue(self.user.hasGroups(G("alpha")))

    def test_expr_G_non_member(self):
        self.assertFalse(self.user.hasGroups(G("beta")))

    def test_expr_and(self):
        self.assertFalse(self.user.hasGroups(G("alpha") & G("beta")))
        self.user.groups.add(self.group_b)
        self.assertTrue(self.user.hasGroups(G("alpha") & G("beta")))

    def test_expr_or(self):
        self.assertTrue(self.user.hasGroups(G("alpha") | G("beta")))

    def test_expr_not(self):
        self.assertFalse(self.user.hasGroups(~G("alpha")))
        self.assertTrue(self.user.hasGroups(~G("beta")))

    def test_expr_and_not(self):
        # has alpha AND NOT beta
        self.assertTrue(self.user.hasGroups(G("alpha") & ~G("beta")))
        self.user.groups.add(self.group_b)
        self.assertFalse(self.user.hasGroups(G("alpha") & ~G("beta")))

    def test_expr_nested(self):
        # alpha AND (beta OR NOT beta) → always True when user has alpha
        self.assertTrue(self.user.hasGroups(G("alpha") & (G("beta") | ~G("beta"))))

    # --- dict tree dispatch ---

    def test_dict_and_match(self):
        self.user.groups.add(self.group_b)
        tree = {"type": "group", "combinator": "AND", "rules": [
            {"type": "rule", "group": "alpha"},
            {"type": "rule", "group": "beta"},
        ]}
        self.assertTrue(self.user.hasGroups(tree))

    def test_dict_and_no_match(self):
        tree = {"type": "group", "combinator": "AND", "rules": [
            {"type": "rule", "group": "alpha"},
            {"type": "rule", "group": "beta"},
        ]}
        self.assertFalse(self.user.hasGroups(tree))

    def test_dict_empty_returns_true(self):
        self.assertTrue(self.user.hasGroups({}))


class HasGroupsRoleInheritanceTest(TestCase):
    """Groups inherited via User.role are included in all hasGroups paths."""

    def setUp(self):
        self.group_a = _make_group("Alpha")    # directly assigned
        self.group_b = _make_group("Beta")     # inherited via role
        self.group_c = _make_group("Gamma")    # neither

        self.role = Role.objects.create(name="TestRole")
        self.role.groups.add(self.group_b)

        self.user = _make_user("roleuser", self.group_a)
        self.user.role = self.role
        self.user.save()

    def test_string_direct_group(self):
        self.assertTrue(self.user.hasGroups("alpha"))

    def test_string_role_inherited_group(self):
        self.assertTrue(self.user.hasGroups("beta"))

    def test_string_not_in_either(self):
        self.assertFalse(self.user.hasGroups("gamma"))

    def test_expr_role_inherited(self):
        self.assertTrue(self.user.hasGroups(G("beta")))

    def test_expr_direct_and_inherited(self):
        self.assertTrue(self.user.hasGroups(G("alpha") & G("beta")))

    def test_expr_direct_and_missing(self):
        self.assertFalse(self.user.hasGroups(G("alpha") & G("gamma")))

    def test_dict_tree_role_inherited(self):
        tree = {"type": "group", "combinator": "AND", "rules": [
            {"type": "rule", "group": "alpha"},
            {"type": "rule", "group": "beta"},
        ]}
        self.assertTrue(self.user.hasGroups(tree))

    def test_no_role_does_not_error(self):
        user_no_role = _make_user("norole", self.group_a)
        self.assertTrue(user_no_role.hasGroups("alpha"))
        self.assertFalse(user_no_role.hasGroups("beta"))

    def test_group_ids_includes_role_groups(self):
        ids = self.user._group_ids()
        self.assertIn(self.group_a.id, ids)
        self.assertIn(self.group_b.id, ids)
        self.assertNotIn(self.group_c.id, ids)


# ---------------------------------------------------------------------------
# 5. access_check API view
# ---------------------------------------------------------------------------

class AccessCheckViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.group_a = _make_group("Alpha")
        self.group_b = _make_group("Beta")

        self.role = Role.objects.create(name="ViewerRole")
        self.role.groups.add(self.group_b)

        # user_direct: has alpha directly
        self.user_direct = _make_user("direct", self.group_a)

        # user_role: has beta via role only
        self.user_role = _make_user("roleuser")
        self.user_role.role = self.role
        self.user_role.save()

    def _post(self, user, payload):
        self.client.force_authenticate(user=user)
        return self.client.post("/api/access-check/", payload, format="json")

    # --- unauthenticated ---

    def test_unauthenticated_returns_401(self):
        resp = self.client.post("/api/access-check/", {"group": "alpha"}, format="json")
        self.assertEqual(resp.status_code, 401)

    # --- simple group format ---

    def test_simple_group_member(self):
        resp = self._post(self.user_direct, {"group": "alpha"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["allowed"])

    def test_simple_group_non_member(self):
        resp = self._post(self.user_direct, {"group": "beta"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["allowed"])

    def test_simple_groups_or_first(self):
        resp = self._post(self.user_direct, {"groups": "alpha,beta"})
        self.assertTrue(resp.data["allowed"])

    def test_simple_groups_or_none(self):
        resp = self._post(self.user_direct, {"groups": "beta"})
        self.assertFalse(resp.data["allowed"])

    def test_empty_body_returns_false(self):
        resp = self._post(self.user_direct, {})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["allowed"])

    # --- role-inherited group (bug fix) ---

    def test_role_inherited_group_is_allowed(self):
        resp = self._post(self.user_role, {"group": "beta"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["allowed"])

    def test_role_inherited_group_not_in_direct_groups(self):
        # Confirm the fix: user_role has no direct group membership for beta
        self.assertFalse(self.user_role.groups.filter(id=self.group_b.id).exists())
        # But the API must still return allowed=True
        resp = self._post(self.user_role, {"group": "beta"})
        self.assertTrue(resp.data["allowed"])

    # --- tree format ---

    def test_tree_and_both_match(self):
        self.user_direct.groups.add(self.group_b)
        tree = {"type": "group", "combinator": "AND", "rules": [
            {"type": "rule", "group": "alpha"},
            {"type": "rule", "group": "beta"},
        ]}
        resp = self._post(self.user_direct, {"tree": tree})
        self.assertTrue(resp.data["allowed"])

    def test_tree_and_partial_match(self):
        tree = {"type": "group", "combinator": "AND", "rules": [
            {"type": "rule", "group": "alpha"},
            {"type": "rule", "group": "beta"},
        ]}
        resp = self._post(self.user_direct, {"tree": tree})
        self.assertFalse(resp.data["allowed"])

    def test_tree_or_match(self):
        tree = {"type": "group", "combinator": "OR", "rules": [
            {"type": "rule", "group": "alpha"},
            {"type": "rule", "group": "beta"},
        ]}
        resp = self._post(self.user_direct, {"tree": tree})
        self.assertTrue(resp.data["allowed"])

    def test_tree_not_leaf(self):
        # alpha AND NOT beta → True for user_direct (has alpha, no beta)
        tree = {"type": "group", "combinator": "AND", "rules": [
            {"type": "rule", "group": "alpha"},
            {"type": "rule", "group": "beta", "not": True},
        ]}
        resp = self._post(self.user_direct, {"tree": tree})
        self.assertTrue(resp.data["allowed"])

    def test_tree_role_inherited_group(self):
        # user_role has beta via role — tree must resolve it
        tree = {"type": "group", "combinator": "AND", "rules": [
            {"type": "rule", "group": "beta"},
        ]}
        resp = self._post(self.user_role, {"tree": tree})
        self.assertTrue(resp.data["allowed"])

    def test_tree_nested(self):
        # alpha AND (beta OR gamma) — user_direct only has alpha → False
        _make_group("Gamma")
        tree = {
            "type": "group", "combinator": "AND",
            "rules": [
                {"type": "rule", "group": "alpha"},
                {"type": "group", "combinator": "OR", "rules": [
                    {"type": "rule", "group": "beta"},
                    {"type": "rule", "group": "gamma"},
                ]},
            ],
        }
        resp = self._post(self.user_direct, {"tree": tree})
        self.assertFalse(resp.data["allowed"])

    def test_tree_empty_returns_true(self):
        resp = self._post(self.user_direct, {"tree": {}})
        self.assertTrue(resp.data["allowed"])
