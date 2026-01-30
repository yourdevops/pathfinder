"""CI Manifest utilities: runtime compatibility checking and GitHub Actions manifest generation."""

import re

import semver
import yaml

from core.models import CIStep


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
    match = re.match(r"^(>=|<=|>|<|==|!=|~=)?\s*(.+)$", str(constraint_value))
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
    all_steps = CIStep.objects.all().select_related("repository").order_by("phase", "name")

    compatible = []
    incompatible = []

    for step in all_steps:
        if is_step_compatible(step, runtime_family, runtime_version):
            compatible.append(step)
        else:
            incompatible.append(step)

    return compatible, incompatible


def generate_github_actions_manifest(workflow) -> str:
    """
    Generate a GitHub Actions workflow YAML for a CIWorkflow instance.

    The manifest includes:
    1. Checkout step (auto-injected)
    2. SSP Notify Start step (auto-injected)
    3. User-composed steps (from workflow_steps, ordered)
    4. SSP Notify Complete step (auto-injected)

    Args:
        workflow: CIWorkflow model instance

    Returns:
        YAML string of the GitHub Actions workflow manifest.
    """
    from core.git_utils import parse_git_url

    manifest = {
        "name": f"CI - {workflow.name}",
        "on": {
            "push": {"branches": ["main"]},
        },
        "jobs": {
            "build": {
                "runs-on": "ubuntu-latest",
                "steps": [],
            },
        },
    }

    steps_list = manifest["jobs"]["build"]["steps"]

    # Auto-inject: checkout
    steps_list.append(
        {
            "name": "Checkout",
            "uses": "actions/checkout@v4",
        }
    )

    # Auto-inject: SSP Notify Start
    steps_list.append(
        {
            "name": "Notify SSP - Build Started",
            "uses": "./ci-steps/ssp-notify-start",
        }
    )

    # User-composed steps
    for ws in workflow.workflow_steps.select_related("step__repository").order_by("order"):
        step = ws.step
        repo = step.repository

        # Build uses reference
        parsed = parse_git_url(repo.git_url)
        if parsed and parsed.get("owner") and parsed.get("repo"):
            uses_ref = f"{parsed['owner']}/{parsed['repo']}/ci-steps/{step.directory_name}"
            if step.commit_sha:
                uses_ref += f"@{step.commit_sha}"
            else:
                uses_ref += "@main"
        else:
            uses_ref = f"./ci-steps/{step.directory_name}"

        step_entry = {
            "name": step.name,
            "uses": uses_ref,
        }
        if ws.input_config:
            step_entry["with"] = ws.input_config

        steps_list.append(step_entry)

    # Auto-inject: SSP Notify Complete
    steps_list.append(
        {
            "name": "Notify SSP - Build Complete",
            "uses": "./ci-steps/ssp-notify-complete",
        }
    )

    return yaml.dump(manifest, default_flow_style=False, sort_keys=False)
