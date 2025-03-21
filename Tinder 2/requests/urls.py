from django.urls import path
from . import views

urlpatterns = [
    path('', views.RequestListView.as_view(), name='request_list'),
    path('<int:pk>/', views.RequestDetailView.as_view(), name='request_detail'),
    path('new/', views.CreateRequestView.as_view(), name='create_request'),
    path('<int:pk>/edit/', views.UpdateRequestView.as_view(), name='update_request'),
    path('<int:pk>/status/<str:status>/', views.change_request_status, name='change_request_status'),
]