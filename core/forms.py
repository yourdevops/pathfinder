from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User, Group, GroupMembership


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
