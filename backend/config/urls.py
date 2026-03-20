"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.views import CustomTokenObtainPairView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('comments/', include('apps.comments.urls')),
    path('captcha/', include('captcha.urls')),

    # Attachments
    path('attachments/', include('apps.attachments.urls')),

    # JWT
    path('api/token/', CustomTokenObtainPairView.as_view(),),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

if not settings.USE_S3:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
