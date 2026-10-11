import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from api.models import BugReport, BugReportAttachment
from .factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _no_ssl_redirect(settings):
    settings.SECURE_SSL_REDIRECT = False
    settings.ALLOWED_HOSTS = ['testserver']


@pytest.fixture
def logged_in(client, user):
    client.force_login(user)
    return client


def _upload(client, name, content=b'a,b\n1,2\n'):
    return client.post(
        reverse('bug_report_upload_file'),
        {'file': SimpleUploadedFile(name, content)},
    )


def test_upload_csv_ok(logged_in):
    resp = _upload(logged_in, 'shopee_order.csv')
    assert resp.status_code == 200
    assert resp.json()['name'] == 'shopee_order.csv'
    assert BugReportAttachment.objects.count() == 1


def test_upload_rejects_unknown_extension(logged_in):
    resp = _upload(logged_in, 'evil.exe')
    assert resp.status_code == 400
    assert BugReportAttachment.objects.count() == 0


def test_upload_rejects_too_large(logged_in, monkeypatch):
    monkeypatch.setattr(BugReportAttachment, 'MAX_SIZE', 5)
    resp = _upload(logged_in, 'big.csv', b'x' * 10)
    assert resp.status_code == 400


def test_upload_requires_login(client):
    resp = _upload(client, 'a.csv')
    assert resp.status_code == 302


def _submit_with_attachment(client):
    att_id = _upload(client, 'tiktok.xlsx').json()['id']
    resp = client.post(
        reverse('bug_report_submit'),
        {'title': 't', 'summary': 's', 'attachment_ids': [att_id]},
        content_type='application/json',
    )
    assert resp.status_code == 200
    return BugReportAttachment.objects.get(pk=att_id)


def test_submit_links_attachment(logged_in):
    att = _submit_with_attachment(logged_in)
    assert att.bug_report is not None


def test_download_owner_ok(logged_in):
    att = _submit_with_attachment(logged_in)
    resp = logged_in.get(reverse('bug_report_attachment', args=[att.pk]))
    assert resp.status_code == 200
    assert 'attachment' in resp['Content-Disposition']


def test_download_other_user_forbidden(client, logged_in):
    att = _submit_with_attachment(logged_in)
    other = UserFactory()
    client.force_login(other)
    resp = client.get(reverse('bug_report_attachment', args=[att.pk]))
    assert resp.status_code == 403


def test_download_staff_ok(client, logged_in, admin_user):
    att = _submit_with_attachment(logged_in)
    client.force_login(admin_user)
    resp = client.get(reverse('bug_report_attachment', args=[att.pk]))
    assert resp.status_code == 200


def test_cannot_claim_other_sessions_attachment(client, logged_in):
    att_id = _upload(logged_in, 'a.csv').json()['id']
    other = UserFactory()
    client.force_login(other)
    client.post(
        reverse('bug_report_submit'),
        {'title': 't', 'summary': 's', 'attachment_ids': [att_id]},
        content_type='application/json',
    )
    assert BugReportAttachment.objects.filter(pk=att_id, bug_report__isnull=False).count() == 0
