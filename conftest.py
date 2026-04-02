"""conftest.py — shared test fixtures for the entire project."""

import pytest
from rest_framework.test import APIClient

from apps.core.models import Organization, User


@pytest.fixture
def api_client():
    """Unauthenticated DRF test client."""
    return APIClient()


@pytest.fixture
def organization(db):
    """A default test organization."""
    return Organization.objects.create(
        name="Test Corp",
        slug="test-corp",
        plan="professional",
        max_users=20,
        max_warehouses=5,
    )


@pytest.fixture
def other_organization(db):
    """A second organization for tenant-isolation tests."""
    return Organization.objects.create(
        name="Other Corp",
        slug="other-corp",
        plan="starter",
    )


@pytest.fixture
def owner_user(db, organization):
    """Owner-role user in the default organization."""
    user = User.objects.create_user(
        username="owner",
        email="owner@testcorp.com",
        password="SecurePass123!",
        organization=organization,
        role=User.Role.OWNER,
        first_name="Owner",
        last_name="User",
    )
    return user


@pytest.fixture
def admin_user(db, organization):
    """Admin-role user in the default organization."""
    user = User.objects.create_user(
        username="admin",
        email="admin@testcorp.com",
        password="SecurePass123!",
        organization=organization,
        role=User.Role.ADMIN,
    )
    return user


@pytest.fixture
def manager_user(db, organization):
    """Manager-role user in the default organization."""
    user = User.objects.create_user(
        username="manager",
        email="manager@testcorp.com",
        password="SecurePass123!",
        organization=organization,
        role=User.Role.MANAGER,
    )
    return user


@pytest.fixture
def viewer_user(db, organization):
    """Viewer-role user in the default organization."""
    user = User.objects.create_user(
        username="viewer",
        email="viewer@testcorp.com",
        password="SecurePass123!",
        organization=organization,
        role=User.Role.VIEWER,
    )
    return user


@pytest.fixture
def other_org_user(db, other_organization):
    """User in the OTHER organization for isolation tests."""
    return User.objects.create_user(
        username="other_user",
        email="other@othercorp.com",
        password="SecurePass123!",
        organization=other_organization,
        role=User.Role.OWNER,
    )


@pytest.fixture
def authenticated_client(owner_user):
    """API client authenticated as the owner user (JWT)."""
    client = APIClient()
    client.force_authenticate(user=owner_user)
    return client


@pytest.fixture
def manager_client(manager_user):
    """API client authenticated as a manager."""
    client = APIClient()
    client.force_authenticate(user=manager_user)
    return client


@pytest.fixture
def viewer_client(viewer_user):
    """API client authenticated as a viewer (read-only)."""
    client = APIClient()
    client.force_authenticate(user=viewer_user)
    return client


@pytest.fixture
def other_org_client(other_org_user):
    """API client authenticated as a user in a DIFFERENT organization."""
    client = APIClient()
    client.force_authenticate(user=other_org_user)
    return client

