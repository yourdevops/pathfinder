from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import login

from ..forms import UnlockForm, AdminRegistrationForm
from ..utils import verify_unlock_token, complete_setup
from ..models import User, Group, GroupMembership


class UnlockView(View):
    """Handle unlock token entry."""
    template_name = 'core/setup/unlock.html'

    def get(self, request):
        return render(request, self.template_name, {'form': UnlockForm()})

    def post(self, request):
        form = UnlockForm(request.POST)
        if form.is_valid():
            if verify_unlock_token(form.cleaned_data['token']):
                # Store verified state in session for registration step
                request.session['unlock_verified'] = True
                return redirect('setup:register')
            form.add_error('token', 'Invalid unlock token.')
        return render(request, self.template_name, {'form': form})


class AdminRegistrationView(View):
    """Handle first admin account creation."""
    template_name = 'core/setup/register.html'

    def dispatch(self, request, *args, **kwargs):
        # Must have verified unlock token first
        if not request.session.get('unlock_verified'):
            return redirect('setup:unlock')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, self.template_name, {'form': AdminRegistrationForm()})

    def post(self, request):
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
            return redirect('users:list')

        return render(request, self.template_name, {'form': form})
