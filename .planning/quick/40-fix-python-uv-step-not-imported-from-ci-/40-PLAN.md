---
phase: quick-40
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: [core/ci_steps.py]
autonomous: true
must_haves:
  truths:
    - "Steps with action.yaml are discovered alongside action.yml steps"
    - "The file_path in results uses the actual filename found on disk"
    - "Steps with neither action.yml nor action.yaml are still ignored"
  artifacts:
    - path: "core/ci_steps.py"
      provides: "YAML extension variant matching in discover_steps"
      contains: "yaml"
  key_links:
    - from: "core/ci_steps.py"
      to: "core/tasks.py"
      via: "discover_steps return value"
      pattern: "file_path.*raw_step"
---

<objective>
Fix discover_steps() to match both .yml and .yaml extensions of engine_file_name.

Purpose: The python-uv CI step uses `action.yaml` but discover_steps only matches `action.yml` (the value returned by GitHubPlugin.engine_file_name). Steps using the alternate YAML extension are silently skipped during repository scanning.

Output: Updated core/ci_steps.py that discovers steps regardless of which YAML extension they use.
</objective>

<execution_context>
@/Users/fandruhin/.claude/get-shit-done/workflows/execute-plan.md
@/Users/fandruhin/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@core/ci_steps.py
@core/tasks.py (lines 312-336 — caller of discover_steps, uses file_path for git log)
@plugins/github/plugin.py (line 44-45 — engine_file_name returns "action.yml")
</context>

<tasks>

<task type="auto">
  <name>Task 1: Support both .yml and .yaml extensions in discover_steps</name>
  <files>core/ci_steps.py</files>
  <action>
In `discover_steps()`, build a set of candidate filenames that includes both the given `engine_file_name` and its alternate YAML extension. The logic:

1. After the function signature (line 33, before the for loop), compute the alternate extension variant:
   - If engine_file_name ends with `.yml`, alternate is the same name with `.yaml`
   - If engine_file_name ends with `.yaml`, alternate is the same name with `.yml`
   - Otherwise (non-YAML engine file), no alternate needed
   - Store both in a set, e.g. `candidates = {engine_file_name}` then add the alternate if applicable

2. In the os.walk loop (line 39), change the match check from:
   `if engine_file_name in filenames:`
   to check if ANY candidate is present:
   `matched = candidates & set(filenames)` then `if matched:`

3. When a match is found, use the ACTUAL filename from disk (not the original engine_file_name). Pick the first match from the set intersection (there should only be one per directory). Use this actual filename for both `file_path` construction (line 40) and the `os.path.join(rel_dir, ...)` in the result dict (line 53). This is critical because `file_path` is used downstream in `core/tasks.py` for `git log --follow` per-file SHA lookups.

4. Update the warning message on YAML parse failure (line 47) to use the actual matched filename instead of `engine_file_name`.

5. Update the docstring to mention that both .yml and .yaml variants are checked.

Do NOT change the function signature — plugins still return a single engine_file_name. The extension handling is internal to discover_steps.
  </action>
  <verify>
Run `uv run python manage.py check` to confirm no Django errors. Then verify the logic manually:
- Read the modified file and confirm both extensions are checked
- Confirm the actual found filename (not the requested one) is used in file_path
  </verify>
  <done>
discover_steps("path", "action.yml") finds directories containing either action.yml or action.yaml, and the returned file_path reflects the actual file on disk.
  </done>
</task>

</tasks>

<verification>
- `uv run python manage.py check` passes with no errors
- Code review confirms: candidates set built correctly, actual filename used in results
- No changes to function signature or return structure (backwards compatible)
</verification>

<success_criteria>
Steps using action.yaml (like python-uv) are discovered during CI steps repository scanning, with correct file_path for downstream git operations.
</success_criteria>

<output>
After completion, create `.planning/quick/40-fix-python-uv-step-not-imported-from-ci-/40-SUMMARY.md`
</output>
