"""
Tests for JWT authentication flows — login, register, refresh, logout, profile.
"""

import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestRegistration:
    url = reverse("auth:register")

    def test_register_success(self, api_client):
        data = {
            "org_name": "New Corp",
            "org_slug": "new-corp",
            "username": "newuser",
            "email": "new@newcorp.com",
            "password": "StrongP@ss1234",
            "first_name": "New",
            "last_name": "User",
        }
        response = api_client.post(self.url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert "tokens" in response.data
        assert "access" in response.data["tokens"]
        assert "refresh" in response.data["tokens"]
        assert response.data["user"]["username"] == "newuser"
        assert response.data["organization"]["name"] == "New Corp"

    def test_register_duplicate_slug(self, api_client, organization):
        data = {
            "org_name": "Duplicate",
            "org_slug": organization.slug,
            "username": "dupuser",
            "email": "dup@test.com",
            "password": "StrongP@ss1234",
        }
        response = api_client.post(self.url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_duplicate_username(self, api_client, owner_user):
        data = {
            "org_name": "Another Corp",
            "org_slug": "another-corp",
            "username": owner_user.username,
            "email": "another@test.com",
            "password": "StrongP@ss1234",
        }
        response = api_client.post(self.url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_weak_password(self, api_client):
        data = {
            "org_name": "Weak Corp",
            "org_slug": "weak-corp",
            "username": "weakuser",
            "email": "weak@test.com",
            "password": "123",
        }
        response = api_client.post(self.url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLogin:
    url = reverse("auth:login")

    def test_login_success(self, api_client, owner_user):
        response = api_client.post(
            self.url,
            {"username": "owner", "password": "SecurePass123!"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_wrong_password(self, api_client, owner_user):
        response = api_client.post(
            self.url,
            {"username": "owner", "password": "wrong"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, api_client):
        response = api_client.post(
            self.url,
            {"username": "nobody", "password": "whatever"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestTokenRefresh:
    login_url = reverse("auth:login")
    refresh_url = reverse("auth:token-refresh")

    def test_refresh_success(self, api_client, owner_user):
        login_resp = api_client.post(
            self.login_url,
            {"username": "owner", "password": "SecurePass123!"},
        )
        refresh_token = login_resp.data["refresh"]
        response = api_client.post(self.refresh_url, {"refresh": refresh_token})
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_refresh_invalid_token(self, api_client):
        response = api_client.post(self.refresh_url, {"refresh": "invalid"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestLogout:
    login_url = reverse("auth:login")
    logout_url = reverse("auth:logout")

    def test_logout_success(self, api_client, owner_user):
        login_resp = api_client.post(
            self.login_url,
            {"username": "owner", "password": "SecurePass123!"},
        )
        api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_resp.data['access']}"
        )
        response = api_client.post(
            self.logout_url,
            {"refresh": login_resp.data["refresh"]},
        )
        assert response.status_code == status.HTTP_205_RESET_CONTENT

    def test_logout_unauthenticated(self, api_client):
        response = api_client.post(self.logout_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestMeEndpoint:
    url = reverse("auth:me")

    def test_get_profile(self, authenticated_client, owner_user):
        response = authenticated_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == owner_user.username
        assert response.data["email"] == owner_user.email

    def test_update_profile(self, authenticated_client):
        response = authenticated_client.patch(
            self.url, {"first_name": "Updated"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["first_name"] == "Updated"

    def test_unauthenticated(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestChangePassword:
    url = reverse("auth:change-password")

    def test_change_password_success(self, authenticated_client):
        response = authenticated_client.put(
            self.url,
            {
                "old_password": "SecurePass123!",
                "new_password": "NewSecureP@ss456",
            },
        )
        assert response.status_code == status.HTTP_200_OK

    def test_change_password_wrong_old(self, authenticated_client):
        response = authenticated_client.put(
            self.url,
            {
                "old_password": "wrong",
                "new_password": "NewSecureP@ss456",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
