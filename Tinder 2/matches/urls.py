from django.urls import path
from . import views

urlpatterns = [
    path('', views.MatchListView.as_view(), name='match_list'),
    path('like/profile/<int:profile_id>/', views.create_like, name='like_profile'),
    path('like/request/<int:request_id>/', views.create_like, name='like_request'),
]