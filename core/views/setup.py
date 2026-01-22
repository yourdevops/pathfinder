from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import login
from django.urls import reverse, NoReverseMatch

from ..forms import UnlockForm, AdminRegistrationForm
from ..utils import verify_unlock_token, complete_setup
from ..models import User, Group, GroupMembership


class UnlockView(View):
    """Handle unlock token entry and admin account creation in single-page flow."""
    template_name = 'core/setup/unlock.html'

    def get(self, request):
        # Check if unlock already verified - show registration form
        if request.session.get('unlock_verified'):
            return render(request, self.template_name, {
                'unlock_verified': True,
                'form': AdminRegistrationForm(),
            })
        # Show unlock form
        return render(request, self.template_name, {
            'unlock_verified': False,
            'form': UnlockForm(),
        })

    def post(self, request):
        # Check if this is a registration submission (unlock already verified)
        if request.session.get('unlock_verified'):
            return self._handle_registration(request)
        # Otherwise handle unlock token validation
        return self._handle_unlock(request)

    def _handle_unlock(self, request):
        """Validate unlock token and transition to registration form."""
        form = UnlockForm(request.POST)
        if form.is_valid():
            if verify_unlock_token(form.cleaned_data['token']):
                # Store verified state in session - stay on same page
                request.session['unlock_verified'] = True
                return render(request, self.template_name, {
                    'unlock_verified': True,
                    'form': AdminRegistrationForm(),
                })
            form.add_error('token', 'Invalid unlock token.')
        return render(request, self.template_name, {
            'unlock_verified': False,
            'form': form,
        })

    def _handle_registration(self, request):
        """Create admin account after unlock verification."""
        form = AdminRegistrationForm(request.POST)
        if form.is_valid():
            # Create user
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                status='active',
                source='local',
            )

            # Create admins group with admin SystemRole
            admins_group, _ = Group.objects.get_or_create(
                name='admins',
                defaults={
                    'description': 'System administrators with full access',
                    'system_roles': ['admin'],
                    'status': 'active',
                    'source': 'local',
                }
            )

            # Add user to admins group
            GroupMembership.objects.create(group=admins_group, user=user)

            # Complete setup (delete token)
            complete_setup()

            # Clear unlock_verified from session
            if 'unlock_verified' in request.session:
                del request.session['unlock_verified']

            # Log in user
            login(request, user)

            # Redirect to user management per requirements
            # Use try/except since users:list may not exist until Plan 04
            try:
                return redirect('users:list')
            except NoReverseMatch:
                # Fallback to hardcoded path when users app not yet created
                return redirect('/users/')

        return render(request, self.template_name, {
            'unlock_verified': True,
            'form': form,
        })
