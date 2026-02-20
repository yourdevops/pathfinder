"""Tests for core.ci_manifest — public API only."""

from types import SimpleNamespace

import pytest

from core.ci_manifest import (
    check_step_constraint_compatibility,
    compute_runtime_constraints,
    intersect_semver_constraints,
    is_step_compatible,
    normalize_version,
)


# ---------------------------------------------------------------------------
# normalize_version
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "input_str, expected",
    [
        ("3", "3.0.0"),
        ("3.11", "3.11.0"),
        ("1.2.3", "1.2.3"),
        ("1.2.3.4", "1.2.3"),
    ],
)
def test_normalize_version(input_str, expected):
    assert normalize_version(input_str) == expected


# ---------------------------------------------------------------------------
# intersect_semver_constraints
# ---------------------------------------------------------------------------
class TestIntersectSemverConstraints:
    def test_empty_and_wildcards(self):
        assert intersect_semver_constraints([]) == "*"
        assert intersect_semver_constraints(["*", "*"]) == "*"
        assert intersect_semver_constraints(["*", ">=3.10"]) == ">=3.10"

    def test_single_constraint(self):
        assert intersect_semver_constraints([">=3.10"]) == ">=3.10"

    def test_tighten_lower_bound(self):
        assert intersect_semver_constraints([">=3.10", ">=3.11"]) == ">=3.11"

    def test_lower_and_upper_bound(self):
        assert intersect_semver_constraints([">=3.10", "<4.0"]) == ">=3.10,<4"

    def test_compound_string(self):
        assert intersect_semver_constraints([">=3.10,<4.0"]) == ">=3.10,<4"

    def test_exclusive_bounds(self):
        assert intersect_semver_constraints([">3.10", "<=3.12"]) == ">3.10,<=3.12"

    def test_compatible_release(self):
        assert intersect_semver_constraints(["~=3.10"]) == ">=3.10,<4"

    def test_exact_match(self):
        assert intersect_semver_constraints(["==3.12"]) == "==3.12.0"
        assert intersect_semver_constraints(["==3.12", ">=3.10"]) == "==3.12.0"

    def test_exact_conflict(self):
        assert intersect_semver_constraints(["==3.11", "==3.12"]) is None

    def test_exact_outside_bounds(self):
        assert intersect_semver_constraints(["==3.9", ">=3.10"]) is None
        assert intersect_semver_constraints(["==4.1", "<4.0"]) is None

    def test_conflicting_bounds(self):
        assert intersect_semver_constraints([">=4.0", "<3.10"]) is None
        assert intersect_semver_constraints([">3.10", "<=3.10"]) is None

    def test_degenerate_equal_bounds(self):
        assert intersect_semver_constraints([">=3.10", "<=3.10"]) == ">=3.10,<=3.10"

    def test_not_equal_ignored(self):
        assert intersect_semver_constraints(["!=3.11", ">=3.10"]) == ">=3.10"


# ---------------------------------------------------------------------------
# is_step_compatible
# ---------------------------------------------------------------------------
def _step(constraints):
    return SimpleNamespace(runtime_constraints=constraints)


class TestIsStepCompatible:
    def test_no_or_empty_constraints(self):
        assert is_step_compatible(_step(None), "python", "3.12")
        assert is_step_compatible(_step({}), "python", "3.12")

    def test_family_missing(self):
        assert not is_step_compatible(_step({"node": ">=18"}), "python", "3.12")

    def test_wildcard(self):
        assert is_step_compatible(_step({"python": "*"}), "python", "3.12")

    def test_gte(self):
        assert is_step_compatible(_step({"python": ">=3.10"}), "python", "3.12")
        assert not is_step_compatible(_step({"python": ">=3.13"}), "python", "3.12")

    def test_exact(self):
        assert is_step_compatible(_step({"python": "==3.12"}), "python", "3.12")
        assert not is_step_compatible(_step({"python": "==3.11"}), "python", "3.12")

    def test_compatible_release(self):
        assert is_step_compatible(_step({"python": "~=3.10"}), "python", "3.12")
        assert not is_step_compatible(_step({"python": "~=3.10"}), "python", "4.0")

    def test_invalid_constraint(self):
        assert not is_step_compatible(_step({"python": "???"}), "python", "3.12")


# ---------------------------------------------------------------------------
# compute_runtime_constraints
# ---------------------------------------------------------------------------
class TestComputeRuntimeConstraints:
    def test_empty(self):
        assert compute_runtime_constraints([]) == {"constraints": {}, "conflicts": []}

    def test_single_step(self):
        steps = [{"name": "lint", "runtime_constraints": {"python": ">=3.10"}}]
        result = compute_runtime_constraints(steps)
        assert result["constraints"] == {"python": ">=3.10"}
        assert result["conflicts"] == []

    def test_wildcard_and_empty_skipped(self):
        steps = [
            {"name": "a", "runtime_constraints": {"*": "*"}},
            {"name": "b", "runtime_constraints": {}},
        ]
        assert compute_runtime_constraints(steps)["constraints"] == {}

    def test_compatible_intersection(self):
        steps = [
            {"name": "lint", "runtime_constraints": {"python": ">=3.10"}},
            {"name": "test", "runtime_constraints": {"python": ">=3.11"}},
        ]
        assert compute_runtime_constraints(steps)["constraints"] == {"python": ">=3.11"}

    def test_conflict(self):
        steps = [
            {"name": "lint", "runtime_constraints": {"python": "==3.10"}},
            {"name": "test", "runtime_constraints": {"python": "==3.12"}},
        ]
        result = compute_runtime_constraints(steps)
        assert result["constraints"] == {}
        assert len(result["conflicts"]) == 1
        assert result["conflicts"][0]["runtime"] == "python"

    def test_multiple_families(self):
        steps = [
            {"name": "lint", "runtime_constraints": {"python": ">=3.10"}},
            {"name": "build", "runtime_constraints": {"node": ">=18"}},
        ]
        result = compute_runtime_constraints(steps)
        assert result["constraints"] == {"python": ">=3.10", "node": ">=18"}


# ---------------------------------------------------------------------------
# check_step_constraint_compatibility
# ---------------------------------------------------------------------------
class TestCheckStepConstraintCompatibility:
    def test_no_constraints_or_wildcard(self):
        assert check_step_constraint_compatibility({"python": ">=3.10"}, {"runtime_constraints": {}})["compatible"]
        assert check_step_constraint_compatibility({"python": ">=3.10"}, {"runtime_constraints": {"*": "*"}})[
            "compatible"
        ]

    def test_compatible(self):
        result = check_step_constraint_compatibility(
            {"python": ">=3.10"}, {"runtime_constraints": {"python": ">=3.11"}}
        )
        assert result["compatible"]

    def test_conflict(self):
        result = check_step_constraint_compatibility({"python": ">=3.12"}, {"runtime_constraints": {"python": "<3.10"}})
        assert not result["compatible"]
        assert len(result["conflicts"]) == 1

    def test_new_family(self):
        result = check_step_constraint_compatibility({"python": ">=3.10"}, {"runtime_constraints": {"node": ">=18"}})
        assert result["compatible"]
