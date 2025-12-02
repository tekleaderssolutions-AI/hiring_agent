from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('', include('hiring_app.urls')),
    path('favicon.ico', RedirectView.as_view(url='/static/favicon.ico')),
]
