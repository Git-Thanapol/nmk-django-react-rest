import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

import os
from datetime import timedelta

from django.utils import timezone

from api.models import BugReport, BugReportAttachment, BugReportImage
from .factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _isolated(settings, tmp_path):
    settings.SECURE_SSL_REDIRECT = False
    settings.ALLOWED_HOSTS = ['testserver']
    settings.PRIVATE_MEDIA_ROOT = str(tmp_path / 'private')
    settings.MEDIA_ROOT = str(tmp_path / 'media')


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


def _submit(client, **payload):
    return client.post(
        reverse('bug_report_submit'),
        {'title': 't', 'summary': 's', **payload},
        content_type='application/json',
    )


def test_attachment_stored_outside_media_root(logged_in, settings):
    att_id = _upload(logged_in, 'a.csv').json()['id']
    att = BugReportAttachment.objects.get(pk=att_id)
    assert os.path.abspath(att.file.path).startswith(settings.PRIVATE_MEDIA_ROOT)
    with pytest.raises(ValueError):
        att.file.url


def test_bad_attachment_ids_do_not_500(logged_in):
    assert _submit(logged_in, attachment_ids='abc', image_ids=['x', None]).status_code == 200
    assert _submit(logged_in, attachment_ids=['x', True]).status_code == 200


def test_cannot_claim_other_users_image(client, logged_in):
    img = BugReportImage.objects.create(
        image=SimpleUploadedFile('i.png', b'x'), session_key='someone-else'
    )
    assert _submit(logged_in, image_ids=[img.pk]).status_code == 200
    img.refresh_from_db()
    assert img.bug_report_id is None


def test_unclaimed_drafts_deleted_with_files(logged_in):
    att_id = _upload(logged_in, 'keep.csv').json()['id']
    drop_id = _upload(logged_in, 'drop.csv').json()['id']
    drop_path = BugReportAttachment.objects.get(pk=drop_id).file.path
    assert os.path.exists(drop_path)
    _submit(logged_in, attachment_ids=[att_id])
    assert not BugReportAttachment.objects.filter(pk=drop_id).exists()
    assert not os.path.exists(drop_path)
    assert BugReportAttachment.objects.get(pk=att_id).bug_report_id is not None


def test_deleting_report_deletes_files(logged_in):
    att = _submit_with_attachment(logged_in)
    path = att.file.path
    assert os.path.exists(path)
    att.bug_report.delete()
    assert not os.path.exists(path)


def test_stale_drafts_purged_on_upload(logged_in):
    old_id = _upload(logged_in, 'old.csv').json()['id']
    BugReportAttachment.objects.filter(pk=old_id).update(
        uploaded_at=timezone.now() - timedelta(hours=48)
    )
    _upload(logged_in, 'new.csv')
    assert not BugReportAttachment.objects.filter(pk=old_id).exists()


def test_download_missing_file_is_404(logged_in):
    att = _submit_with_attachment(logged_in)
    os.remove(att.file.path)
    resp = logged_in.get(reverse('bug_report_attachment', args=[att.pk]))
    assert resp.status_code == 404


def test_discard_draft(logged_in):
    att_id = _upload(logged_in, 'a.csv').json()['id']
    path = BugReportAttachment.objects.get(pk=att_id).file.path
    resp = logged_in.post(reverse('bug_report_attachment_discard', args=[att_id]))
    assert resp.status_code == 200
    assert not BugReportAttachment.objects.filter(pk=att_id).exists()
    assert not os.path.exists(path)


def test_discard_other_session_forbidden(client, logged_in):
    att_id = _upload(logged_in, 'a.csv').json()['id']
    client.force_login(UserFactory())
    resp = client.post(reverse('bug_report_attachment_discard', args=[att_id]))
    assert resp.status_code == 404
    assert BugReportAttachment.objects.filter(pk=att_id).exists()


def test_discard_submitted_attachment_not_allowed(logged_in):
    att = _submit_with_attachment(logged_in)
    resp = logged_in.post(reverse('bug_report_attachment_discard', args=[att.pk]))
    assert resp.status_code == 404
