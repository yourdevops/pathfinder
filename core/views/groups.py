from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages

from ..decorators import AdminRequiredMixin
from ..forms import GroupCreateForm, GroupEditForm, GroupAddMemberForm
from ..models import Group, GroupMembership, User


class GroupListView(AdminRequiredMixin, View):
    """Display list of all groups."""

    template_name = "core/groups/list.html"

    def get(self, request):
        groups = (
            Group.objects.all().prefetch_related("memberships__user").order_by("name")
        )
        return render(request, self.template_name, {"groups": groups})


class GroupDetailView(AdminRequiredMixin, View):
    """Display group detail with members."""

    template_name = "core/groups/detail.html"

    def get(self, request, group_name):
        group = get_object_or_404(Group, name=group_name)
        members = GroupMembership.objects.filter(group=group).select_related("user")
        add_member_form = GroupAddMemberForm(group=group)

        return render(
            request,
            self.template_name,
            {
                "group": group,
                "members": members,
                "add_member_form": add_member_form,
            },
        )


class GroupCreateView(AdminRequiredMixin, View):
    """Create a new group."""

    template_name = "core/groups/create.html"

    def get(self, request):
        return render(request, self.template_name, {"form": GroupCreateForm()})

    def post(self, request):
        form = GroupCreateForm(request.POST)
        if form.is_valid():
            group = Group.objects.create(
                name=form.cleaned_data["name"],
                description=form.cleaned_data["description"],
                system_roles=form.cleaned_data["system_roles"],
                status="active",
                source="local",
            )
            messages.success(request, f'Group "{group.name}" created successfully.')
            return redirect("groups:detail", group_name=group.name)

        return render(request, self.template_name, {"form": form})


class GroupEditView(AdminRequiredMixin, View):
    """Edit group settings."""

    template_name = "core/groups/edit.html"

    def get(self, request, group_name):
        group = get_object_or_404(Group, name=group_name)
        form = GroupEditForm(
            initial={
                "description": group.description,
                "status": group.status,
                "system_roles": group.system_roles,
            }
        )
        return render(request, self.template_name, {"group": group, "form": form})

    def post(self, request, group_name):
        group = get_object_or_404(Group, name=group_name)
        form = GroupEditForm(request.POST)

        if form.is_valid():
            group.description = form.cleaned_data["description"]
            group.status = form.cleaned_data["status"]
            group.system_roles = form.cleaned_data["system_roles"]
            group.save()

            messages.success(request, f'Group "{group.name}" updated successfully.')
            return redirect("groups:detail", group_name=group.name)

        return render(request, self.template_name, {"group": group, "form": form})


class GroupDeleteView(AdminRequiredMixin, View):
    """Delete a group."""

    def post(self, request, group_name):
        group = get_object_or_404(Group, name=group_name)

        # Prevent deletion of admins group
        if group.name == "admins":
            messages.error(request, "The admins group cannot be deleted.")
            return redirect("groups:list")

        name = group.name
        group.delete()
        messages.success(request, f'Group "{name}" deleted successfully.')
        return redirect("groups:list")


class GroupAddMemberView(AdminRequiredMixin, View):
    """Add a user to a group."""

    def post(self, request, group_name):
        group = get_object_or_404(Group, name=group_name)
        form = GroupAddMemberForm(request.POST, group=group)

        if form.is_valid():
            user = form.cleaned_data["user"]
            GroupMembership.objects.get_or_create(group=group, user=user)
            messages.success(request, f'User "{user.username}" added to group.')
        else:
            messages.error(request, "Could not add user to group.")

        return redirect("groups:detail", group_name=group.name)


class GroupRemoveMemberView(AdminRequiredMixin, View):
    """Remove a user from a group."""

    def post(self, request, group_name, user_uuid):
        group = get_object_or_404(Group, name=group_name)
        user = get_object_or_404(User, uuid=user_uuid)

        membership = GroupMembership.objects.filter(group=group, user=user).first()
        if membership:
            membership.delete()
            messages.success(request, f'User "{user.username}" removed from group.')
        else:
            messages.error(request, "User is not a member of this group.")

        return redirect("groups:detail", group_name=group.name)
