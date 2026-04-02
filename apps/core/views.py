"""
Core Views — Authentication, Registration, User & Organization management.
"""

from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.models import Organization
from apps.core.permissions import IsOrgAdmin, IsOrganizationMember
from apps.core.serializers import (
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    OrganizationSerializer,
    RegistrationSerializer,
    UserCreateSerializer,
    UserSerializer,
)

User = get_user_model()


# =============================================================================
# Authentication Views
# =============================================================================


class CustomTokenObtainPairView(TokenObtainPairView):
    """POST /api/v1/auth/login/ — obtain JWT access + refresh tokens."""

    serializer_class = CustomTokenObtainPairSerializer


class CustomTokenRefreshView(TokenRefreshView):
    """POST /api/v1/auth/refresh/ — refresh an access token."""

    pass


class RegisterView(generics.CreateAPIView):
    """
    POST /api/v1/auth/register/

    Create a new organization and its owner user atomically.
    Returns JWT tokens so the user is logged in immediately.
    """

    serializer_class = RegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        user = result["user"]
        org = result["organization"]

        # Generate JWT tokens for immediate login
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "user": UserSerializer(user).data,
                "organization": OrganizationSerializer(org).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LogoutView(generics.GenericAPIView):
    """
    POST /api/v1/auth/logout/

    Blacklist the refresh token to log the user out.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response(
                {"detail": "Successfully logged out."},
                status=status.HTTP_205_RESET_CONTENT,
            )
        except Exception:
            return Response(
                {"detail": "Invalid or expired refresh token."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class MeView(generics.RetrieveUpdateAPIView):
    """
    GET/PATCH /api/v1/auth/me/

    View or update the currently authenticated user's profile.
    """

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(generics.UpdateAPIView):
    """
    PUT /api/v1/auth/change-password/

    Change the current user's password.
    """

    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response(
            {"detail": "Password updated successfully."},
            status=status.HTTP_200_OK,
        )


# =============================================================================
# Organization Views
# =============================================================================


class OrganizationDetailView(generics.RetrieveUpdateAPIView):
    """
    GET/PATCH /api/v1/core/organization/

    View or update the current user's organization.
    Only org admins can update.
    """

    serializer_class = OrganizationSerializer
    permission_classes = [IsOrganizationMember]

    def get_object(self):
        return self.request.organization

    def get_permissions(self):
        if self.request.method in ("PATCH", "PUT"):
            return [IsOrganizationMember(), IsOrgAdmin()]
        return [IsOrganizationMember()]


# =============================================================================
# User Management Views
# =============================================================================


class UserViewSet(viewsets.ModelViewSet):
    """
    /api/v1/core/users/

    CRUD for users within the current organization.
    Only org admins can create, update, or deactivate users.
    Viewers and managers can list/retrieve.
    """

    permission_classes = [IsOrganizationMember]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def get_queryset(self):
        return User.objects.filter(
            organization=self.request.organization
        ).select_related("organization")

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsOrganizationMember(), IsOrgAdmin()]
        return [IsOrganizationMember()]

    def perform_create(self, serializer):
        serializer.save(organization=self.request.organization)

    def perform_destroy(self, instance):
        """Soft-delete: deactivate instead of removing."""
        if instance == self.request.user:
            return Response(
                {"detail": "You cannot deactivate your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.is_active = False
        instance.save(update_fields=["is_active"])

    @action(detail=False, methods=["get"])
    def active(self, request):
        """GET /api/v1/core/users/active/ — list only active users."""
        qs = self.get_queryset().filter(is_active=True)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
