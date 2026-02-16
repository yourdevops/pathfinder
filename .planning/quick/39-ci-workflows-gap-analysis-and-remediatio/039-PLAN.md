---
phase: quick-039
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - docs/ci-workflows/REMEDIATION.md
autonomous: true

must_haves:
  truths:
    - "All 19 gaps are categorized into logical remediation phases"
    - "Each phase has clear goal, gap references, complexity estimate, and dependencies"
    - "Phases are ordered for sequential execution with minimal rework"
    - "Document is actionable as input for GSD phase creation"
  artifacts:
    - path: "docs/ci-workflows/REMEDIATION.md"
      provides: "Complete gap analysis with phased remediation plan"
      contains: "## Phase"
  key_links: []
---

<objective>
Create a comprehensive CI Workflows Gap Analysis and Remediation Plan document that catalogs all 19 gaps between design docs and implementation, then organizes them into logical GSD phases for sequential execution.

Purpose: Provide a single reference document that maps every design-implementation gap and prescribes a phased remediation strategy. This document will be the input for creating consecutive GSD phases.

Output: `docs/ci-workflows/REMEDIATION.md`
</objective>

<execution_context>
@/Users/fandruhin/.claude/get-shit-done/workflows/execute-plan.md
@/Users/fandruhin/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@docs/ci-workflows/README.md
@docs/ci-workflows/steps-catalog.md
@docs/ci-workflows/workflow-definition.md
@docs/ci-workflows/versioning.md
@docs/ci-workflows/build-lifecycle.md
@docs/ci-workflows/build-authorization.md
@docs/ci-workflows/logging.md
@docs/ci-workflows/plugin-interface.md
@docs/ci-workflows/state.md
@core/models.py (CIStep, CIWorkflow, CIWorkflowVersion, Build, StepsRepository models)
@plugins/github/plugin.py (CICapableMixin implementation)
@core/ci_steps.py (step scanning logic)
@core/tasks.py (verify_build, push_ci_manifest, poll_build_details)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create CI Workflows Gap Analysis and Remediation Plan</name>
  <files>docs/ci-workflows/REMEDIATION.md</files>
  <action>
Create `docs/ci-workflows/REMEDIATION.md` with the following structure and content:

## Document Structure

### 1. Header and Purpose
- Title: "CI Workflows — Gap Analysis and Remediation Plan"
- Date, status (draft), scope (all 9 design docs vs implementation)
- Purpose: bridge every gap between docs/ci-workflows/ design and core/ implementation
- How to use: each remediation phase maps to a future GSD phase

### 2. Gap Inventory Table
A summary table of ALL 19 gaps with columns:
- ID (GAP-01 through GAP-19)
- Name (short label)
- Design Doc (which doc defines it)
- Severity (critical / high / medium / low)
- Remediation Phase (which proposed phase fixes it)

Severity criteria:
- **Critical**: Data integrity or security risk (hard deletes losing data, missing verification states)
- **High**: Core workflow feature gap (versioning, change detection, engine identity)
- **Medium**: Operational feature gap (logging, cleanup, sync triggers)
- **Low**: Code quality or naming inconsistency (field rename, dead code)

### 3. Detailed Gap Descriptions (one subsection per gap)
For each of the 19 gaps, document:
- **Gap ID and Name**
- **Design Reference**: Exact doc file and section
- **Current Implementation**: What exists today (file paths, field names, behavior)
- **Gap Description**: What is missing or wrong
- **Impact**: What breaks or is suboptimal without this fix
- **Remediation**: Specific changes needed (models, views, tasks, templates)

Use the gap analysis provided in the planning context as the source. Enrich with exact file paths from the codebase.

### 4. Remediation Phases
Organize the 19 gaps into 5-7 phases. Each phase section includes:
- **Phase Name** (e.g., "Phase R1: Step Identity and Tracking")
- **Goal** (outcome-shaped, not task-shaped)
- **Gaps Addressed** (list of GAP-IDs)
- **Estimated Complexity** (Small: 1-2 plans / Medium: 2-3 plans / Large: 3-4 plans)
- **Dependencies** (which remediation phases must complete first)
- **Key Changes**: bullet list of models/views/tasks/templates affected
- **Risk Notes**: what could go wrong, migration considerations

### Phase Organization Logic

Group gaps by these principles:
1. **Dependency order**: Foundation changes before features that depend on them
2. **Same-subsystem**: Gaps touching the same models/files grouped together
3. **Vertical slices**: Each phase delivers a testable outcome

**Proposed phase groupings:**

**Phase R1: Step Identity and Change Tracking** (GAP-1, GAP-2, GAP-3, GAP-4)
- Goal: Steps have proper identity (slug), per-file versioning, change detection, and soft-delete
- Rationale: All four gaps are on CIStep model and step scanning. Foundation for everything else.
- Complexity: Large (3-4 plans) — schema migration, scan rewrite, change detection logic, archive workflow
- Dependencies: None

