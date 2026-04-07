import uuid

from django.conf import settings
from django.db import models


class RetailerProfile(models.Model):
    """Links a Django User to a retailer role (CEO or Store Manager)."""

    ROLE_CHOICES = [
        ("ceo", "CEO"),
        ("manager", "Store Manager"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="retailer_profile",
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="manager")

    class Meta:
        db_table = "retailer_profiles"

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


class Product(models.Model):
    """Mirror of the 'products' table in the cloud PostgreSQL database."""

    product_id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    current_stock = models.IntegerField(default=0)
    reserved_stock = models.IntegerField(default=0)
    aisle_zone = models.CharField(max_length=50, blank=True, null=True)
    image_url = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "products"

    def __str__(self):
        return self.name


class ActiveCartSession(models.Model):
    """Mirror of the 'active_cart_sessions' table."""

    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    customer_id = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20)
    current_zone = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "active_cart_sessions"

    def __str__(self):
        return f"Session {self.session_id} — {self.status}"


class ActiveCartItem(models.Model):
    """Mirror of the 'active_cart_items' table."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    session = models.ForeignKey(
        ActiveCartSession,
        on_delete=models.CASCADE,
        db_column="session_id",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        db_column="product_id",
    )
    quantity = models.IntegerField(default=1)

    class Meta:
        managed = False
        db_table = "active_cart_items"

    def __str__(self):
        return f"{self.product_id} ×{self.quantity}"


class BeaconZone(models.Model):
    """Maps a physical BLE beacon (identified by major + minor) to a
    store aisle/zone.  Used by the location endpoint to resolve the
    shopper's current zone from the strongest beacon signal."""

    major = models.IntegerField(help_text="iBeacon major value (0–65535)")
    minor = models.IntegerField(help_text="iBeacon minor value (0–65535)")
    aisle_zone = models.CharField(
        max_length=50,
        help_text="Human-readable zone label, e.g. 'Aisle 1 – Dairy'",
    )

    class Meta:
        db_table = "beacon_zones"
        unique_together = ("major", "minor")

    def __str__(self):
        return f"Beacon ({self.major}, {self.minor}) → {self.aisle_zone}"


class Customer(models.Model):
    """Mirror of the 'customers' table in the cloud PostgreSQL database."""

    customer_id = models.CharField(max_length=50, primary_key=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    mobile_token = models.CharField(max_length=100, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "customers"

    def __str__(self):
        return self.customer_id


class Order(models.Model):
    """Mirror of the 'orders' table in the cloud PostgreSQL database."""

    order_id = models.CharField(max_length=50, primary_key=True)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        db_column="customer_id",
    )
    order_date = models.DateTimeField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        managed = False
        db_table = "orders"

    def __str__(self):
        return f"Order {self.order_id}"


class OrderItem(models.Model):
    """Mirror of the 'order_items' table in the cloud PostgreSQL database."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        db_column="order_id",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        db_column="product_id",
    )
    quantity = models.IntegerField()
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = "order_items"

    def __str__(self):
        return f"Item {self.id} — Order {self.order_id}"


class StoreZone(models.Model):
    """Represents a drawable map section on the store floor plan."""

    ZONE_TYPES = [
        ('aisle', 'Aisle'),
        ('boundary', 'Boundary'),
        ('obstacle', 'Obstacle'),
    ]

    name = models.CharField(max_length=100)
    zone_type = models.CharField(max_length=20, choices=ZONE_TYPES, default='aisle')
    color_hex = models.CharField(max_length=20, default="#33B5E5")
    x_min = models.FloatField(help_text="Min X percentage (0.0 to 1.0)")
    y_min = models.FloatField(help_text="Min Y percentage (0.0 to 1.0)")
    x_max = models.FloatField(help_text="Max X percentage (0.0 to 1.0)")
    y_max = models.FloatField(help_text="Max Y percentage (0.0 to 1.0)")
    major = models.IntegerField(null=True, blank=True, help_text="iBeacon major value")
    minor = models.IntegerField(null=True, blank=True, help_text="iBeacon minor value")

    class Meta:
        db_table = "store_zones"

    def __str__(self):
        return f"Zone {self.name} ({self.color_hex})"


class StoreConfig(models.Model):
    """Singleton model persisting the retailer's store metadata."""
    floor_plan_image_url = models.URLField(max_length=1000, blank=True, null=True)

    class Meta:
        db_table = "store_config"

    def __str__(self):
        return "Store Configuration"

class CartLocation(models.Model):
    """Tracks the real-time position of an active smart cart on the store map."""
    target_uuid = models.CharField(max_length=100, unique=True, db_index=True)
    x_position = models.FloatField(default=0.0)
    y_position = models.FloatField(default=0.0)
    last_updated = models.DateTimeField(auto_now=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cart_locations"

    def __str__(self):
        return f"Cart {self.target_uuid} at ({self.x_position:.2f}, {self.y_position:.2f})"


class RoutePath(models.Model):
    """A straight-line path segment drawn by the retailer on the floor plan.

    Coordinates are stored as percentages (0.0 – 1.0) relative to the
    floor-plan image dimensions.  The ``length`` field is the Euclidean
    distance between the two endpoints, auto-calculated on save.
    """

    start_x = models.FloatField(help_text="Start X percentage (0.0 to 1.0)")
    start_y = models.FloatField(help_text="Start Y percentage (0.0 to 1.0)")
    end_x = models.FloatField(help_text="End X percentage (0.0 to 1.0)")
    end_y = models.FloatField(help_text="End Y percentage (0.0 to 1.0)")
    length = models.FloatField(
        editable=False,
        default=0.0,
        help_text="Euclidean distance between the two endpoints",
    )

    class Meta:
        db_table = "route_paths"

    def save(self, *args, **kwargs):
        self.length = (
            (self.end_x - self.start_x) ** 2
            + (self.end_y - self.start_y) ** 2
        ) ** 0.5
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"Path {self.pk}: "
            f"({self.start_x:.2f}, {self.start_y:.2f}) → "
            f"({self.end_x:.2f}, {self.end_y:.2f})  len={self.length:.4f}"
        )
