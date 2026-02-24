from django.urls import path

from core.consumers import ServiceConsumer

websocket_urlpatterns = [
    path("ws/services/<int:service_id>/", ServiceConsumer.as_asgi()),
]