**Phase R2: Workflow Model Hardening** (GAP-8, GAP-9, GAP-10)
- Goal: CIWorkflow has explicit engine field, step ordering validation, and archived status
- Rationale: Three distinct but related workflow model gaps. GAP-8 (engine) is needed by GAP-9 (ordering validation uses engine-specific rules)
- Complexity: Small (1-2 plans) — model field additions, validation logic, UI toggle
- Dependencies: None (can run parallel with R1)

**Phase R3: Build Model Corrections** (GAP-14, GAP-15, GAP-16)
- Goal: Build model is engine-agnostic, has correct verification states, and categorizes by manifest_id
- Rationale: Three build-related gaps that should ship together for consistent build handling
- Complexity: Small (1-2 plans) — field rename, status addition, categorization fix
- Dependencies: R2 (GAP-14 needs manifest_id which uses workflow engine)

**Phase R4: Sync Operations and Logging** (GAP-6, GAP-7, GAP-5)
- Goal: Step repository syncs are triggered by webhooks and scheduled tasks, all sync operations are logged with per-step detail, branch protection is validated
- Rationale: Sync triggers, logging, and branch protection are all sync-operation concerns
- Complexity: Medium (2-3 plans) — new models, webhook handler, scheduled task, validation logic, UI for sync history
- Dependencies: R1 (sync logging references step slugs and archive actions from R1)

**Phase R5: Version Lifecycle Automation** (GAP-11, GAP-12)
- Goal: Patch versions auto-push to services; old versions cleaned up per retention policy
- Rationale: Both are version lifecycle concerns that operate post-publish
- Complexity: Medium (2-3 plans) — auto-update task, retention settings, cleanup task, deletion guards
- Dependencies: R2 (needs workflow archived status), R3 (cleanup references builds)

**Phase R6: Manifest and Plugin Interface** (GAP-13, GAP-17, GAP-18, GAP-19)
- Goal: Artifact discovery via CI plugin API, CI variables injected into manifests, step validation API endpoint, manifest_path cleanup
- Rationale: Plugin interface gaps that affect manifest generation and artifact handling
- Complexity: Medium (2-3 plans) — plugin method additions, manifest template changes, new API endpoint, dead code removal
- Dependencies: R2 (manifest generation uses engine field), R3 (artifact ref resolution relates to build model)

### 5. Migration and Risk Assessment
- Database migrations: List all model changes across all phases with migration order considerations
- Data migration: Steps need slug backfill from directory_name; commit_sha needs per-file recalculation on next sync
- Breaking changes: github_run_id rename, hard-delete to soft-delete transition
- Rollback strategy: Each phase should be independently deployable

### 6. Implementation Priority Matrix
A 2x2 matrix (Impact vs Effort) placing each gap:
- High Impact / Low Effort: Do first (quick wins)
- High Impact / High Effort: Plan carefully (R1)
- Low Impact / Low Effort: Bundle with related work
- Low Impact / High Effort: Defer or simplify

### 7. What Is Already Implemented
List the items from the "ALREADY IMPLEMENTED" section of the gap analysis to provide completeness and show that the remediation plan builds on solid existing work.

### Formatting Notes
- Use standard Markdown (no HTML)
- Gap IDs are consistent throughout (GAP-01 format)
- File paths are relative to project root
- Each phase has a clear "done when" statement
- Cross-reference design docs by filename (e.g., "per steps-catalog.md, Section: Step Identity")
  </action>
  <verify>
1. File exists: `ls docs/ci-workflows/REMEDIATION.md`
2. Contains all 19 gaps: search for GAP-01 through GAP-19
3. Contains all remediation phases: search for "Phase R1" through "Phase R6"
4. Contains summary table, detailed gaps, phase groupings, migration notes, priority matrix
5. No placeholder text remaining (no TODO, TBD, or "...")
  </verify>
  <done>
docs/ci-workflows/REMEDIATION.md exists with:
- Summary table listing all 19 gaps with severity and phase assignment
- Detailed description of each gap with design reference, current state, and remediation steps
- 5-7 remediation phases with goals, gap lists, complexity estimates, dependencies, and key changes
- Migration risk assessment and implementation priority matrix
- Zero placeholder text — every section is complete and actionable
  </done>
</task>

</tasks>

<verification>
- Document covers all 19 identified gaps without omission
- Each gap maps to exactly one remediation phase
- Phase dependencies form a valid DAG (no circular dependencies)
- Complexity estimates are reasonable for the scope of changes
- Document is self-contained and understandable without reading this plan
</verification>

<success_criteria>
A single comprehensive document at docs/ci-workflows/REMEDIATION.md that:
1. Catalogs all 19 design-implementation gaps with severity ratings
2. Organizes gaps into 5-7 sequentially executable remediation phases
3. Each phase has: goal, gaps addressed, complexity, dependencies, key changes, risks
4. Provides migration/risk assessment for the full remediation effort
5. Is ready to be used as input for creating GSD phases via /gsd:plan-phase
</success_criteria>

<output>
After completion, create `.planning/quick/39-ci-workflows-gap-analysis-and-remediatio/039-SUMMARY.md`
</output>
