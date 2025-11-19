from django.core.management.base import BaseCommand
from apps.houses.models import House


class Command(BaseCommand):
    help = "Create default Game of Thrones Houses"

    def handle(self, *args, **options):
        deleted_count, _ = House.objects.all().delete()
        self.stdout.write(self.style.WARNING(f"🗑️ Deleted {deleted_count} existing houses."))

        houses_data = [
            {
                "name": "House Lannister of Casterly Rock",
                "motto": "Hear Me Roar!",
                "color_primary": "#FF0000",  # Crimson Red
                "color_secondary": "#FFD700",  # Gold
                "crest": "house_crests/lannister.jpg",
            },
            {
                "name": "House Stark of Winterfell",
                "motto": "Winter Is Coming",
                "color_primary": "#A9A9A9",  # Gray
                "color_secondary": "#000000",  # Black
                "crest": "house_crests/stark.jpg",
            },
            {
                "name": "House Targaryen of Dragonstone",
                "motto": "Fire and Blood",
                "color_primary": "#000000",  # Black
                "color_secondary": "#FF0000",  # Red
                "crest": "house_crests/tageryn.jpg",
            },
            {
                "name": "House Baratheon of Storm’s End",
                "motto": "Ours is the Fury",
                "color_primary": "#FFD700",  # Gold
                "color_secondary": "#000000",  # Black
                "crest": "house_crests/barrthon.jpg"
            },
            {
                "name": "House Greyjoy of Pyke",
                "motto": "We Do Not Sow",
                "color_primary": "#2F4F4F",  # Dark Slate Gray
                "color_secondary": "#DAA520",  # Goldenrod
                "crest": "house_crests/greyjoy.jpg"
            },
        ]

        for house_data in houses_data:
            house, created = House.objects.get_or_create(
                name=house_data["name"],
                defaults={
                    "motto": house_data["motto"],
                    "color_primary": house_data["color_primary"],
                    "color_secondary": house_data["color_secondary"],
                    "crest": house_data["crest"],
                },
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"✅ Created {house.name}"))
            else:
                self.stdout.write(self.style.WARNING(f"⚠️ {house.name} already exists"))

        self.stdout.write(self.style.SUCCESS("🎉 All houses processed successfully!"))
