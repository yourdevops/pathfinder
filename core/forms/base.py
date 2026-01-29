import re

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from core.models import User, Group, GroupMembership, Project, Environment, IntegrationConnection, SiteConfiguration


class UnlockForm(forms.Form):
    """Form for entering the unlock token."""
    token = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'input-field w-full',
            'placeholder': 'Enter unlock token',
            'autocomplete': 'off',
        }),
        label='Unlock Token'
    )


class AdminRegistrationForm(forms.Form):
    """Form for creating the first admin account."""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'input-field w-full',
            'placeholder': 'Username',
            'autocomplete': 'username',
        }),
        label='Username'
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'input-field w-full',
            'placeholder': 'Email address',
            'autocomplete': 'email',
        }),
        label='Email'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'input-field w-full',
            'placeholder': 'Password',
            'autocomplete': 'new-password',
        }),
        label='Password'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'input-field w-full',
            'placeholder': 'Confirm password',
            'autocomplete': 'new-password',
        }),
        label='Confirm Password'
    )

    def clean_password(self):
        password = self.cleaned_data.get('password')
        try:
            validate_password(password)
        except ValidationError as e:
            raise forms.ValidationError(e.messages)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data


class LoginForm(forms.Form):
    """Form for user login."""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'input-field w-full',
            'placeholder': 'Username',
            'autocomplete': 'username',
        }),
        label='Username'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'input-field w-full',
            'placeholder': 'Password',
            'autocomplete': 'current-password',
        }),
        label='Password'
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-dark-border bg-dark-bg text-dark-accent focus:ring-dark-accent',
        }),
        label='Remember me'
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if username and password:
            self.user_cache = authenticate(
                self.request,
                username=username,
                password=password
            )
            if self.user_cache is None:
                raise forms.ValidationError('Invalid username or password.')
            if not self.user_cache.is_active:
                raise forms.ValidationError('This account has been deactivated.')
        return cleaned_data

    def get_user(self):
        return self.user_cache


class UserCreateForm(forms.Form):
    """Form for creating a new user."""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'input-field w-full',
            'placeholder': 'Username',
        }),
        label='Username'
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'input-field w-full',
            'placeholder': 'Email address',
        }),
        label='Email'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'input-field w-full',
            'placeholder': 'Password',
        }),
        label='Password'
    )
    status = forms.ChoiceField(
        choices=[('active', 'Active'), ('inactive', 'Inactive')],
        widget=forms.Select(attrs={
            'class': 'input-field w-full',
        }),
        initial='active',
        label='Status'
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('A user with this username already exists.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        try:
            validate_password(password)
        except ValidationError as e:
            raise forms.ValidationError(e.messages)
        return password


class UserEditForm(forms.Form):
    """Form for editing an existing user."""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'input-field w-full',
        }),
        label='Email'
    )
    status = forms.ChoiceField(
        choices=[('active', 'Active'), ('inactive', 'Inactive')],
        widget=forms.Select(attrs={
            'class': 'input-field w-full',
        }),
        label='Status'
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.filter(status='active'),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'rounded border-dark-border bg-dark-bg text-dark-accent',
        }),
        required=False,
        label='Group Memberships'
    )
    new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'input-field w-full',
            'placeholder': 'Leave blank to keep current password',
        }),
        label='New Password'
    )

    def __init__(self, *args, user_instance=None, **kwargs):
        self.user_instance = user_instance
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if self.user_instance:
            if User.objects.filter(email=email).exclude(pk=self.user_instance.pk).exists():
                raise forms.ValidationError('A user with this email already exists.')
        return email

    def clean_new_password(self):
        password = self.cleaned_data.get('new_password')
        if password:
            try:
                validate_password(password)
            except ValidationError as e:
                raise forms.ValidationError(e.messages)
        return password


# System role choices for groups
SYSTEM_ROLE_CHOICES = [
    ('admin', 'Admin - Full system access'),
    ('operator', 'Operator - Manage integrations and CI workflows'),
    ('auditor', 'Auditor - Read-only access to all projects'),
]


