from django.apps import AppConfig


class AiConfig(AppConfig):
    name = "plane.ai"
    verbose_name = "Plane AI"

    def ready(self):
        import plane.ai.signals  # noqa: F401 — register signal handlers
