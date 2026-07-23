# Plane Plus — Create AgentDoc table for workspace-level markdown notes.
#
# Forwards-only. Pure DDL: new table, new indexes, no data migration.
# Drop is intentionally not supported in this branch — once we start writing
# agent state to it, rollback would mean data loss. If we need to undo, do it
# in a follow-up migration with an explicit data-export step.

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "iw_003_pagefolder_and_page_folder_fk"),
    ]

    operations = [
        migrations.CreateModel(
            name="AgentDoc",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Last Modified At"),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="Deleted At"),
                ),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("path", models.CharField(max_length=256)),
                ("content", models.TextField(blank=True, default="")),
                ("version", models.PositiveIntegerField(default=1)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Last Modified By",
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="agent_docs",
                        to="db.workspace",
                    ),
                ),
            ],
            options={
                "db_table": "agent_docs",
                "verbose_name": "Agent Doc",
                "verbose_name_plural": "Agent Docs",
                "ordering": ["path"],
            },
        ),
        migrations.AddConstraint(
            model_name="agentdoc",
            constraint=models.UniqueConstraint(
                fields=("workspace", "path"),
                name="agent_doc_workspace_path_uniq",
            ),
        ),
        migrations.AddIndex(
            model_name="agentdoc",
            index=models.Index(
                fields=["workspace", "path"],
                name="agent_doc_ws_path_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="agentdoc",
            index=models.Index(
                fields=["workspace", "-updated_at"],
                name="agent_doc_ws_updated_idx",
            ),
        ),
    ]
