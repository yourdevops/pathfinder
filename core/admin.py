from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Group, GroupMembership, Project, Environment, ProjectMembership


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'status', 'source', 'is_staff']
    list_filter = ['status', 'source', 'is_staff', 'is_superuser']
    fieldsets = UserAdmin.fieldsets + (
        ('DevSSP', {'fields': ('uuid', 'status', 'source', 'external_id')}),
    )
    readonly_fields = ['uuid']
    search_fields = ['username', 'email']


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'source', 'created_at']
    list_filter = ['status', 'source']
    search_fields = ['name', 'description']


@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'group', 'created_at']
    list_filter = ['group']
    raw_id_fields = ['user', 'group']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'created_by', 'created_at', 'updated_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'description', 'created_by']
    readonly_fields = ['uuid', 'created_at', 'updated_at']


@admin.register(Environment)
class EnvironmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'project_name', 'is_production', 'is_default', 'status', 'order']
    list_filter = ['status', 'is_production', 'is_default', 'project']
    search_fields = ['name', 'description', 'project__name']
    readonly_fields = ['uuid', 'created_at', 'updated_at']
    raw_id_fields = ['project']

    @admin.display(description='Project')
    def project_name(self, obj):
        return obj.project.name


@admin.register(ProjectMembership)
class ProjectMembershipAdmin(admin.ModelAdmin):
    list_display = ['project', 'group', 'project_role', 'added_by', 'created_at']
    list_filter = ['project_role', 'project', 'group']
    search_fields = ['project__name', 'group__name', 'added_by']
    readonly_fields = ['created_at']
    raw_id_fields = ['project', 'group']
