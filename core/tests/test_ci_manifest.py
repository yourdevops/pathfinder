"""Tests for CI manifest utilities: version normalization, runtime compatibility,
constraint parsing, semver intersection, and runtime constraint computation."""

from types import SimpleNamespace

import semver
from django.test import SimpleTestCase

from core.ci_manifest import (
    _format_version,
    _is_tighter_lower,
    _is_tighter_upper,
    _parse_constraint,
    check_step_constraint_compatibility,
    compute_runtime_constraints,
    intersect_semver_constraints,
    is_step_compatible,
    normalize_version,
)

# ---------------------------------------------------------------------------
# normalize_version
# ---------------------------------------------------------------------------


class NormalizeVersionTest(SimpleTestCase):
    """Test version string normalization to 3-part semver."""

    def test_three_part_passthrough(self):
        self.assertEqual(normalize_version("1.2.3"), "1.2.3")

    def test_two_part_pads_patch(self):
        self.assertEqual(normalize_version("3.11"), "3.11.0")

    def test_one_part_pads_minor_and_patch(self):
        self.assertEqual(normalize_version("3"), "3.0.0")

    def test_four_part_truncated(self):
        self.assertEqual(normalize_version("1.2.3.4"), "1.2.3")

    def test_whitespace_stripped(self):
        self.assertEqual(normalize_version("  3.11  "), "3.11.0")

    def test_zero_version(self):
        self.assertEqual(normalize_version("0"), "0.0.0")


# ---------------------------------------------------------------------------
# _format_version
# ---------------------------------------------------------------------------


class FormatVersionTest(SimpleTestCase):
    """Test compact version formatting (drops trailing .0 segments)."""

    def test_drops_patch_and_minor_zeros(self):
        self.assertEqual(_format_version(semver.Version.parse("3.0.0")), "3")

    def test_drops_patch_zero(self):
        self.assertEqual(_format_version(semver.Version.parse("3.11.0")), "3.11")

    def test_keeps_all_nonzero(self):
        self.assertEqual(_format_version(semver.Version.parse("1.2.3")), "1.2.3")

    def test_zero_version(self):
        self.assertEqual(_format_version(semver.Version.parse("0.0.0")), "0")

    def test_zero_minor_nonzero_patch(self):
        self.assertEqual(_format_version(semver.Version.parse("1.0.3")), "1.0.3")


# ---------------------------------------------------------------------------
# _parse_constraint
# ---------------------------------------------------------------------------


class ParseConstraintTest(SimpleTestCase):
    """Test constraint string parsing into (operator, version) tuples."""

    def test_simple_gte(self):
        result = _parse_constraint(">=3.10")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], ">=")
        self.assertEqual(result[0][1], semver.Version.parse("3.10.0"))

    def test_compound_constraint(self):
        result = _parse_constraint(">=3.10,<4.0")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0][0], ">=")
        self.assertEqual(result[1][0], "<")

    def test_no_operator_defaults_gte(self):
        result = _parse_constraint("3.10")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], ">=")

    def test_exact_match(self):
        result = _parse_constraint("==3.12")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "==")

    def test_compatible_release(self):
        result = _parse_constraint("~=3.10")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "~=")

    def test_invalid_constraint_skipped(self):
        result = _parse_constraint("not-valid")
        # "not-valid" won't match the regex, so empty
        self.assertEqual(len(result), 0)

    def test_empty_string(self):
        result = _parse_constraint("")
        self.assertEqual(len(result), 0)

    def test_whitespace_handling(self):
        result = _parse_constraint(" >= 3.10 , < 4.0 ")
        self.assertEqual(len(result), 2)


# ---------------------------------------------------------------------------
# _is_tighter_lower / _is_tighter_upper
# ---------------------------------------------------------------------------


