from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Group, GroupMembership


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
