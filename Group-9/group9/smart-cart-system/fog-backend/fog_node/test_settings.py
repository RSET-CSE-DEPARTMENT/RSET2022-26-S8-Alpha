"""
Test-specific settings.
Inherits everything from the main settings but swaps the database
to an in-memory SQLite so tests run without PostgreSQL.
"""
from fog_node.settings import *  # noqa: F401, F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# ── Force managed=False models to create tables during tests ──
# The models marked managed=False (Product, Customer, Order, etc.) exist in
# the cloud Supabase DB in production. In tests we use SQLite and need Django
# to actually create those tables.

from django.test.runner import DiscoverRunner


class ManagedModelTestRunner(DiscoverRunner):
    """Flips managed=False → True on ALL models *before* the DB is created,
    then restores after teardown."""

    def setup_databases(self, **kwargs):
        from django.apps import apps

        self._unmanaged = []
        for model in apps.get_models():
            if not model._meta.managed:
                model._meta.managed = True
                self._unmanaged.append(model)

        result = super().setup_databases(**kwargs)
        return result

    def teardown_databases(self, old_config, **kwargs):
        super().teardown_databases(old_config, **kwargs)
        for model in self._unmanaged:
            model._meta.managed = False


TEST_RUNNER = "fog_node.test_settings.ManagedModelTestRunner"

# Skip all migrations so that syncdb is used — this respects our managed=True
# override and creates full tables for every model including the unmanaged ones.
MIGRATION_MODULES = {
    "cart_api": None,
    "admin": None,
    "auth": None,
    "contenttypes": None,
    "sessions": None,
}