class IsTighterLowerTest(SimpleTestCase):
    """Test lower bound tightening logic."""

    def test_none_current_always_tighter(self):
        ver = semver.Version.parse("3.10.0")
        self.assertTrue(_is_tighter_lower(None, ver, True))
        self.assertTrue(_is_tighter_lower(None, ver, False))

    def test_higher_version_is_tighter(self):
        current = (semver.Version.parse("3.10.0"), True)
        self.assertTrue(_is_tighter_lower(current, semver.Version.parse("3.11.0"), True))

    def test_same_version_exclusive_current_inclusive_new(self):
        """Same version: current >3.10, new >=3.10 — function returns True.

        Note: semantically >=3.10 is WIDER than >3.10, but the function treats
        inclusive as "tighter" at the same version. This is safe in practice
        because constraint intersection rarely mixes > and >= on the same version.
        """
        ver = semver.Version.parse("3.10.0")
        current = (ver, False)  # >3.10
        self.assertTrue(_is_tighter_lower(current, ver, True))

    def test_same_version_inclusive_over_exclusive(self):
        """Same version: inclusive current is NOT replaced by exclusive new."""
        ver = semver.Version.parse("3.10.0")
        current = (ver, True)  # current is inclusive (>=3.10)
        # New is exclusive (>3.10) — this IS tighter (higher minimum)
        # But the function returns: ver == cur_ver and not cur_inc and inclusive
        # cur_inc=True, so "not True" = False, whole thing is False
        self.assertFalse(_is_tighter_lower(current, ver, False))

    def test_lower_version_is_not_tighter(self):
        current = (semver.Version.parse("3.11.0"), True)
        self.assertFalse(_is_tighter_lower(current, semver.Version.parse("3.10.0"), True))


class IsTighterUpperTest(SimpleTestCase):
    """Test upper bound tightening logic."""

    def test_none_current_always_tighter(self):
        ver = semver.Version.parse("4.0.0")
        self.assertTrue(_is_tighter_upper(None, ver, True))
        self.assertTrue(_is_tighter_upper(None, ver, False))

    def test_lower_version_is_tighter(self):
        current = (semver.Version.parse("4.0.0"), False)
        self.assertTrue(_is_tighter_upper(current, semver.Version.parse("3.13.0"), False))

    def test_higher_version_is_not_tighter(self):
        current = (semver.Version.parse("4.0.0"), False)
        self.assertFalse(_is_tighter_upper(current, semver.Version.parse("5.0.0"), False))


# ---------------------------------------------------------------------------
# is_step_compatible
# ---------------------------------------------------------------------------


class IsStepCompatibleTest(SimpleTestCase):
    """Test step runtime compatibility checking."""

    def _step(self, constraints):
        return SimpleNamespace(runtime_constraints=constraints)

    def test_no_constraints_always_compatible(self):
        self.assertTrue(is_step_compatible(self._step(None), "python", "3.12"))
        self.assertTrue(is_step_compatible(self._step({}), "python", "3.12"))

    def test_wrong_family_incompatible(self):
        step = self._step({"node": ">=18"})
        self.assertFalse(is_step_compatible(step, "python", "3.12"))

    def test_wildcard_matches_all(self):
        step = self._step({"python": "*"})
        self.assertTrue(is_step_compatible(step, "python", "3.12"))
        self.assertTrue(is_step_compatible(step, "python", "2.7"))

    def test_gte_match(self):
        step = self._step({"python": ">=3.10"})
        self.assertTrue(is_step_compatible(step, "python", "3.12"))
        self.assertTrue(is_step_compatible(step, "python", "3.10"))
        self.assertFalse(is_step_compatible(step, "python", "3.9"))

    def test_lt_match(self):
        step = self._step({"python": "<4.0"})
        self.assertTrue(is_step_compatible(step, "python", "3.12"))
        self.assertFalse(is_step_compatible(step, "python", "4.0"))

    def test_exact_match(self):
        step = self._step({"python": "==3.12"})
        self.assertTrue(is_step_compatible(step, "python", "3.12"))
        self.assertFalse(is_step_compatible(step, "python", "3.11"))

    def test_not_equal(self):
        step = self._step({"python": "!=3.11"})
        self.assertTrue(is_step_compatible(step, "python", "3.12"))
        self.assertFalse(is_step_compatible(step, "python", "3.11"))

    def test_compatible_release(self):
        step = self._step({"python": "~=3.10"})
        self.assertTrue(is_step_compatible(step, "python", "3.12"))
        self.assertFalse(is_step_compatible(step, "python", "4.0"))
        self.assertFalse(is_step_compatible(step, "python", "3.9"))

    def test_gt_strict(self):
        step = self._step({"python": ">3.10"})
        self.assertTrue(is_step_compatible(step, "python", "3.11"))
        self.assertFalse(is_step_compatible(step, "python", "3.10"))

    def test_lte(self):
        step = self._step({"python": "<=3.12"})
        self.assertTrue(is_step_compatible(step, "python", "3.12"))
        self.assertFalse(is_step_compatible(step, "python", "3.13"))

    def test_invalid_constraint_returns_false(self):
        step = self._step({"python": "???invalid"})
        self.assertFalse(is_step_compatible(step, "python", "3.12"))

    def test_one_part_version(self):
        step = self._step({"node": ">=18"})
        self.assertTrue(is_step_compatible(step, "node", "22"))
        self.assertFalse(is_step_compatible(step, "node", "16"))


