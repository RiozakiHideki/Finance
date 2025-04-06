"""
URL configuration for Finance project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from django.contrib import admin
from django.views.generic import TemplateView

from app import views
from django.contrib.auth import views as auth_views
from rest_framework.routers import DefaultRouter
from app.views import UserProfileViewSet, FinanceDataViewSet, confirm_email

router = DefaultRouter()
router.register(r'user-profile', UserProfileViewSet, basename='user-profile')
router.register(r'finance-data', FinanceDataViewSet, basename='finance-data')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('try_app', views.try_app, name='try_app'),
    path('contacts', views.contacts, name='contacts'),
    path('add_data/', views.add_data, name='add_data'),
    path('delete_transaction/<int:index>/', views.delete_transaction, name='delete_transaction'),
    path('edit_transaction/<int:index>/', views.edit_transaction, name='edit_transaction'),
    path('finances/<int:user_id>/', views.finances, name='finances'),
    path('add_data_user/<int:user_id>/', views.add_data_user, name='add_data_user'),
    path('edit_transaction_user/<int:user_id>/<int:transaction_id>/', views.edit_transaction_user, name='edit_transaction_user'),
    path('delete_transaction_user/<int:user_id>/<int:transaction_id>/', views.delete_transaction_user, name='delete_transaction_user'),
    path('add_category_user/<int:user_id>/', views.add_category_user, name='add_category_user'),
    path('add_budget_user/<int:user_id>/', views.add_budget_user, name='add_budget_user'),
    path('delete_budget_user/<int:user_id>/<str:budget_name>/', views.delete_budget_user, name='delete_budget_user'),
    path('chart_user/<int:user_id>/', views.chart_user, name='chart_user'),
    path('download_data_user/<int:user_id>/', views.download_data_user, name='download_data_user'),
    path('api/', include(router.urls)),
    path('confirm-email/<str:token>/', confirm_email, name='confirm_email'),
    path('registration-pending/', TemplateView.as_view(
        template_name='app/registration_pending.html'), name='registration_pending'),
]
