from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/profiles/', permanent=True)),
    path('', include('authentication.urls')),
    path('profiles/', include('profiles.urls')),
    path('requests/', include('requests.urls')),
    path('matches/', include('matches.urls')),
    path('chat/', include('chat.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)