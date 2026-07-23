# Plane Plus — Hierarchy depth validation utilities
# Enforces: Epic -> Work Item -> Sub-item (3 levels max)
#
# Rules:
# 1. An epic cannot be set as parent of another epic
# 2. A work item that already has a parent (sub-item) cannot become a parent
# 3. No circular parent references
# 4. An epic cannot have a parent (epics are always top-level)

from rest_framework import serializers

from plane.db.models import Issue


def validate_parent_hierarchy(child_issue_or_id, parent_issue_or_id, is_child_epic=None):
    """Validate that setting parent on child does not violate hierarchy rules.

    Args:
        child_issue_or_id: The Issue instance or ID that will become the child.
        parent_issue_or_id: The Issue instance or ID that will become the parent.
            Pass None to clear the parent (always valid).
        is_child_epic: Optional bool. If not provided, will be looked up from DB.

    Raises:
        serializers.ValidationError on any violation.
    """
    if parent_issue_or_id is None:
        return

    # Resolve to instances if needed
    if isinstance(parent_issue_or_id, Issue):
        parent = parent_issue_or_id
    else:
        parent = Issue.objects.select_related("type", "parent").filter(
            pk=parent_issue_or_id
        ).first()
        if not parent:
            raise serializers.ValidationError(
                "Parent issue not found."
            )

    if isinstance(child_issue_or_id, Issue):
        child = child_issue_or_id
        child_id = child.pk
    else:
        child_id = child_issue_or_id
        child = Issue.objects.select_related("type").filter(
            pk=child_id
        ).first()

    # Determine if child is an epic
    if is_child_epic is None and child is not None:
        is_child_epic = (
            child.type_id is not None
            and child.type.is_epic
        )

    # Rule 1: Epics cannot have a parent
    if is_child_epic:
        raise serializers.ValidationError(
            "An epic cannot be set as a child of another issue."
        )

    # Rule 2: Parent cannot be a sub-item (already has a parent itself)
    parent_is_epic = (
        parent.type_id is not None
        and parent.type.is_epic
    )
    if not parent_is_epic and parent.parent_id is not None:
        raise serializers.ValidationError(
            "Cannot add a child to a sub-item. Maximum hierarchy depth is 3 levels "
            "(Epic/Work Item -> Work Item -> Sub-item)."
        )

    # Rule 3: Child cannot already be a parent (would create depth > 3)
    # Only applies if child exists already (update path)
    if child is not None and child.pk:
        has_children = Issue.issue_objects.filter(parent_id=child.pk).exists()
        if has_children:
            raise serializers.ValidationError(
                "This work item already has children. Moving it under another parent "
                "would exceed the maximum hierarchy depth of 3 levels."
            )

    # Rule 4: Circular reference detection
    if child is not None and child.pk:
        _check_circular_reference(child.pk, parent)


def _check_circular_reference(child_id, parent):
    """Walk up the parent chain from parent to ensure child_id is not an ancestor."""
    visited = set()
    current = parent
    while current is not None:
        if current.pk == child_id:
            raise serializers.ValidationError(
                "Circular parent reference detected."
            )
        if current.pk in visited:
            break  # already a cycle in existing data, stop
        visited.add(current.pk)
        if current.parent_id is not None:
            current = Issue.objects.select_related("type").filter(
                pk=current.parent_id
            ).first()
        else:
            current = None


def validate_sub_issues_bulk(parent_issue, sub_issue_ids):
    """Validate a bulk sub-issue assignment (SubIssuesEndpoint.post).

    Args:
        parent_issue: The Issue instance that will become the parent.
        sub_issue_ids: List of issue IDs to assign as children.

    Raises:
        serializers.ValidationError on any violation.
    """
    parent_is_epic = (
        parent_issue.type_id is not None
        and parent_issue.type.is_epic
    )

    # Parent cannot be a sub-item itself (unless it's an epic)
    if not parent_is_epic and parent_issue.parent_id is not None:
        raise serializers.ValidationError(
            "Cannot add children to a sub-item. Maximum hierarchy depth is 3 levels."
        )

    # Load all candidate children
    sub_issues = Issue.objects.select_related("type").filter(
        id__in=sub_issue_ids
    )

    for sub_issue in sub_issues:
        child_is_epic = (
            sub_issue.type_id is not None
            and sub_issue.type.is_epic
        )

        # Epics cannot be children
        if child_is_epic:
            raise serializers.ValidationError(
                f"Issue {sub_issue.pk} is an epic and cannot be set as a sub-issue."
            )

        # Children that already have their own children cannot be re-parented
        # under a non-epic parent that already has a parent (would exceed depth)
        has_children = Issue.issue_objects.filter(parent_id=sub_issue.pk).exists()
        if has_children and not parent_is_epic:
            raise serializers.ValidationError(
                f"Issue {sub_issue.pk} already has children. Assigning it as a "
                f"sub-issue would exceed the maximum hierarchy depth of 3 levels."
            )

        # Circular reference check
        _check_circular_reference(sub_issue.pk, parent_issue)
