from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


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