class GroupCreateForm(forms.Form):
    """Form for creating a new group."""
    name = forms.CharField(
        max_length=63,
        widget=forms.TextInput(attrs={
            'class': 'input-field w-full',
            'placeholder': 'Group name (DNS-compatible)',
        }),
        label='Name',
        help_text='Lowercase letters, numbers, and hyphens only. Max 63 characters.'
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'input-field w-full',
            'rows': 3,
            'placeholder': 'Optional description',
        }),
        label='Description'
    )
    system_roles = forms.MultipleChoiceField(
        required=False,
        choices=SYSTEM_ROLE_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'rounded border-dark-border bg-dark-bg text-dark-accent',
        }),
        label='System Roles'
    )

    def clean_name(self):
        import re
        name = self.cleaned_data.get('name', '').lower()
        if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$', name):
            raise forms.ValidationError(
                'Name must be DNS-compatible: lowercase letters, numbers, and hyphens only. '
                'Max 63 characters, no leading/trailing hyphens.'
            )
        if Group.objects.filter(name=name).exists():
            raise forms.ValidationError("A group named '{}' already exists. Choose a different name.".format(name))
        return name


class GroupEditForm(forms.Form):
    """Form for editing an existing group."""
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'input-field w-full',
            'rows': 3,
        }),
        label='Description'
    )
    status = forms.ChoiceField(
        choices=[('active', 'Active'), ('inactive', 'Inactive')],
        widget=forms.Select(attrs={
            'class': 'input-field w-full',
        }),
        label='Status'
    )
    system_roles = forms.MultipleChoiceField(
        required=False,
        choices=SYSTEM_ROLE_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'rounded border-dark-border bg-dark-bg text-dark-accent',
        }),
        label='System Roles'
    )


class GroupAddMemberForm(forms.Form):
    """Form for adding a user to a group."""
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(status='active'),
        widget=forms.Select(attrs={
            'class': 'input-field w-full',
        }),
        label='User'
    )

    def __init__(self, *args, group=None, **kwargs):
        super().__init__(*args, **kwargs)
        if group:
            # Exclude users already in the group
            existing_user_ids = GroupMembership.objects.filter(group=group).values_list('user_id', flat=True)
            self.fields['user'].queryset = User.objects.filter(status='active').exclude(id__in=existing_user_ids)


class ProjectCreateForm(forms.ModelForm):
    """Form for creating a new project."""

    class Meta:
        model = Project
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent',
                'placeholder': 'my-project',
                'pattern': '[a-z0-9][a-z0-9-]*[a-z0-9]|[a-z0-9]',
                'title': 'Lowercase letters, numbers, and hyphens only',
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent',
                'rows': 3,
                'placeholder': 'A brief description of this project',
            }),
        }

    def clean_name(self):
        name = self.cleaned_data['name'].lower()
        # DNS-compatible validation (RFC 1123 label format)
        if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$', name):
            raise forms.ValidationError(
                'Name must be DNS-compatible: lowercase letters, numbers, and hyphens only. '
                'Max 63 characters, no leading/trailing hyphens.'
            )
        if Project.objects.filter(name=name).exists():
            raise forms.ValidationError("A project named '{}' already exists. Choose a different name.".format(name))
        return name


class ProjectUpdateForm(forms.ModelForm):
    """Form for updating project settings."""

    class Meta:
        model = Project
        fields = ['description', 'status']
        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent',
                'rows': 3,
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent',
            }),
        }


class EnvironmentForm(forms.ModelForm):
    """Form for creating/editing environments."""

    class Meta:
        model = Environment
        fields = ['name', 'description', 'is_production', 'is_default', 'order']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent',
                'placeholder': 'e.g., dev, staging, production',
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent',
                'rows': 2,
            }),
            'is_production': forms.CheckboxInput(attrs={
                'class': 'rounded border-dark-border bg-dark-bg text-dark-accent focus:ring-dark-accent',
            }),
            'is_default': forms.CheckboxInput(attrs={
                'class': 'rounded border-dark-border bg-dark-bg text-dark-accent focus:ring-dark-accent',
            }),
            'order': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Name cannot be changed after creation
        if self.instance and self.instance.pk:
            self.fields['name'].disabled = True
            self.fields['name'].widget.attrs['class'] += ' cursor-not-allowed opacity-50'

    def clean_name(self):
        name = self.cleaned_data['name'].lower()
        # DNS-compatible validation (RFC 1123 label format)
        if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$', name):
            raise forms.ValidationError(
                'Name must be DNS-compatible: lowercase letters, numbers, and hyphens only. '
                'Max 63 characters, no leading/trailing hyphens.'
            )
        return name


