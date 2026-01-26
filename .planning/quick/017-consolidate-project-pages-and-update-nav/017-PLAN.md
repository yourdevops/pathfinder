---
phase: quick
plan: 017
type: execute
wave: 1
depends_on: []
files_modified:
  - core/templates/core/components/nav_project.html
  - core/templates/core/projects/_settings_tab.html
  - core/views/projects.py
  - core/templates/core/projects/_members_tab.html
autonomous: true

must_haves:
  truths:
    - "Services is the default landing page when navigating to a project"
    - "Navigation shows only: Services, Environments, Settings (in that order)"
    - "Settings page contains Members section with Add Group button"
    - "Members content (owners/contributors/viewers) is accessible via Settings"
  artifacts:
    - path: "core/templates/core/components/nav_project.html"
      provides: "Updated project sidebar nav with 3 items"
      contains: "Services.*Environments.*Settings"
    - path: "core/templates/core/projects/_settings_tab.html"
      provides: "Settings tab with Members section"
      contains: "Project Members"
    - path: "core/views/projects.py"
      provides: "Updated valid_tabs without members, members context in settings"
      contains: "valid_tabs = ['services', 'environments', 'settings']"
  key_links:
    - from: "nav_project.html"
      to: "projects:detail"
      via: "tab parameter"
      pattern: "tab=services|tab=environments|tab=settings"
    - from: "_settings_tab.html"
      to: "projects:add_member_modal"
      via: "HTMX button"
      pattern: "add_member_modal"
---

<objective>
Consolidate project navigation from 4 items to 3 by removing Details and merging Members into Settings.

Purpose: Simplify project UI by making Services the default landing and consolidating related settings in one place.
Output: Cleaner navigation (Services, Environments, Settings) with Members accessible via Settings tab.
</objective>

<context>
@core/templates/core/components/nav_project.html
@core/templates/core/projects/_settings_tab.html
@core/templates/core/projects/_members_tab.html
@core/views/projects.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update project sidebar navigation</name>
  <files>core/templates/core/components/nav_project.html</files>
  <action>
    Update nav_project.html to:
    1. Remove the "Details" nav item entirely (lines 25-32)
    2. Remove the "Members" nav item entirely (lines 52-59)
    3. Keep only: Services, Environments, Settings (in that order)
    4. Update Services link to be the default (no ?tab= or tab=services):
       - href="{% url 'projects:detail' project_name=current_project.name %}"
       - Active state: {% if not request.GET.tab or request.GET.tab == 'services' %}bg-dark-border{% endif %}
    5. Update Environments link:
       - href with ?tab=environments
       - Active state: {% if request.GET.tab == 'environments' %}bg-dark-border{% endif %}
    6. Add Settings nav item after Environments:
       - href="{% url 'projects:detail' project_name=current_project.name %}?tab=settings"
       - Active state: {% if request.GET.tab == 'settings' %}bg-dark-border{% endif %}
       - Use cog/gear icon (same as currently on Details)

    Navigation order: Services (default), Environments, Settings
  </action>
  <verify>Visual inspection of nav_project.html shows exactly 3 nav items in correct order</verify>
  <done>Project sidebar has only Services, Environments, Settings navigation items</done>
</task>

