---
task: 004
type: quick
autonomous: true
files_modified:
  - devssp/urls.py

must_haves:
  truths:
    - "Visiting / redirects to /projects/"
    - "Unauthenticated users see login page after redirect chain"
    - "Authenticated users see projects list"
  artifacts:
    - path: "devssp/urls.py"
      provides: "Root URL redirect"
      contains: "RedirectView"
---

<objective>
Add root URL redirect to /projects/

Currently the app has no handler for "/" and returns a 404. Since projects is the primary workflow entry point (LOGIN_REDIRECT_URL already points there), the root URL should redirect to /projects/.

Purpose: Better UX when users navigate to the app root
Output: Working redirect from / to /projects/
</objective>

<context>
@devssp/urls.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add root URL redirect</name>
  <files>devssp/urls.py</files>
  <action>
Add a redirect from "/" to "/projects/" using Django's RedirectView:

1. Import RedirectView from django.views.generic
2. Add path('', RedirectView.as_view(url='/projects/', permanent=False), name='root') as the first URL pattern

Use permanent=False (302) since this is an application redirect that could change, not a permanent SEO redirect.
  </action>
  <verify>
Run Django dev server and verify:
- `curl -I http://localhost:8000/` returns 302 with Location: /projects/
- Browser visiting http://localhost:8000/ ends up at /projects/ (or login if not authenticated)
  </verify>
  <done>Root URL "/" redirects to "/projects/" with 302 status</done>
</task>

</tasks>

<verification>
- `curl -I http://localhost:8000/` shows 302 redirect to /projects/
- No 404 when visiting root URL
</verification>

<success_criteria>
- Visiting http://localhost:8000/ redirects to /projects/
- Unauthenticated users end up at login page (redirect chain: / -> /projects/ -> /auth/login/)
- Authenticated users see projects list
</success_criteria>

<output>
After completion, create `.planning/quick/004-add-root-url-redirect-to-projects/004-SUMMARY.md`
</output>
