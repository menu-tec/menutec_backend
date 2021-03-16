from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from .views import webhook

urlpatterns = [
    path('<str:secret>', csrf_exempt(webhook))
]