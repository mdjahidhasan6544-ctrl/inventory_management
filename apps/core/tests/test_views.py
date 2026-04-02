"""
Tests for core API endpoints — Organization and User management.
"""

import pytest
from django.urls import reverse
from rest_framework import status

from apps.core.models import User


@pytest.mark.django_db
class TestOrganizationEndpoint:
    url = reverse("core:organization-detail")

    def test_get_organization(self, authenticated_client, organization):
        response = authenticated_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == organization.name

    def test_update_organization_as_owner(self, authenticated_client):
        response = authenticated_client.patch(self.url, {"name": "Updated Corp"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Updated Corp"

    def test_update_organization_as_viewer(self, viewer_client):
        response = viewer_client.patch(self.url, {"name": "Hacked"})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserEndpoints:
    list_url = reverse("core:user-list")

    def detail_url(self, user_id):
        return reverse("core:user-detail", kwargs={"pk": user_id})

    def test_list_users(self, authenticated_client, owner_user):
        response = authenticated_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1

    def test_create_user_as_owner(self, authenticated_client):
        data = {
            "username": "newteammate",
            "email": "new@testcorp.com",
            "password": "TeamMateP@ss1",
            "first_name": "New",
            "last_name": "Teammate",
            "role": "manager",
        }
        response = authenticated_client.post(self.list_url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["username"] == "newteammate"
        assert response.data["role"] == "manager"

    def test_create_user_as_viewer_forbidden(self, viewer_client):
        data = {
            "username": "hacker",
            "email": "hacker@test.com",
            "password": "HackP@ss1234",
            "role": "admin",
        }
        response = viewer_client.post(self.list_url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_user_as_manager_forbidden(self, manager_client):
        data = {
            "username": "sneaky",
            "email": "sneaky@test.com",
            "password": "SneakyP@ss1234",
            "role": "viewer",
        }
        response = manager_client.post(self.list_url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_viewer_can_list_users(self, viewer_client):
        response = viewer_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK

    def test_tenant_isolation_users(
        self, other_org_client, owner_user
    ):
        """User from another org should NOT see users from the first org."""
        response = other_org_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        usernames = [u["username"] for u in response.data["results"]]
        assert owner_user.username not in usernames

    def test_active_users_endpoint(self, authenticated_client):
        url = reverse("core:user-active")
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
