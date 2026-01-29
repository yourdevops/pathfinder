"""CI Manifest utilities: runtime compatibility checking for CI workflows."""
import re

import semver

from core.models import CIStep


def normalize_version(version_str: str) -> str:
    """
    Normalize version string to 3-part semver format.

    "3.11" -> "3.11.0"
    "3" -> "3.0.0"
    "1.2.3" -> "1.2.3"
    """
    parts = version_str.strip().split('.')
    while len(parts) < 3:
        parts.append('0')
    return '.'.join(parts[:3])


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
    if constraint_value == '*':
        return True

    # Parse constraint: e.g. ">=3.10", "<4.0", "==3.12"
    match = re.match(r'^(>=|<=|>|<|==|!=|~=)?\s*(.+)$', str(constraint_value))
    if not match:
        return False

    operator = match.group(1) or '>='
    constraint_ver_str = match.group(2).strip()

    try:
        normalized_runtime = normalize_version(runtime_version)
        normalized_constraint = normalize_version(constraint_ver_str)

        runtime_ver = semver.Version.parse(normalized_runtime)
        constraint_ver = semver.Version.parse(normalized_constraint)

        # Map operators to comparisons
        if operator == '>=':
            return runtime_ver >= constraint_ver
        elif operator == '<=':
            return runtime_ver <= constraint_ver
        elif operator == '>':
            return runtime_ver > constraint_ver
        elif operator == '<':
            return runtime_ver < constraint_ver
        elif operator == '==':
            return runtime_ver == constraint_ver
        elif operator == '!=':
            return runtime_ver != constraint_ver
        elif operator == '~=':
            # Compatible release: ~=3.10 means >=3.10, <4.0
            return runtime_ver >= constraint_ver and runtime_ver.major == constraint_ver.major
        else:
            return False
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
    all_steps = CIStep.objects.all().select_related('repository').order_by('phase', 'name')

    compatible = []
    incompatible = []

    for step in all_steps:
        if is_step_compatible(step, runtime_family, runtime_version):
            compatible.append(step)
        else:
            incompatible.append(step)

    return compatible, incompatible