# Project role choices for project membership
PROJECT_ROLE_CHOICES = [
    ('owner', 'Owner'),
    ('contributor', 'Contributor'),
    ('viewer', 'Viewer'),
]


class AddProjectMemberForm(forms.Form):
    """Form for adding a group to a project."""
    group = forms.ModelChoiceField(
        queryset=Group.objects.filter(status='active'),
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent',
        }),
        label='Group'
    )
    project_role = forms.ChoiceField(
        choices=PROJECT_ROLE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent',
        }),
        label='Role'
    )

    def __init__(self, *args, existing_group_ids=None, **kwargs):
        super().__init__(*args, **kwargs)
        if existing_group_ids:
            self.fields['group'].queryset = Group.objects.filter(
                status='active'
            ).exclude(id__in=existing_group_ids)


class AttachConnectionForm(forms.Form):
    """Form for attaching a connection to project or environment."""
    connection = forms.ModelChoiceField(
        queryset=IntegrationConnection.objects.none(),
        label='Connection',
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent',
        })
    )
    is_default = forms.BooleanField(
        required=False,
        label='Set as default',
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-dark-border bg-dark-bg text-dark-accent focus:ring-dark-accent',
        })
    )

    def __init__(self, *args, category=None, exclude_ids=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = IntegrationConnection.objects.filter(status='active')
        if category:
            # Filter by plugin category
            from plugins.base import registry
            plugin_names = [p.name for p in registry.all().values() if p.category == category]
            qs = qs.filter(plugin_name__in=plugin_names)
        if exclude_ids:
            qs = qs.exclude(id__in=exclude_ids)
        self.fields['connection'].queryset = qs


class ConnectionConfigUpdateForm(forms.Form):
    """Form for updating connection configuration (description + editable sensitive fields)."""
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent',
            'rows': 2,
            'placeholder': 'Optional description',
        }),
        label='Description'
    )

    def __init__(self, *args, connection=None, **kwargs):
        from plugins.base import registry
        self.connection = connection
        self.editable_fields = []
        super().__init__(*args, **kwargs)

        if connection:
            self.fields['description'].initial = connection.description

            # Dynamically add editable fields from plugin schema
            plugin = registry.get(connection.plugin_name)
            if plugin:
                schema = plugin.get_config_schema()
                config = connection.get_config()
                for field_name, field_info in schema.items():
                    if not field_info.get('editable'):
                        continue
                    is_sensitive = field_info.get('sensitive', False)
                    # Sensitive fields must be present in config; non-sensitive can be added anytime
                    if is_sensitive and field_name not in config:
                        continue
                    if is_sensitive:
                        # Sensitive field - use password input
                        self.fields[field_name] = forms.CharField(
                            required=False,
                            widget=forms.PasswordInput(attrs={
                                'class': 'w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent',
                                'placeholder': '••••••••',
                                'autocomplete': 'off',
                            }),
                            label=field_info.get('label', field_name)
                        )
                    else:
                        # Non-sensitive field - use text input with current value
                        self.fields[field_name] = forms.CharField(
                            required=False,
                            initial=config.get(field_name, ''),
                            widget=forms.TextInput(attrs={
                                'class': 'w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent',
                            }),
                            label=field_info.get('label', field_name)
                        )
                    self.editable_fields.append(field_name)


class SiteConfigurationForm(forms.ModelForm):
    """Form for site-wide configuration settings."""

    class Meta:
        model = SiteConfiguration
        fields = ['external_url']
        widgets = {
            'external_url': forms.URLInput(attrs={
                'class': 'w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent',
                'placeholder': 'https://devssp.example.com',
            }),
        }
        labels = {
            'external_url': 'External URL',
        }
        help_texts = {
            'external_url': 'Public URL where DevSSP is accessible. Required for OAuth callbacks and webhooks.',
        }

    def clean_external_url(self):
        url = self.cleaned_data.get('external_url', '').rstrip('/')
        return url
