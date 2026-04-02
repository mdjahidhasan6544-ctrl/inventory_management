"""
Core Serializers — Users, Organizations, JWT Authentication.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.core.models import Organization

User = get_user_model()


# =============================================================================
# JWT
# =============================================================================


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Include user metadata in the JWT token claims."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["email"] = user.email
        token["role"] = user.role
        if user.organization:
            token["org_id"] = str(user.organization.id)
            token["org_name"] = user.organization.name
        return token


# =============================================================================
# Organization
# =============================================================================


class OrganizationSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "slug",
            "plan",
            "max_users",
            "max_warehouses",
            "is_active",
            "member_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "member_count"]

    def get_member_count(self, obj):
        return obj.members.count()


class OrganizationCreateSerializer(serializers.ModelSerializer):
    """Used during registration to create an org + owner user atomically."""

    class Meta:
        model = Organization
        fields = ["name", "slug"]


# =============================================================================
# User
# =============================================================================


class UserSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source="organization.name", read_only=True
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "role",
            "organization",
            "organization_name",
            "is_active",
            "date_joined",
        ]
        read_only_fields = [
            "id",
            "organization",
            "organization_name",
            "date_joined",
        ]


class UserCreateSerializer(serializers.ModelSerializer):
    """Admin-level user creation within an organization."""

    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "phone",
            "role",
        ]

    def create(self, validated_data):
        # Organization is injected by the view from request.organization
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


# =============================================================================
# Registration (public)
# =============================================================================


class RegistrationSerializer(serializers.Serializer):
    """
    Register a new organization and its owner user in one step.
    """

    # Organization fields
    org_name = serializers.CharField(max_length=255)
    org_slug = serializers.SlugField(max_length=100)

    # User fields
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    first_name = serializers.CharField(max_length=150, required=False, default="")
    last_name = serializers.CharField(max_length=150, required=False, default="")

    def validate_org_slug(self, value):
        if Organization.objects.filter(slug=value).exists():
            raise serializers.ValidationError(
                "An organization with this slug already exists."
            )
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def create(self, validated_data):
        from django.db import transaction

        with transaction.atomic():
            org = Organization.objects.create(
                name=validated_data["org_name"],
                slug=validated_data["org_slug"],
            )
            user = User.objects.create_user(
                username=validated_data["username"],
                email=validated_data["email"],
                password=validated_data["password"],
                first_name=validated_data.get("first_name", ""),
                last_name=validated_data.get("last_name", ""),
                organization=org,
                role=User.Role.OWNER,
            )
        return {"organization": org, "user": user}


class ChangePasswordSerializer(serializers.Serializer):
    """Change password for the authenticated user."""

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True, validators=[validate_password]
    )

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value
