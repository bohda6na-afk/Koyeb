from django.urls import path
from . import views

app_name = 'detection'

urlpatterns = [
    # Review views
    # path('review/', views.review_view, name='review'),
    
    # Marker-level processing
    path('marker/<int:marker_id>/process/', views.process_marker_api, name='process_marker'),
    path('marker/<int:marker_id>/results/', views.marker_detection_results, name='marker_results'),
    
    # File-level processing
    path('file/<int:file_id>/process/', views.process_single_file, name='process_file'),
    
    # API endpoints
    path('api/models/', views.available_models, name='api_models'),
]