<task type="auto">
  <name>Task 2: Merge Members content into Settings tab</name>
  <files>core/templates/core/projects/_settings_tab.html</files>
  <action>
    Add a Members section to _settings_tab.html between "SCM Connections" and "Danger Zone":

    1. Add new section with card structure matching existing sections:
       ```html
       <!-- Members Section -->
       <div class="bg-dark-surface border border-dark-border rounded-lg">
           <div class="px-6 py-4 border-b border-dark-border flex items-center justify-between">
               <div>
                   <h2 class="text-lg font-semibold text-dark-text">Project Members</h2>
                   <p class="text-dark-muted text-sm mt-1">Groups with access to this project.</p>
               </div>
               {% if user_project_role == 'owner' %}
               <button hx-get="{% url 'projects:add_member_modal' project_name=project.name %}"
                       hx-target="body"
                       hx-swap="beforeend"
                       class="px-4 py-2 bg-dark-accent hover:bg-dark-accent/80 text-white rounded-lg transition-colors flex items-center gap-2">
                   <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                       <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                   </svg>
                   Add Group
               </button>
               {% endif %}
           </div>
           <div class="p-6">
               {% if memberships %}
               <div class="space-y-4">
                   <!-- Owners -->
                   {% if owners %}
                   <div>
                       <h3 class="text-sm font-semibold text-dark-muted uppercase tracking-wider mb-3">Owners</h3>
                       <ul class="space-y-2">
                           {% for membership in owners %}
                           <li class="flex items-center justify-between py-2 px-3 bg-dark-bg/30 rounded-lg">
                               <div class="flex items-center gap-3">
                                   <div class="w-8 h-8 rounded-full bg-dark-accent/20 flex items-center justify-center">
                                       <svg class="w-4 h-4 text-dark-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                           <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                                       </svg>
                                   </div>
                                   <span class="text-dark-text">{{ membership.group.name }}</span>
                                   <span class="text-dark-muted text-sm">({{ membership.group.memberships.count }} member{{ membership.group.memberships.count|pluralize }})</span>
                               </div>
                               {% if user_project_role == 'owner' %}
                               <form method="post" action="{% url 'projects:remove_member' project_name=project.name group_name=membership.group.name %}"
                                     onsubmit="return confirm('Remove {{ membership.group.name }} from this project?');">
                                   {% csrf_token %}
                                   <button type="submit" class="text-dark-muted hover:text-red-400 transition-colors">
                                       <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                           <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                       </svg>
                                   </button>
                               </form>
                               {% endif %}
                           </li>
                           {% endfor %}
                       </ul>
                   </div>
                   {% endif %}

                   <!-- Contributors -->
                   {% if contributors %}
                   <div>
                       <h3 class="text-sm font-semibold text-dark-muted uppercase tracking-wider mb-3">Contributors</h3>
                       <ul class="space-y-2">
                           {% for membership in contributors %}
                           <li class="flex items-center justify-between py-2 px-3 bg-dark-bg/30 rounded-lg">
                               <div class="flex items-center gap-3">
                                   <div class="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center">
                                       <svg class="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                           <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                                       </svg>
                                   </div>
                                   <span class="text-dark-text">{{ membership.group.name }}</span>
                                   <span class="text-dark-muted text-sm">({{ membership.group.memberships.count }} member{{ membership.group.memberships.count|pluralize }})</span>
                               </div>
                               {% if user_project_role == 'owner' %}
                               <form method="post" action="{% url 'projects:remove_member' project_name=project.name group_name=membership.group.name %}"
                                     onsubmit="return confirm('Remove {{ membership.group.name }} from this project?');">
                                   {% csrf_token %}
                                   <button type="submit" class="text-dark-muted hover:text-red-400 transition-colors">
                                       <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                           <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                       </svg>
                                   </button>
                               </form>
                               {% endif %}
                           </li>
                           {% endfor %}
                       </ul>
                   </div>
                   {% endif %}

                   <!-- Viewers -->
                   {% if viewers %}
                   <div>
                       <h3 class="text-sm font-semibold text-dark-muted uppercase tracking-wider mb-3">Viewers</h3>
                       <ul class="space-y-2">
                           {% for membership in viewers %}
                           <li class="flex items-center justify-between py-2 px-3 bg-dark-bg/30 rounded-lg">
                               <div class="flex items-center gap-3">
                                   <div class="w-8 h-8 rounded-full bg-gray-500/20 flex items-center justify-center">
                                       <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                           <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                                       </svg>
                                   </div>
                                   <span class="text-dark-text">{{ membership.group.name }}</span>
                                   <span class="text-dark-muted text-sm">({{ membership.group.memberships.count }} member{{ membership.group.memberships.count|pluralize }})</span>
                               </div>
                               {% if user_project_role == 'owner' %}
                               <form method="post" action="{% url 'projects:remove_member' project_name=project.name group_name=membership.group.name %}"
                                     onsubmit="return confirm('Remove {{ membership.group.name }} from this project?');">
                                   {% csrf_token %}
                                   <button type="submit" class="text-dark-muted hover:text-red-400 transition-colors">
                                       <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                           <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                       </svg>
                                   </button>
                               </form>
                               {% endif %}
                           </li>
                           {% endfor %}
                       </ul>
                   </div>
                   {% endif %}
               </div>
               {% else %}
               <div class="text-center py-8">
                   <svg class="w-12 h-12 mx-auto text-dark-muted mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                       <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                   </svg>
                   <p class="text-dark-muted">No groups assigned to this project.</p>
                   {% if user_project_role == 'owner' %}
                   <p class="text-dark-muted text-sm mt-1">Add groups to give users access.</p>
                   {% endif %}
               </div>
               {% endif %}
           </div>
       </div>
       ```

    Place this section after SCM Connections and before Danger Zone.
  </action>
  <verify>_settings_tab.html contains Members section with proper HTMX add button</verify>
  <done>Settings tab displays Members section with owners/contributors/viewers and Add Group button</done>