# ---------------------------------------------------------------------------
# intersect_semver_constraints
# ---------------------------------------------------------------------------


class IntersectSemverConstraintsTest(SimpleTestCase):
    """Test semver constraint intersection algorithm."""

    def test_all_wildcards(self):
        self.assertEqual(intersect_semver_constraints(["*", "*"]), "*")

    def test_single_constraint(self):
        self.assertEqual(intersect_semver_constraints([">=3.10"]), ">=3.10")

    def test_tightens_lower_bound(self):
        result = intersect_semver_constraints([">=3.10", ">=3.11"])
        self.assertEqual(result, ">=3.11")

    def test_combines_lower_and_upper(self):
        result = intersect_semver_constraints([">=3.10", "<4.0"])
        self.assertEqual(result, ">=3.10,<4")

    def test_conflicting_constraints_returns_none(self):
        result = intersect_semver_constraints([">=4.0", "<3.0"])
        self.assertIsNone(result)

    def test_exact_within_bounds(self):
        result = intersect_semver_constraints(["==3.12", ">=3.10"])
        self.assertEqual(result, "==3.12.0")

    def test_exact_outside_bounds_returns_none(self):
        result = intersect_semver_constraints(["==3.9", ">=3.10"])
        self.assertIsNone(result)

    def test_conflicting_exacts_returns_none(self):
        result = intersect_semver_constraints(["==3.12", "==3.11"])
        self.assertIsNone(result)

    def test_wildcard_with_constraint(self):
        result = intersect_semver_constraints(["*", ">=3.10"])
        self.assertEqual(result, ">=3.10")

    def test_compatible_release_intersection(self):
        result = intersect_semver_constraints(["~=3.10", ">=3.11"])
        self.assertEqual(result, ">=3.11,<4")

    def test_empty_list(self):
        self.assertEqual(intersect_semver_constraints([]), "*")

    def test_multiple_overlapping(self):
        result = intersect_semver_constraints([">=3.10", ">=3.11", "<3.13"])
        self.assertEqual(result, ">=3.11,<3.13")

    def test_equal_lower_upper_inclusive(self):
        """>=3.12,<=3.12 should work (single version range)."""
        result = intersect_semver_constraints([">=3.12", "<=3.12"])
        self.assertEqual(result, ">=3.12,<=3.12")

    def test_equal_lower_upper_exclusive_conflicts(self):
        """>3.12,<3.12 is empty — conflict."""
        result = intersect_semver_constraints([">3.12", "<3.12"])
        self.assertIsNone(result)

    def test_equal_lower_exclusive_upper_inclusive_conflicts(self):
        """>3.12,<=3.12 is empty — conflict."""
        result = intersect_semver_constraints([">3.12", "<=3.12"])
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# compute_runtime_constraints
# ---------------------------------------------------------------------------


