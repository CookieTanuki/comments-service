from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.users.serializers import (
    CustomTokenObtainPairSerializer,
    UserRegistrationSerializer,
)


@extend_schema_view(
    post=extend_schema(
        tags=["Auth"],
        summary="Obtain JWT token pair",
        description="Authenticate an existing user and return JWT access and refresh tokens.",
    ),
)
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


@extend_schema_view(
    post=extend_schema(
        tags=["Auth"],
        summary="Register a new user",
        description="Create a new user account with unique username and email.",
    ),
)
class UserRegistrationView(CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
