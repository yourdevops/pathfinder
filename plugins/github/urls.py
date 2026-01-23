"""GitHub plugin URL configuration."""
from django.urls import path
from . import views

app_name = 'github'

urlpatterns = [
    path('create/', views.GitHubConnectionWizard.as_view(), name='create'),
]
