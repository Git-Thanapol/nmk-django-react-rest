import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateMediaStorage(FileSystemStorage):
    """Files outside MEDIA_ROOT, never served by nginx or the DEBUG static handler.

    No base_url, so .url raises; access only through login-checked views.
    Root is read lazily so tests can override settings.PRIVATE_MEDIA_ROOT.
    """

    @property
    def base_location(self):
        return settings.PRIVATE_MEDIA_ROOT

    @property
    def location(self):
        return os.path.abspath(self.base_location)

    @property
    def base_url(self):
        return None
