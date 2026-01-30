from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages

from ..decorators import AdminRequiredMixin
from ..forms import UserCreateForm, UserEditForm
from ..models import User, Group, GroupMembership


class UserListView(AdminRequiredMixin, View):
    """Display list of all users."""

    template_name = "core/users/list.html"

    def get(self, request):
        users = (
            User.objects.all()
            .prefetch_related("group_memberships__group")
            .order_by("username")
        )
        return render(
            request,
            self.template_name,
            {
                "users": users,
                "form": UserCreateForm(),
            },
        )


class UserCreateView(AdminRequiredMixin, View):
    """Create a new user via modal form."""

    def post(self, request):
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data["username"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
                status=form.cleaned_data["status"],
                source="local",
            )
            messages.success(request, f'User "{user.username}" created successfully.')
            return redirect("users:list")

        # Re-render list with form errors
        users = (
            User.objects.all()
            .prefetch_related("group_memberships__group")
            .order_by("username")
        )
        return render(
            request,
            "core/users/list.html",
            {
                "users": users,
                "form": form,
                "show_modal": True,
            },
        )


class UserEditView(AdminRequiredMixin, View):
    """Edit user details and group memberships."""

    template_name = "core/users/edit.html"

    def get(self, request, uuid):
        user = get_object_or_404(User, uuid=uuid)
        current_groups = Group.objects.filter(memberships__user=user)

        form = UserEditForm(
            user_instance=user,
            initial={
                "email": user.email,
                "status": user.status,
                "groups": current_groups,
            },
        )

        return render(
            request,
            self.template_name,
            {
                "edit_user": user,
                "form": form,
            },
        )

    def post(self, request, uuid):
        user = get_object_or_404(User, uuid=uuid)
        form = UserEditForm(request.POST, user_instance=user)

        if form.is_valid():
            # Update user fields
            user.email = form.cleaned_data["email"]
            user.status = form.cleaned_data["status"]

            # Update password if provided
            if form.cleaned_data.get("new_password"):
                user.set_password(form.cleaned_data["new_password"])

            user.save()

            # Update group memberships
            new_groups = set(form.cleaned_data["groups"])
            current_groups = set(Group.objects.filter(memberships__user=user))

            # Remove from groups no longer selected
            for group in current_groups - new_groups:
                GroupMembership.objects.filter(user=user, group=group).delete()

            # Add to newly selected groups
            for group in new_groups - current_groups:
                GroupMembership.objects.get_or_create(user=user, group=group)

            messages.success(request, f'User "{user.username}" updated successfully.')
            return redirect("users:list")

        return render(
            request,
            self.template_name,
            {
                "edit_user": user,
                "form": form,
            },
        )


class UserDeleteView(AdminRequiredMixin, View):
    """Delete a user."""

    def post(self, request, uuid):
        user = get_object_or_404(User, uuid=uuid)

        # Prevent self-deletion
        if user == request.user:
            messages.error(request, "You cannot delete your own account.")
            return redirect("users:list")

        username = user.username
        user.delete()
        messages.success(request, f'User "{username}" deleted successfully.')
        return redirect("users:list")
