# Plane Plus — PageFolder model for organizing workspace wiki pages.

from django.db import models

from .base import BaseModel


class PageFolder(BaseModel):
    """Folder for organizing workspace wiki pages."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    icon = models.CharField(max_length=50, blank=True, default="")
    parent_folder = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    workspace = models.ForeignKey(
        "db.Workspace",
        on_delete=models.CASCADE,
        related_name="page_folders",
    )

    class Meta:
        db_table = "page_folders"
        ordering = ["name"]
        verbose_name = "Page Folder"
        verbose_name_plural = "Page Folders"

    def __str__(self):
        return f"{self.name} ({self.workspace})"
