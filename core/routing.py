from django.urls import path

from core.consumers import ServiceConsumer, StepsRepoConsumer

websocket_urlpatterns = [
    path("ws/services/<int:service_id>/", ServiceConsumer.as_asgi()),
    path("ws/repos/<int:repo_id>/", StepsRepoConsumer.as_asgi()),
]
