from django.urls import path
from . import views

urlpatterns = [
    path('', views.ProfileListView.as_view(), name='profile_list'),
    path('<int:pk>/', views.ProfileDetailView.as_view(), name='profile_detail'),
    path('swipe/', views.view_next_profile, name='swipe_profiles'),]