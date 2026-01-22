---
phase: quick-003
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - core/views/setup.py
autonomous: true

must_haves:
  truths:
    - "User cannot access admin registration without first entering valid unlock token"
    - "Stale session with unlock_verified=True does not bypass token validation"
    - "Fresh install shows unlock token input, not registration form"
  artifacts:
    - path: "core/views/setup.py"
      provides: "Secure UnlockView with token existence validation"
      contains: "get_unlock_token_path"
  key_links:
    - from: "core/views/setup.py"
      to: "core/utils.py"
      via: "get_unlock_token_path import"
      pattern: "get_unlock_token_path\\(\\)\\.exists\\(\\)"
---

<objective>
Fix critical security vulnerability where users can bypass unlock token validation and go directly to admin account creation.

Purpose: The unlock_verified session flag persists even after setup is complete. When a user clears the database or starts fresh, the old session bypasses token validation. This is a critical security issue on public networks.

Output: Secure UnlockView that validates token file existence before trusting session state.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@core/views/setup.py
@core/utils.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add token existence validation to UnlockView</name>
  <files>core/views/setup.py</files>
  <action>
Modify UnlockView to validate token file exists BEFORE trusting session state:

1. Import `get_unlock_token_path` from `..utils`

2. In the `get()` method, add token existence check:
   - BEFORE checking `request.session.get('unlock_verified')`
   - Call `get_unlock_token_path().exists()` to verify token file exists
   - If token file does NOT exist, clear any stale `unlock_verified` session flag
   - Only trust `unlock_verified` if token file EXISTS

3. In the `post()` method, add same validation:
   - Before processing registration (when `unlock_verified` is True)
   - Verify token file still exists
   - If token file does NOT exist, clear session and show unlock form with error

Logic flow should be:
```python
def get(self, request):
    token_path = get_unlock_token_path()

    # Security check: token must exist for session flag to be valid
    if not token_path.exists():
        # Clear stale session flag if token is gone
        if 'unlock_verified' in request.session:
            del request.session['unlock_verified']

    # Now check session only if token exists
    if token_path.exists() and request.session.get('unlock_verified'):
        return render(request, self.template_name, {
            'unlock_verified': True,
            'form': AdminRegistrationForm(),
        })
    # Show unlock form
    return render(request, self.template_name, {
        'unlock_verified': False,
        'form': UnlockForm(),
    })
```

Apply similar pattern to `post()` method - verify token exists before processing registration.
  </action>
  <verify>
Manual test:
1. Delete db.sqlite3 and secrets/initialUnlockToken (fresh state)
2. Start server: `python manage.py runserver`
3. Navigate to http://localhost:8000/
4. Verify unlock token input field is shown (not registration form)
5. Enter token from secrets/initialUnlockToken
6. Verify registration form appears
7. Complete registration
8. Delete db.sqlite3 (simulate fresh database, keep session cookie)
9. Navigate to http://localhost:8000/
10. Verify unlock token input is shown again (session flag should not bypass)
  </verify>
  <done>
- UnlockView validates token file exists before trusting unlock_verified session flag
- Stale sessions cannot bypass unlock token requirement
- Fresh install always shows unlock token input first
  </done>
</task>

</tasks>

<verification>
1. Fresh install (no db, no token) -> redirected to unlock page -> token input shown
2. After unlock -> registration form shown
3. After registration -> redirected to users list
4. Database cleared + old session -> unlock token input shown (not registration)
5. Token file deleted + old session -> unlock token input shown (not registration)
</verification>

<success_criteria>
- [ ] Token file existence checked before trusting session flag
- [ ] Stale unlock_verified session cleared when token file missing
- [ ] Cannot access registration form without valid unlock token
- [ ] Normal unlock -> register flow still works correctly
</success_criteria>

<output>
After completion, create `.planning/quick/003-fix-unlock-token-bypass-security-issue/003-SUMMARY.md`
</output>
