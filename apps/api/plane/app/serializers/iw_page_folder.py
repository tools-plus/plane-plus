# Plane Plus — PageFolder serializer for wiki folder management.

from .base import BaseSerializer
from plane.db.models import PageFolder


class PageFolderSerializer(BaseSerializer):
    class Meta:
        model = PageFolder
        fields = [
            "id",
            "name",
            "description",
            "icon",
            "parent_folder",
            "workspace",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["workspace", "created_by", "updated_by"]