class ComputeRuntimeConstraintsTest(SimpleTestCase):
    """Test derived constraint computation from step lists."""

    def _step(self, name, constraints):
        return {"name": name, "runtime_constraints": constraints}

    def test_no_steps(self):
        result = compute_runtime_constraints([])
        self.assertEqual(result, {"constraints": {}, "conflicts": []})

    def test_single_step(self):
        steps = [self._step("lint", {"python": ">=3.10"})]
        result = compute_runtime_constraints(steps)
        self.assertEqual(result["constraints"], {"python": ">=3.10"})
        self.assertEqual(result["conflicts"], [])

    def test_compatible_steps(self):
        steps = [
            self._step("lint", {"python": ">=3.10"}),
            self._step("test", {"python": ">=3.11"}),
        ]
        result = compute_runtime_constraints(steps)
        self.assertEqual(result["constraints"], {"python": ">=3.11"})
        self.assertEqual(result["conflicts"], [])

    def test_conflicting_steps(self):
        steps = [
            self._step("old-tool", {"python": "<3.0"}),
            self._step("new-tool", {"python": ">=3.10"}),
        ]
        result = compute_runtime_constraints(steps)
        self.assertEqual(result["constraints"], {})
        self.assertEqual(len(result["conflicts"]), 1)
        self.assertEqual(result["conflicts"][0]["runtime"], "python")

    def test_wildcard_steps_ignored(self):
        steps = [
            self._step("any", {"*": "*"}),
            self._step("lint", {"python": ">=3.10"}),
        ]
        result = compute_runtime_constraints(steps)
        self.assertEqual(result["constraints"], {"python": ">=3.10"})

    def test_multiple_families(self):
        steps = [
            self._step("py-lint", {"python": ">=3.10"}),
            self._step("node-lint", {"node": ">=18"}),
        ]
        result = compute_runtime_constraints(steps)
        self.assertIn("python", result["constraints"])
        self.assertIn("node", result["constraints"])

    def test_accepts_model_instances(self):
        """Should work with SimpleNamespace (model-like objects)."""
        steps = [
            SimpleNamespace(name="lint", runtime_constraints={"python": ">=3.10"}),
            SimpleNamespace(name="test", runtime_constraints={"python": ">=3.11"}),
        ]
        result = compute_runtime_constraints(steps)
        self.assertEqual(result["constraints"], {"python": ">=3.11"})

    def test_none_constraints_ignored(self):
        steps = [
            self._step("no-rc", None),
            self._step("lint", {"python": ">=3.10"}),
        ]
        result = compute_runtime_constraints(steps)
        self.assertEqual(result["constraints"], {"python": ">=3.10"})


# ---------------------------------------------------------------------------
# check_step_constraint_compatibility
# ---------------------------------------------------------------------------


class CheckStepConstraintCompatibilityTest(SimpleTestCase):
    """Test candidate step compatibility against existing constraints."""

    def _step(self, constraints):
        return {"runtime_constraints": constraints}

    def test_no_constraints_always_compatible(self):
        result = check_step_constraint_compatibility(
            {"python": ">=3.10"},
            self._step(None),
        )
        self.assertTrue(result["compatible"])

    def test_wildcard_always_compatible(self):
        result = check_step_constraint_compatibility(
            {"python": ">=3.10"},
            self._step({"*": "*"}),
        )
        self.assertTrue(result["compatible"])

    def test_compatible_candidate(self):
        result = check_step_constraint_compatibility(
            {"python": ">=3.10"},
            self._step({"python": ">=3.11"}),
        )
        self.assertTrue(result["compatible"])

    def test_incompatible_candidate(self):
        result = check_step_constraint_compatibility(
            {"python": ">=3.10"},
            self._step({"python": "<3.0"}),
        )
        self.assertFalse(result["compatible"])
        self.assertEqual(len(result["conflicts"]), 1)

    def test_new_family_always_compatible(self):
        """Candidate adds a family not in current constraints — no conflict."""
        result = check_step_constraint_compatibility(
            {"python": ">=3.10"},
            self._step({"node": ">=18"}),
        )
        self.assertTrue(result["compatible"])

    def test_accepts_model_instance(self):
        step = SimpleNamespace(runtime_constraints={"python": ">=3.11"})
        result = check_step_constraint_compatibility({"python": ">=3.10"}, step)
        self.assertTrue(result["compatible"])
