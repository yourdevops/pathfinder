"""Template CRUD views: list, detail, register, deregister, sync status."""

import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from core.forms.templates import TemplateRegisterForm
from core.git_utils import (
    build_authenticated_git_url,
    cleanup_repo,
    clone_repo_full,
    clone_repo_shallow,
    list_tags_from_repo,
    parse_version_tag,
    read_pathfinder_manifest,
)
from core.models import Template, TemplateVersion
from core.permissions import OperatorRequiredMixin, has_system_role

logger = logging.getLogger(__name__)


class TemplateListView(LoginRequiredMixin, View):
    """List all registered service templates."""

    def get(self, request):
        templates = Template.objects.annotate(version_count=Count("versions")).order_by("name")
        is_operator = request.user.is_authenticated and (
            has_system_role(request.user, "admin") or has_system_role(request.user, "operator")
        )
        return render(
            request,
            "core/templates/list.html",
            {
                "templates": templates,
                "is_operator": is_operator,
            },
        )


class TemplateDetailView(LoginRequiredMixin, View):
    """Show template detail with metadata and versions."""

    def get(self, request, template_name):
        template = get_object_or_404(Template, name=template_name)
        versions = template.versions.order_by("-sort_key")
        is_operator = request.user.is_authenticated and (
            has_system_role(request.user, "admin") or has_system_role(request.user, "operator")
        )
        can_delete = is_operator and not template.services.exists()
        return render(
            request,
            "core/templates/detail.html",
            {
                "template": template,
                "versions": versions,
                "is_operator": is_operator,
                "can_delete": can_delete,
            },
        )


class TemplateRegisterView(OperatorRequiredMixin, View):
    """Register a new service template from a git repository."""

    def get(self, request):
        form = TemplateRegisterForm()
        return render(
            request,
            "core/templates/register.html",
            {"form": form},
        )

    def post(self, request):
        form = TemplateRegisterForm(request.POST)
        if not form.is_valid():
            return render(request, "core/templates/register.html", {"form": form})

        git_url = form.cleaned_data["git_url"]
        connection = form.cleaned_data.get("connection")

        # Build authenticated URL if connection provided
        auth_url = build_authenticated_git_url(git_url, connection) if connection else None

        # Step 1: Shallow clone to read manifest
        try:
            repo, temp_dir = clone_repo_shallow(git_url, auth_url=auth_url)
        except Exception as e:
            form.add_error("git_url", f"Failed to clone repository: {e}")
            return render(request, "core/templates/register.html", {"form": form})

        try:
            manifest = read_pathfinder_manifest(temp_dir)
        except FileNotFoundError:
            cleanup_repo(repo, temp_dir)
            form.add_error("git_url", "pathfinder.yaml not found in repository root.")
            return render(request, "core/templates/register.html", {"form": form})
        except ValueError as e:
            cleanup_repo(repo, temp_dir)
            form.add_error("git_url", f"Invalid manifest: {e}")
            return render(request, "core/templates/register.html", {"form": form})

        cleanup_repo(repo, temp_dir)

        # Step 2: Check name uniqueness
        template_name = manifest["name"]
        if Template.objects.filter(name=template_name).exists():
            form.add_error("git_url", f'Template "{template_name}" is already registered.')
            return render(request, "core/templates/register.html", {"form": form})

        # Step 3: Create Template record
        template = Template.objects.create(
            name=template_name,
            description=manifest.get("description", ""),
            git_url=git_url,
            connection=connection,
            runtimes=manifest.get("runtimes", []),
            required_vars=manifest.get("required_vars", {}),
            sync_status="synced",
            last_synced_at=timezone.now(),
            created_by=request.user.username,
        )

        # Step 4: Full clone to list tags and create versions
        try:
            full_repo, full_temp_dir = clone_repo_full(git_url, auth_url=auth_url)
            tags = list_tags_from_repo(full_repo)
            for tag_info in tags:
                parsed = parse_version_tag(tag_info["name"])
                if parsed:
                    TemplateVersion.objects.create(
                        template=template,
                        tag_name=tag_info["name"],
                        commit_sha=tag_info["commit_sha"],
                        sort_key=parsed["sort_key"],
                    )
            template.last_synced_sha = full_repo.head.commit.hexsha
            template.save(update_fields=["last_synced_sha"])
            cleanup_repo(full_repo, full_temp_dir)
        except Exception as e:
            logger.warning(f"Failed to list tags for template {template_name}: {e}")
            # Template is created but without versions - that's OK

        messages.success(request, f'Template "{template_name}" registered successfully.')
        return redirect("templates:detail", template_name=template.name)


class TemplateDeregisterView(OperatorRequiredMixin, View):
    """Deregister (delete) a template with guard against service references."""

    def post(self, request, template_name):
        template = get_object_or_404(Template, name=template_name)
        if template.services.exists():
            messages.error(
                request,
                "Cannot delete template — services reference it.",
            )
            return redirect("templates:detail", template_name=template.name)
        name = template.name
        template.delete()
        messages.success(request, f'Template "{name}" has been deregistered.')
        return redirect("templates:list")


class TemplateSyncStatusView(LoginRequiredMixin, View):
    """HTMX partial returning sync status badge for auto-refresh."""

    def get(self, request, template_name):
        template = get_object_or_404(Template, name=template_name)
        return render(
            request,
            "core/templates/_sync_status.html",
            {"template": template},
        )
