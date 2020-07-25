from django.urls import path, include
from esi.views import sso_redirect
from eve_dashboard import settings
from . import views


urlpatterns = [
    path('', views.index, name='dashboard-index'),
    path('index/', views.index, name='dashboard-index'),
    path('contracts/', views.contracts, name='dashboard-contracts'),
    path('calendar/', views.calendar, name='dashboard-calendar'),
    path('market/', views.market, name='dashboard-market'),
    path('ajax/gettimers', views.ajax_get_timers, name='dashboard-contracts'),
    path('ajax/newtimer', views.ajax_new_timer, name='dashboard-contracts'),
    path('ajax/removetimer', views.ajax_remove_timer, name='dashboard-contracts'),
    path('ajax/getcorpcontracts', views.ajax_get_corp_contracts, name='dashboard-contracts'),
    path('ajax/getplanets', views.ajax_get_planets, name='dashboard-contracts'),
    path('ajax/getusercontracts', views.ajax_get_user_contracts, name='dashboard-contracts'),
    path('ajax/getwalletbalance', views.ajax_get_walletbalance, name='dashboard-contracts'),
    path('ajax/getactiveorders', views.ajax_get_activeorders, name='dashboard-contracts'),
    path('ajax/get24htransactions', views.ajax_get_24htransactions, name='dashboard-contracts'),
    path('ajax/getwalletjournal', views.ajax_get_walletjournal, name='dashboard-contracts'),
    path('ajax/event_count', views.cal_even_count, name='dashboard-contracts'),
    path('ajax/contract_count', views.contract_count, name='dashboard-contracts'),
    path('ajax/get_market_active', views.get_market_active, name='dashboard-contracts'),
    path('ajax/get_market_history', views.get_market_history, name='dashboard-contracts'),
]
