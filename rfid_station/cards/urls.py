from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router for API endpoints
router = DefaultRouter()

# Template Views
urlpatterns = [
    # Web interfaces
    path('', views.home_view, name='home'),
    path('cashier/', views.cashier_view, name='cashier'),
    path('cashier-dashboard/', views.cashier_dashboard_view, name='cashier_dashboard'),
    path('passenger/', views.passenger_view, name='passenger'),
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('reports/', views.reports_view, name='reports'),
    path('lost-card-management/', views.lost_card_management_view, name='lost_card_management'),
    path('station-management/', views.station_management_view, name='station_management'),
    
    # API endpoints
    path('cards/purchase/', views.PurchaseCardView.as_view(), name='purchase-card'),
    path('cards/<str:uid>/reload/', views.ReloadCardView.as_view(), name='reload-card'),
    path('cards/<str:uid>/ride/', views.RideView.as_view(), name='ride-charge'),
    path('cards/<str:uid>/status/', views.CardStatusView.as_view(), name='update-card-status'),
    path('cards/<str:uid>/fare-category/', views.UpdateFareCategoryView.as_view(), name='update-fare-category'),
    path('cards/<str:uid>/update/', views.UpdateCardView.as_view(), name='update-card'),
    path('cards/<str:uid>/', views.CardDetailView.as_view(), name='card-detail'),
    path('cards/<str:uid>/balance/', views.card_balance, name='card-balance'),
    path('public/cards/<str:uid>/balance/', views.public_card_balance, name='public-card-balance'),
    path('public/cards/<str:uid>/transactions/', views.public_card_transactions, name='public-card-transactions'),
    path('public/cards/<str:uid>/ride/', views.public_ride_charge, name='public-ride-charge'),
    path('clear-passenger-session/', views.clear_passenger_session, name='clear-passenger-session'),
    path('cards/', views.CardListView.as_view(), name='card-list'),
    path('recent-transactions/', views.recent_transactions, name='recent-transactions'),
    
    # Reports
    path('reports/data/', views.ReportsView.as_view(), name='reports-api'),
    
    # System
    path('health/', views.system_health, name='system-health'),
]
