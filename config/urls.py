from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("appointments/", include("apps.appointments.urls")),
    path("patients/", include("apps.patients.urls")),
    path("doctors/", include("apps.doctors.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)