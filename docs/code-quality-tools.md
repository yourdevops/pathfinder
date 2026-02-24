# Code Quality Tools — Evaluation Notes

Tools evaluated for Pathfinder beyond what's already configured (ruff, bandit, semgrep, django-upgrade, checkov, gitleaks).

## Implemented

**import-linter** — Architectural boundary enforcement. Configured in `pyproject.toml` with 3 contracts. Added to pre-commit.

**SonarQube** — Continuous code quality and security analysis. Running on SonarCloud with IDE integration (SonarLint). Covers code smells, bugs, vulnerabilities, duplication, and coverage tracking.

## Recommended Next

| Tool | Purpose | Effort | Notes |
|------|---------|--------|-------|
| **deptry** | Finds unused/missing deps in pyproject.toml | Low | Rust-powered, fast. Native uv support. `[tool.deptry]` in pyproject.toml. |
| **vulture** | Dead code detection | Medium | Needs whitelist for Django patterns (views/models referenced as strings). Start with `--min-confidence 80`. |
| **djLint** | Django template linting/formatting | Low | Catches unclosed tags, accessibility issues. May need tuning for Alpine.js attributes. |
| **mypy + django-stubs** | Type checking | High | Only type checker with proper Django support (model fields, querysets, forms). Gradual adoption possible. |

## Evaluated and Skipped

| Tool | Why Skip |
|------|----------|
| unimport / autoflake | Ruff F401 already handles unused imports |
| pyright | No Django plugin — inferior to mypy for Django-specific types |
| ty (Astral) | Beta, no Django support yet |
| pyre / pyrefly (Meta) | No Django support |
| fixit (Meta) | Overkill — CST-based custom rules with auto-fix, only worth it for recurring project-specific patterns |
| dead (asottile) | Less configurable than vulture, more false positives with Django |
| pylint-django | Marginal benefit over ruff DJ rules, significant perf cost |
| pydeps | Import graph visualization — useful one-off, not CI material |
