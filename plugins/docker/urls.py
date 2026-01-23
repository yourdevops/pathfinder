"""Docker plugin URL configuration."""
from django.urls import path
from . import views

app_name = 'docker'

urlpatterns = [
    path('create/', views.DockerConnectionCreateView.as_view(), name='create'),
]
