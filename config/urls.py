
from django.contrib import admin
from django.urls import include, path,inlcude

urlpatterns = [
    path('admin/', admin.site.urls),
    path('appointments/', include('apps.appointments.urls')),
    path('patients/', include('apps.patients.urls')),
    path('doctors/', include('apps.doctors.urls')),
]
