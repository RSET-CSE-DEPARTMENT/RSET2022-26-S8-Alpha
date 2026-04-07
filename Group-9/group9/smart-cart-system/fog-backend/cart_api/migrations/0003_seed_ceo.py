"""
Data migration: seed the CEO user.

Creates a Django superuser with username "ceo" and password "smartcart2026",
linked to a RetailerProfile with role="ceo".
"""

from django.db import migrations


def seed_ceo(apps, schema_editor):
    from django.contrib.auth.hashers import make_password

    User = apps.get_model("auth", "User")
    RetailerProfile = apps.get_model("cart_api", "RetailerProfile")

    if not User.objects.filter(username="ceo").exists():
        user = User.objects.create(
            username="ceo",
            password=make_password("smartcart2026"),
            is_staff=True,
            is_superuser=True,
        )
        RetailerProfile.objects.create(user=user, role="ceo")


def remove_ceo(apps, schema_editor):
    User = apps.get_model("auth", "User")
    User.objects.filter(username="ceo").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("cart_api", "0002_retailer_profile"),
    ]

    operations = [
        migrations.RunPython(seed_ceo, remove_ceo),
    ]