</task>

<task type="auto">
  <name>Task 3: Update view logic for tabs and context</name>
  <files>core/views/projects.py</files>
  <action>
    Update ProjectDetailView in core/views/projects.py:

    1. Change valid_tabs from ['services', 'environments', 'members', 'settings'] to ['services', 'environments', 'settings']
       - Update both occurrences (lines 71 and 81)

    2. Move members context loading from the 'members' tab block to the 'settings' tab block:
       - Currently lines 92-97 load members context when tab == 'members'
       - Move this logic into the 'settings' block (elif tab == 'settings')
       - The settings block should now be:
         ```python
         elif tab == 'settings':
             context['form'] = ProjectUpdateForm(instance=self.project)
             # Members context (merged from members tab)
             memberships = self.project.memberships.select_related('group').order_by('project_role')
             context['memberships'] = memberships
             context['owners'] = [m for m in memberships if m.project_role == 'owner']
             context['contributors'] = [m for m in memberships if m.project_role == 'contributor']
             context['viewers'] = [m for m in memberships if m.project_role == 'viewer']
         ```

    3. Remove the entire 'elif tab == members' block (lines 91-97)

    4. Update AddMemberModalView.post() redirect (line 278):
       - Change from: reverse(...) + '?tab=members'
       - Change to: reverse(...) + '?tab=settings'

    5. Update RemoveMemberView.post() redirect (line 293):
       - Currently redirects to project detail without tab param
       - Change to redirect to settings tab: redirect('projects:detail', ...) becomes:
         ```python
         return redirect(reverse('projects:detail', kwargs={'project_name': self.project.name}) + '?tab=settings')
         ```
       - Add import: from django.urls import reverse (already imported at top)
  </action>
  <verify>python manage.py check passes; valid_tabs has 3 items; settings tab loads members context</verify>
  <done>View returns services as default, valid_tabs excludes members, settings tab includes members context</done>
</task>

<task type="auto">
  <name>Task 4: Delete obsolete members tab template</name>
  <files>core/templates/core/projects/_members_tab.html</files>
  <action>
    Delete the file core/templates/core/projects/_members_tab.html

    This template is no longer needed since members content is now integrated into _settings_tab.html.

    Command: rm core/templates/core/projects/_members_tab.html
  </action>
  <verify>File no longer exists: ls core/templates/core/projects/_members_tab.html returns error</verify>
  <done>_members_tab.html deleted, no orphaned template</done>
</task>

</tasks>

<verification>
1. Navigate to a project - should land on Services tab (no ?tab= in URL)
2. Sidebar shows only 3 items: Services, Environments, Settings
3. Click Settings - shows Project Info, Env Vars, SCM Connections, Members, Danger Zone
4. Members section in Settings has Add Group button (for owners)
5. Can add/remove groups from Settings page
6. No 404 errors when navigating tabs
</verification>

<success_criteria>
- Project landing page is Services (default tab)
- Navigation has exactly 3 items: Services, Environments, Settings
- Members management works from Settings tab
- _members_tab.html template deleted
- python manage.py check passes
</success_criteria>

<output>
After completion, create `.planning/quick/017-consolidate-project-pages-and-update-nav/017-SUMMARY.md`
</output>
