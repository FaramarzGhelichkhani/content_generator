from django.core.management.base import BaseCommand, CommandError

from core.models import Project
from content.services.pagebrief_sync import sync_project


class Command(BaseCommand):
    help = "Sync all page briefs, page contents and internal links."

    def add_arguments(self, parser):
        parser.add_argument("--project-id", type=int, required=True)
        parser.add_argument("--keyword-ids", type=int, nargs="*", default=None)
        parser.add_argument("--entity-ids", type=int, nargs="*", default=None)
        parser.add_argument("--no-links", action="store_true")

    def handle(self, *args, **opts):
        try:
            project = Project.objects.get(id=opts["project_id"])
        except Project.DoesNotExist:
            raise CommandError("Project not found")

        result = sync_project(
            project=project,
            keyword_ids=opts["keyword_ids"],
            entity_ids=opts["entity_ids"],
            rebuild_links=not opts["no_links"],
        )

        self.stdout.write(self.style.SUCCESS(
            f"root={len(result['root_pages'])} "
            f"entity={len(result['entity_pages'])} "
            f"keyword={len(result['keyword_pages'])}"
        ))