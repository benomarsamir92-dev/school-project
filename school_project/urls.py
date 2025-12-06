from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseNotFound

# Custom view for missing media files
def missing_media(request, path):
    return HttpResponseNotFound("Media file not found")

urlpatterns = i18n_patterns(
    path('admin/', admin.site.urls),
    path('', include('school_management.urls')),
    prefix_default_language=False,
)

urlpatterns += [
    path('i18n/', include('django.conf.urls.i18n')),
]

# Serve media files in development, but don't crash on missing files
if settings.DEBUG:
    from django.views.static import serve
    urlpatterns += [
        path('media/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
else:
    # In production, return 404 for missing files instead of crashing
    urlpatterns += [
        path('media/<path:path>', missing_media),
    ]
