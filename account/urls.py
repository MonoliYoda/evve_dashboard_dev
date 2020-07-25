from django.urls import path, include
from esi.views import sso_redirect
from eve_dashboard import settings
from . import views


urlpatterns = [
    path('login/', sso_redirect,
         {'scopes': settings.ESI_SSO_SCOPES, 'return_to': 'dashboard-index'}, name='dashboard-ssoredir'),
    path('logout/', views.logout_user, name='account-logout'),
    path('adduser/', views.add_user, name='account-adduser'),
]
