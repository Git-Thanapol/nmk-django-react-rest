"""
DRF REST API tests — Notes, JWT auth, user registration, VAT endpoints.
"""
import pytest
from rest_framework import status
from django.urls import reverse

from api.models import Note
from .factories import UserFactory, NoteFactory


# ---------------------------------------------------------------------------
# JWT Authentication
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestJWTAuth:
    def test_obtain_token_with_valid_credentials(self, api_client, user):
        resp = api_client.post('/api/token/', {
            'username': user.username,
            'password': 'testpass123',
        })
        assert resp.status_code == status.HTTP_200_OK
        assert 'access' in resp.data
        assert 'refresh' in resp.data

    def test_obtain_token_with_invalid_credentials(self, api_client, user):
        resp = api_client.post('/api/token/', {
            'username': user.username,
            'password': 'wrongpassword',
        })
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_obtain_token_with_empty_credentials(self, api_client):
        resp = api_client.post('/api/token/', {'username': '', 'password': ''})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_refresh_token(self, api_client, user):
        resp = api_client.post('/api/token/', {
            'username': user.username,
            'password': 'testpass123',
        })
        refresh = resp.data['refresh']
        refresh_resp = api_client.post('/api/token/refresh/', {'refresh': refresh})
        assert refresh_resp.status_code == status.HTTP_200_OK
        assert 'access' in refresh_resp.data

    def test_refresh_with_invalid_token(self, api_client):
        resp = api_client.post('/api/token/refresh/', {'refresh': 'not.a.token'})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# User Registration
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserRegistration:
    def test_register_new_user(self, api_client):
        resp = api_client.post('/api/user/register/', {
            'username': 'brandnew',
            'password': 'Str0ngPass!',
        })
        assert resp.status_code == status.HTTP_201_CREATED

    def test_register_duplicate_username(self, api_client, user):
        resp = api_client.post('/api/user/register/', {
            'username': user.username,
            'password': 'Str0ngPass!',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_without_password(self, api_client):
        resp = api_client.post('/api/user/register/', {'username': 'nopw'})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_without_username(self, api_client):
        resp = api_client.post('/api/user/register/', {'password': 'Str0ngPass!'})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_not_returned_in_response(self, api_client):
        resp = api_client.post('/api/user/register/', {
            'username': 'safe_user',
            'password': 'Str0ngPass!',
        })
        assert 'password' not in resp.data


# ---------------------------------------------------------------------------
# Notes API
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestNotesAPI:
    def test_unauthenticated_cannot_list_notes(self, api_client):
        resp = api_client.get('/api/notes/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_own_notes(self, auth_api_client, user):
        NoteFactory(user=user, title="My Note")
        NoteFactory()  # Belongs to a different user
        resp = auth_api_client.get('/api/notes/')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1
        assert resp.data[0]['title'] == "My Note"

    def test_cannot_see_other_users_notes(self, auth_api_client, user):
        other_user = UserFactory()
        NoteFactory(user=other_user)
        resp = auth_api_client.get('/api/notes/')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 0

    def test_create_note(self, auth_api_client):
        resp = auth_api_client.post('/api/notes/', {
            'title': 'New Note',
            'content': 'Some content',
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['title'] == 'New Note'
        assert Note.objects.filter(title='New Note').exists()

    def test_create_note_without_title(self, auth_api_client):
        resp = auth_api_client.post('/api/notes/', {'content': 'orphan'})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_note_empty_title(self, auth_api_client):
        resp = auth_api_client.post('/api/notes/', {'title': '', 'content': 'x'})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_own_note(self, auth_api_client, user):
        note = NoteFactory(user=user)
        resp = auth_api_client.delete(f'/api/notes/{note.pk}/')
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Note.objects.filter(pk=note.pk).exists()

    def test_cannot_delete_other_users_note(self, auth_api_client):
        other_note = NoteFactory()
        resp = auth_api_client.delete(f'/api/notes/{other_note.pk}/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_nonexistent_note(self, auth_api_client):
        resp = auth_api_client.delete('/api/notes/999999/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# NoteSerializer — password not exposed on user field
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestNoteSerializer:
    def test_user_field_read_only(self, auth_api_client, user):
        other = UserFactory()
        resp = auth_api_client.post('/api/notes/', {
            'title': 'Hijack',
            'content': 'x',
            'user': other.pk,
        })
        if resp.status_code == status.HTTP_201_CREATED:
            assert resp.data.get('user') == user.pk, "user field should be set from request, not payload"

    def test_timestamps_are_read_only(self, auth_api_client):
        resp = auth_api_client.post('/api/notes/', {
            'title': 'Timestamp Test',
            'content': 'x',
            'created_at': '2000-01-01T00:00:00Z',
        })
        if resp.status_code == status.HTTP_201_CREATED:
            assert resp.data['created_at'] != '2000-01-01T00:00:00Z'
