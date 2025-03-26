from django.urls import path
from . import views

urlpatterns = [
    path('', views.ChatListView.as_view(), name='chat_list'),
    path('<int:match_id>/', views.chat_view, name='chat'),
]