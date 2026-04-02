"""
Unit tests for core models — Organization and User.
"""

import pytest

from apps.core.models import Organization, User


@pytest.mark.django_db
class TestOrganization:
    def test_create_organization(self):
        org = Organization.objects.create(name="Acme Corp", slug="acme-corp")
        assert org.name == "Acme Corp"
        assert org.slug == "acme-corp"
        assert org.is_active is True
        assert org.plan == "free"
        assert org.max_users == 5
        assert org.max_warehouses == 2

    def test_organization_str(self):
        org = Organization.objects.create(name="Acme Corp", slug="acme-corp")
        assert str(org) == "Acme Corp"

    def test_organization_uuid_pk(self):
        org = Organization.objects.create(name="Acme Corp", slug="acme-corp")
        assert org.id is not None
        assert len(str(org.id)) == 36  # UUID format

    def test_unique_slug(self):
        Organization.objects.create(name="Acme Corp", slug="acme-corp")
        with pytest.raises(Exception):
            Organization.objects.create(name="Acme Corp 2", slug="acme-corp")

    def test_organization_timestamps(self):
        org = Organization.objects.create(name="Acme Corp", slug="acme-corp")
        assert org.created_at is not None
        assert org.updated_at is not None


@pytest.mark.django_db
class TestUser:
    def test_create_user(self, organization):
        user = User.objects.create_user(
            username="testuser",
            email="test@test.com",
            password="SecurePass123!",
            organization=organization,
            role=User.Role.MANAGER,
        )
        assert user.username == "testuser"
        assert user.organization == organization
        assert user.role == User.Role.MANAGER
        assert user.check_password("SecurePass123!")

    def test_user_str(self, organization):
        user = User.objects.create_user(
            username="testuser",
            email="test@test.com",
            password="SecurePass123!",
            organization=organization,
            first_name="Test",
            last_name="User",
        )
        assert "Test User" in str(user)
        assert str(organization) in str(user)

    def test_user_default_role(self, organization):
        user = User.objects.create_user(
            username="newuser",
            email="new@test.com",
            password="SecurePass123!",
            organization=organization,
        )
        assert user.role == User.Role.VIEWER

    def test_is_org_admin_owner(self, owner_user):
        assert owner_user.is_org_admin is True

    def test_is_org_admin_admin(self, admin_user):
        assert admin_user.is_org_admin is True

    def test_is_org_admin_manager(self, manager_user):
        assert manager_user.is_org_admin is False

    def test_is_org_admin_viewer(self, viewer_user):
        assert viewer_user.is_org_admin is False

    def test_user_uuid_pk(self, organization):
        user = User.objects.create_user(
            username="uuiduser",
            email="uuid@test.com",
            password="SecurePass123!",
            organization=organization,
        )
        assert user.id is not None
        assert len(str(user.id)) == 36
