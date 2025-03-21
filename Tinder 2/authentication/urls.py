from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('profile/setup/', views.profile_setup, name='profile_setup'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),]