from django.urls import path
from . import views

urlpatterns = [
    path('overview/', views.dashboard_overview, name='dashboard-overview'),
    path('monthly-sales/', views.monthly_sales, name='monthly-sales'),
    path('daily-sales/', views.daily_sales, name='daily-sales'),
    path('product-insights/', views.product_insights, name='product-insights'),
    path('revenue-breakdown/', views.revenue_breakdown, name='revenue-breakdown'),
    path('sales-report/', views.sales_report, name='sales-report'),
    path('inventory-report/', views.inventory_report, name='inventory-report'),
]
