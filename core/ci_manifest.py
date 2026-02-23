"""CI Manifest utilities: runtime compatibility checking and constraint intersection."""

import re

import semver

from core.models import CIStep

_CONSTRAINT_RE = re.compile(r"^(>=|<=|>|<|==|!=|~=)?\s*(\S+)$")


def normalize_version(version_str: str) -> str:
    """
    Normalize version string to 3-part semver format.

    "3.11" -> "3.11.0"
    "3" -> "3.0.0"
    "1.2.3" -> "1.2.3"
    """
    parts = version_str.strip().split(".")
    while len(parts) < 3:
        parts.append("0")
    return ".".join(parts[:3])


def is_step_compatible(step, runtime_family: str, runtime_version: str) -> bool:
    """
    Check if a CIStep is compatible with the given runtime family and version.

    Args:
        step: CIStep model instance
        runtime_family: e.g. 'python', 'node'
        runtime_version: e.g. '3.12', '22'

    Returns:
        True if step is compatible with the runtime, False otherwise.
    """
    constraints = step.runtime_constraints
    if not constraints:
        return True

    if runtime_family not in constraints:
        return False

    constraint_value = constraints[runtime_family]

    # Wildcard matches all versions
    if constraint_value == "*":
        return True

    # Parse constraint: e.g. ">=3.10", "<4.0", "==3.12"
    match = _CONSTRAINT_RE.match(str(constraint_value))
    if not match:
        return False

    operator = match.group(1) or ">="
    constraint_ver_str = match.group(2).strip()

    try:
        normalized_runtime = normalize_version(runtime_version)
        normalized_constraint = normalize_version(constraint_ver_str)

        runtime_ver = semver.Version.parse(normalized_runtime)
        constraint_ver = semver.Version.parse(normalized_constraint)

        # Map operators to comparisons
        ops = {
            ">=": lambda: runtime_ver >= constraint_ver,
            "<=": lambda: runtime_ver <= constraint_ver,
            ">": lambda: runtime_ver > constraint_ver,
            "<": lambda: runtime_ver < constraint_ver,
            "==": lambda: runtime_ver == constraint_ver,
            "!=": lambda: runtime_ver != constraint_ver,
            # Compatible release: ~=3.10 means >=3.10, <4.0
            "~=": lambda: runtime_ver >= constraint_ver and runtime_ver.major == constraint_ver.major,
        }
        return ops.get(operator, lambda: False)()
    except ValueError:
        return False


def get_compatible_steps(runtime_family: str, runtime_version: str):
    """
    Partition all CISteps into compatible and incompatible lists.

    Args:
        runtime_family: e.g. 'python'
        runtime_version: e.g. '3.12'

    Returns:
        Tuple of (compatible_steps, incompatible_steps), both ordered by phase then name.
    """
    all_steps = CIStep.objects.filter(status="active").select_related("repository").order_by("phase", "name")

    compatible = []
    incompatible = []

    for step in all_steps:
        if is_step_compatible(step, runtime_family, runtime_version):
            compatible.append(step)
        else:
            incompatible.append(step)

    return compatible, incompatible


def _parse_constraint(constraint_str: str):
    """Parse a single constraint string into (operator, semver.Version) pairs.

    Supports compound constraints separated by commas, e.g. ">=3.10,<4.0".
    Returns a list of (operator, version) tuples.
    """
    parts = [c.strip() for c in constraint_str.split(",") if c.strip()]
    parsed = []
    for part in parts:
        match = _CONSTRAINT_RE.match(part)
        if not match:
            continue
        op = match.group(1) or ">="
        ver_str = match.group(2).strip()
        try:
            ver = semver.Version.parse(normalize_version(ver_str))
            parsed.append((op, ver))
        except ValueError:
            continue
    return parsed


def _is_tighter_lower(current, ver, inclusive):
    """Return True if (ver, inclusive) is a tighter lower bound than current."""
    if current is None:
        return True
    cur_ver, cur_inc = current
    if ver > cur_ver:
        return True
    return ver == cur_ver and not cur_inc and inclusive


def _is_tighter_upper(current, ver, inclusive):
    """Return True if (ver, inclusive) is a tighter upper bound than current."""
    if current is None:
        return True
    cur_ver, cur_inc = current
    if ver < cur_ver:
        return True
    return ver == cur_ver and not cur_inc and inclusive


_CONFLICT = object()  # sentinel for exact-version conflicts


def _apply_exact(ver, lower, upper, exact):
    if exact is not None and exact != ver:
        return lower, upper, _CONFLICT
    return lower, upper, ver


def _apply_compatible(ver, lower, upper, exact):
    # ~=3.10 means >=3.10, <(next major)
    if _is_tighter_lower(lower, ver, True):
        lower = (ver, True)
    next_major = semver.Version(ver.major + 1)
    if _is_tighter_upper(upper, next_major, False):
        upper = (next_major, False)
    return lower, upper, exact


def _apply_bound(op, ver, lower, upper, exact):
    bound_ops = {
        ">=": (True, True),  # (is_lower, inclusive)
        ">": (True, False),
        "<=": (False, True),
        "<": (False, False),
    }
    is_lower, inclusive = bound_ops[op]
    if is_lower and _is_tighter_lower(lower, ver, inclusive):
        lower = (ver, inclusive)
    elif not is_lower and _is_tighter_upper(upper, ver, inclusive):
        upper = (ver, inclusive)
    return lower, upper, exact


