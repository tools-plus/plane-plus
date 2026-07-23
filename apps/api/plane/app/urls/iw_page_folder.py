# Plane Plus — PageFolder URL patterns for wiki folder management.

from django.urls import path

from plane.app.views import PageFolderViewSet

urlpatterns = [
    path(
        "workspaces/<str:slug>/page-folders/",
        PageFolderViewSet.as_view({"get": "list", "post": "create"}),
        name="page-folders",
    ),
    path(
        "workspaces/<str:slug>/page-folders/<uuid:pk>/",
        PageFolderViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="page-folders-detail",
    ),
]
