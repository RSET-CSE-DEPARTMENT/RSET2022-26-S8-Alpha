from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Product, RetailerProfile, StoreZone, StoreConfig, RoutePath


class ProductSerializer(serializers.ModelSerializer):
    """Serializes all fields of the Product model for the inventory API."""

    class Meta:
        model = Product
        fields = ["product_id", "name", "category", "price", "current_stock"]


class RecommendationProductSerializer(serializers.ModelSerializer):
    """Serializes Product model for recommendation responses."""

    class Meta:
        model = Product
        fields = ["product_id", "name", "price", "aisle_zone"]


class RetailerLoginSerializer(serializers.Serializer):
    """Validates retailer login credentials (username + password)."""

    username = serializers.CharField()
    password = serializers.CharField()


class ShopperOtpSerializer(serializers.Serializer):
    """Validates the 6-digit OTP sent by the shopper app."""

    otp = serializers.CharField(max_length=6, min_length=6)


class ManagerSerializer(serializers.Serializer):
    """For creating a new store manager (CEO-only endpoint)."""

    username = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=6)


class ManagerListSerializer(serializers.ModelSerializer):
    """Serializes manager user information for the list view."""

    role = serializers.CharField(source="retailer_profile.role", read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "role", "date_joined"]



class BeaconReadingSerializer(serializers.Serializer):
    """Validates a single beacon reading within a batch."""

    major = serializers.IntegerField(
        min_value=0,
        max_value=65535,
        help_text="iBeacon major value",
    )
    minor = serializers.IntegerField(
        min_value=0,
        max_value=65535,
        help_text="iBeacon minor value",
    )
    rssi = serializers.IntegerField(
        help_text="Received Signal Strength Indicator (dBm, typically negative)",
    )


class BatchLocationUpdateSerializer(serializers.Serializer):
    """
    Validates a batched BLE iBeacon payload from the ESP32.

    Expected JSON:
    {
        "target_uuid": "11112222-3333-4444-5555-666677778888",
        "beacons": [
            {"major": 1, "minor": 1, "rssi": -65},
            {"major": 1, "minor": 2, "rssi": -70}
        ]
    }
    """

    target_uuid = serializers.CharField(
        max_length=36,
        help_text="iBeacon proximity UUID (e.g. 'fda50693-a4e2-4fb1-afcf-c6eb07647825')",
    )
    beacons = BeaconReadingSerializer(
        many=True,
        allow_empty=False,
        help_text="List of beacon readings detected in this scan cycle",
    )


class CheckoutItemSerializer(serializers.Serializer):
    """Validates an individual item within a checkout payload."""

    product_id = serializers.CharField(max_length=50)
    quantity = serializers.IntegerField(min_value=1)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)


class CheckoutSerializer(serializers.Serializer):
    """Validates the main checkout payload from the shopper app."""

    customer_id = serializers.CharField(max_length=50)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    items = CheckoutItemSerializer(many=True, allow_empty=False)


class StoreZoneSerializer(serializers.ModelSerializer):
    """Serializes StoreZone model for the store layout editor and shopper map APIs."""

    class Meta:
        model = StoreZone
        fields = ["id", "name", "zone_type", "color_hex", "x_min", "y_min", "x_max", "y_max", "major", "minor"]


class StoreConfigSerializer(serializers.ModelSerializer):
    """Serializes the singleton StoreConfig model."""

    class Meta:
        model = StoreConfig
        fields = ["id", "floor_plan_image_url"]


class RoutePathSerializer(serializers.ModelSerializer):
    """Serializes RoutePath model for the pathfinding route editor API.

    ``length`` is read-only — it is auto-computed on save.
    """

    class Meta:
        model = RoutePath
        fields = ["id", "start_x", "start_y", "end_x", "end_y", "length"]
        read_only_fields = ["length"]