def _apply_constraint(op, ver, lower, upper, exact):
    """Apply a single (op, ver) constraint, returning updated (lower, upper, exact).

    Returns exact=_CONFLICT sentinel if == constraints conflict.
    """
    if op == "==":
        return _apply_exact(ver, lower, upper, exact)
    if op == "!=":
        return lower, upper, exact
    if op == "~=":
        return _apply_compatible(ver, lower, upper, exact)
    return _apply_bound(op, ver, lower, upper, exact)


def _validate_exact(exact, lower, upper):
    """Check exact version fits within bounds. Returns formatted string or None."""
    if lower is not None:
        lb_ver, lb_inc = lower
        if exact < lb_ver or (exact == lb_ver and not lb_inc):
            return None
    if upper is not None:
        ub_ver, ub_inc = upper
        if exact > ub_ver or (exact == ub_ver and not ub_inc):
            return None
    return f"=={exact}"


def _bounds_conflict(lower, upper):
    """Return True if lower and upper bounds are mutually exclusive."""
    if lower is None or upper is None:
        return False
    lb_ver, lb_inc = lower
    ub_ver, ub_inc = upper
    if lb_ver > ub_ver:
        return True
    return lb_ver == ub_ver and not (lb_inc and ub_inc)


def _format_bounds(lower, upper):
    """Build the result constraint string from lower/upper bounds."""
    parts = []
    if lower is not None:
        lb_ver, lb_inc = lower
        ver_str = _format_version(lb_ver)
        parts.append(f"{'>=' if lb_inc else '>'}{ver_str}")
    if upper is not None:
        ub_ver, ub_inc = upper
        ver_str = _format_version(ub_ver)
        parts.append(f"{'<=' if ub_inc else '<'}{ver_str}")
    if not parts:
        return "*"
    return ",".join(parts)


def intersect_semver_constraints(constraint_strings: list[str]) -> str | None:
    """Intersect a list of semver constraint strings for a single runtime family.

    Args:
        constraint_strings: e.g. [">=3.10", ">=3.11", "<4.0"]

    Returns:
        The tightest combined constraint string, or None if constraints conflict.
        If all are wildcards, returns "*".
    """
    non_wildcard = [c for c in constraint_strings if c.strip() != "*"]
    if not non_wildcard:
        return "*"

    lower, upper, exact = None, None, None
    for cs in non_wildcard:
        for op, ver in _parse_constraint(cs):
            lower, upper, exact = _apply_constraint(op, ver, lower, upper, exact)
            if exact is _CONFLICT:
                return None

    if exact is not None:
        return _validate_exact(exact, lower, upper)
    if _bounds_conflict(lower, upper):
        return None
    return _format_bounds(lower, upper)


def _format_version(ver: semver.Version) -> str:
    """Format a semver Version compactly (drop trailing .0 segments)."""
    if ver.patch == 0 and ver.minor == 0:
        return str(ver.major)
    if ver.patch == 0:
        return f"{ver.major}.{ver.minor}"
    return str(ver)


def _collect_family_constraints(steps):
    """Collect per-family constraints from steps (model instances or dicts)."""
    family_constraints: dict[str, list[tuple[str, str]]] = {}

    for step in steps:
        if hasattr(step, "runtime_constraints"):
            rc, name = step.runtime_constraints, step.name
        else:
            rc, name = step.get("runtime_constraints", {}), step.get("name", "unknown")

        if not rc or rc == {"*": "*"}:
            continue

        for family, constraint in rc.items():
            if family != "*":
                family_constraints.setdefault(family, []).append((str(constraint), name))

    return family_constraints


def compute_runtime_constraints(steps) -> dict:
    """Compute derived runtime constraints from a list of CIStep instances.

    Args:
        steps: List of CIStep instances (or dicts with 'runtime_constraints' and 'name').

    Returns:
        Dict with 'constraints' (family -> range) and 'conflicts' (list of conflict details).
    """
    family_constraints = _collect_family_constraints(steps)
    constraints = {}
    conflicts = []

    for family, entries in family_constraints.items():
        constraint_strings = [e[0] for e in entries]
        step_names = [e[1] for e in entries]
        result = intersect_semver_constraints(constraint_strings)
        if result is None:
            conflicts.append(
                {
                    "runtime": family,
                    "steps": step_names,
                    "constraints": constraint_strings,
                }
            )
        else:
            constraints[family] = result

    return {"constraints": constraints, "conflicts": conflicts}


def check_step_constraint_compatibility(current_constraints: dict, candidate_step) -> dict:
    """Check if adding a candidate step would create constraint conflicts.

    Args:
        current_constraints: Current derived constraints dict (family -> range).
        candidate_step: CIStep instance to check.

    Returns:
        Dict with 'compatible' bool and 'conflicts' list.
    """
    if hasattr(candidate_step, "runtime_constraints"):
        rc = candidate_step.runtime_constraints
    else:
        rc = candidate_step.get("runtime_constraints", {})

    if not rc or rc == {"*": "*"}:
        return {"compatible": True, "conflicts": []}

    conflict_list = []
    for family, constraint in rc.items():
        if family == "*":
            continue
        if family in current_constraints:
            existing = current_constraints[family]
            result = intersect_semver_constraints([existing, str(constraint)])
            if result is None:
                conflict_list.append(
                    {
                        "runtime": family,
                        "existing": existing,
                        "step_constraint": str(constraint),
                    }
                )

    if conflict_list:
        return {"compatible": False, "conflicts": conflict_list}
    return {"compatible": True, "conflicts": []}
