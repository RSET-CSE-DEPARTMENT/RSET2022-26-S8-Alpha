import logging
import uuid
from django.utils import timezone
from django.db import transaction
from datetime import timedelta

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView  # noqa: F401 (re-exported in urls)

from .models import ActiveCartSession, BeaconZone, Customer, Product, RetailerProfile, Order, OrderItem, StoreZone, StoreConfig, CartLocation, RoutePath
from .serializers import (
    BatchLocationUpdateSerializer,
    CheckoutSerializer,
    ManagerListSerializer,
    ManagerSerializer,
    ProductSerializer,
    RecommendationProductSerializer,
    RetailerLoginSerializer,
    ShopperOtpSerializer,
    StoreZoneSerializer,
    StoreConfigSerializer,
    RoutePathSerializer,
)
from .ml_services import RecommendationEngine

logger = logging.getLogger(__name__)


# ─── Auth Views ────────────────────────────────────────────────────────────


class RetailerLoginView(APIView):
    """
    POST /api/auth/retailer/login/

    Validates username + password and returns a JWT pair + role.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RetailerLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )

        if user is None:
            return Response(
                {"detail": "Invalid username or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Determine role
        try:
            role = user.retailer_profile.role
        except RetailerProfile.DoesNotExist:
            role = "unknown"

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "role": role,
                "username": user.username,
            },
            status=status.HTTP_200_OK,
        )


class ShopperVerifyOtpView(APIView):
    """
    POST /api/auth/shopper/verify-otp/

    Accepts {"otp": "123456"}, looks up a Customer by mobile_token,
    and returns a short-lived JWT.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ShopperOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        otp = serializer.validated_data["otp"]
        customer = Customer.objects.filter(mobile_token=otp).first()

        if customer is None:
            return Response(
                {"detail": "Invalid OTP."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Create a token with custom claims
        refresh = RefreshToken()
        refresh["customer_id"] = customer.customer_id
        refresh["type"] = "shopper"

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "customer_id": customer.customer_id,
            },
            status=status.HTTP_200_OK,
        )


# ─── Manager CRUD (CEO only) ──────────────────────────────────────────────


class IsCeo:
    """Inline permission check mixin — raises 403 if user is not a CEO."""

    def check_ceo(self, request):
        if not request.user.is_authenticated:
            return False
        try:
            return request.user.retailer_profile.role == "ceo"
        except RetailerProfile.DoesNotExist:
            return False


class ManagerListCreateView(APIView, IsCeo):
    """
    GET  /api/auth/managers/      — list all store managers (CEO only)
    POST /api/auth/managers/      — create a store manager  (CEO only)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not self.check_ceo(request):
            return Response(
                {"detail": "CEO access required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        managers = User.objects.filter(
            retailer_profile__role="manager"
        ).select_related("retailer_profile")
        serializer = ManagerListSerializer(managers, many=True)
        return Response(serializer.data)

    def post(self, request):
        if not self.check_ceo(request):
            return Response(
                {"detail": "CEO access required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ManagerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        if User.objects.filter(username=username).exists():
            return Response(
                {"detail": f"Username '{username}' already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.create_user(username=username, password=password)
        RetailerProfile.objects.create(user=user, role="manager")

        return Response(
            {"id": user.id, "username": user.username, "role": "manager"},
            status=status.HTTP_201_CREATED,
        )


class ManagerDeleteView(APIView, IsCeo):
    """
    DELETE /api/auth/managers/<int:pk>/  — delete a store manager (CEO only)
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        if not self.check_ceo(request):
            return Response(
                {"detail": "CEO access required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            user = User.objects.get(pk=pk, retailer_profile__role="manager")
        except User.DoesNotExist:
            return Response(
                {"detail": "Manager not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Product & Location Views ─────────────────────────────────────────────


class ProductListView(generics.ListCreateAPIView):
    """
    GET /api/products/
    POST /api/products/

    Returns the full list of products from the database or creates a new one.
    Publicly accessible to allow the shopper app to load the catalog.
    """

    permission_classes = [AllowAny]
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class ProductDetailView(generics.RetrieveUpdateAPIView):
    """
    GET /api/products/<product_id>/
    PATCH /api/products/<product_id>/
    PUT /api/products/<product_id>/

    Retrieve or update a specific product.
    """

    permission_classes = [AllowAny]
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = 'product_id'


class LocationUpdateView(APIView):
    """
    POST /api/location/update/

    Accepts a batched BLE iBeacon payload from the ESP32.
    Stays open (no auth) — the ESP32 cannot carry a JWT.

    Raw Tracking — takes the single strongest beacon (highest RSSI,
    i.e. closest to 0) and immediately updates the cart position.
    No smoothing, no thresholds, no history.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = BatchLocationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        target_uuid = data["target_uuid"]
        beacons = data["beacons"]

        # ── Sort by RSSI descending (closest to 0 = strongest) ─────────
        beacons_sorted = sorted(beacons, key=lambda b: b["rssi"], reverse=True)
        strongest = beacons_sorted[0]

        beacon_major = strongest["major"]
        beacon_minor = strongest["minor"]

        # ── Resolve zone ───────────────────────────────────────────────
        zone = BeaconZone.objects.filter(
            major=beacon_major,
            minor=beacon_minor,
        ).first()
        aisle_zone = zone.aisle_zone if zone else "unknown"

        # Find matching map node to position the cart
        store_zone = StoreZone.objects.filter(
            major=beacon_major,
            minor=beacon_minor,
        ).first()

        if store_zone:
            center_x = (store_zone.x_min + store_zone.x_max) / 2
            center_y = (store_zone.y_min + store_zone.y_max) / 2

            loc, created = CartLocation.objects.update_or_create(
                target_uuid=target_uuid,
                defaults={
                    "x_position": center_x,
                    "y_position": center_y,
                }
            )
            if not created:
                loc.save()

        # ── Update current_zone on the ActiveCartSession ──────────────
        zone_name = store_zone.name if store_zone else (zone.aisle_zone if zone else None)
        if zone_name:
            try:
                session = ActiveCartSession.objects.get(session_id=target_uuid)
                session.current_zone = zone_name
                session.save(update_fields=["current_zone"])
            except ActiveCartSession.DoesNotExist:
                logger.warning("No ActiveCartSession for UUID=%s – skipping zone update.", target_uuid)

        # ── Logging ────────────────────────────────────────────────────
        logger.info(
            "BLE Batch ▸ UUID=%s  |  %d beacon(s)  |  Zone=%s  "
            "(raw #1: Major=%s Minor=%s RSSI=%s dBm)",
            target_uuid,
            len(beacons),
            aisle_zone,
            beacon_major, beacon_minor, strongest["rssi"],
        )

        return Response(
            {
                "status": "received",
                "target_uuid": target_uuid,
                "beacon_count": len(beacons),
                "aisle_zone": aisle_zone,
                "strongest_beacon": {
                    "major": beacon_major,
                    "minor": beacon_minor,
                    "rssi": strongest["rssi"],
                },
            },
            status=status.HTTP_201_CREATED,
        )


class CartStartView(APIView):
    """
    POST /api/cart/start/

    Initializes (or resets) an ActiveCartSession row for the given cart UUID.
    Called by the Flutter app right before entering the shopping dashboard.

    Payload: {"target_uuid": "the-cart-uuid"}
    """

    permission_classes = [AllowAny]

    def post(self, request):
        target_uuid = request.data.get("target_uuid")
        if not target_uuid:
            return Response(
                {"detail": "target_uuid is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session, created = ActiveCartSession.objects.update_or_create(
            session_id=target_uuid,
            defaults={
                "status": "active",
                "current_zone": None,
            },
        )

        # Also reset the CartLocation so the map starts at (0, 0)
        CartLocation.objects.update_or_create(
            target_uuid=target_uuid,
            defaults={"x_position": 0.0, "y_position": 0.0},
        )

        logger.info(
            "Cart session %s — %s",
            "CREATED" if created else "RESET",
            target_uuid,
        )

        return Response(
            {"status": "session_started", "session_id": str(session.session_id)},
            status=status.HTTP_200_OK,
        )


class CheckoutView(APIView):
    """
    POST /api/checkout/

    Accepts checkout payload, creates an Order and associated OrderItems
    in a transaction, and updates product stock.
    """

    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        customer_id = data["customer_id"]
        total_amount = data["total_amount"]
        items = data["items"]

        customer = Customer.objects.filter(customer_id=customer_id).first()

        order_id = str(uuid.uuid4())
        order = Order.objects.create(
            order_id=order_id,
            customer=customer,
            order_date=timezone.now(),
            total_amount=total_amount,
        )

        for item in items:
            product_id = item["product_id"]
            quantity = item["quantity"]
            price_at_purchase = item["price"]

            product = Product.objects.filter(product_id=product_id).first()
            if product:
                product.current_stock = max(0, product.current_stock - quantity)
                product.save(update_fields=["current_stock"])

            OrderItem.objects.create(
                id=uuid.uuid4(),
                order=order,
                product=product,
                quantity=quantity,
                price_at_purchase=price_at_purchase,
            )

        return Response(
            {"status": "checkout_successful", "order_id": order_id},
            status=status.HTTP_201_CREATED,
        )


class RecommendationView(APIView):
    """
    POST /api/recommend/

    Accepts {"cart_items": ["PROD-1", "PROD-2"]} and returns recommended 
    products using the ML engine.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        cart_items = request.data.get("cart_items", [])
        if not isinstance(cart_items, list):
            return Response(
                {"detail": "cart_items must be a list of product IDs."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get top product IDs from engine
        recommended_ids = RecommendationEngine.get_recommendations(cart_items)

        if not recommended_ids:
            return Response([], status=status.HTTP_200_OK)

        # Query products
        products = Product.objects.filter(product_id__in=recommended_ids)

        # Reorder to match recommendation ranking
        product_dict = {p.product_id: p for p in products}
        ordered_products = [
            product_dict[r_id] for r_id in recommended_ids if r_id in product_dict
        ]

        # Serialize Name, Price, Aisle_zone
        serializer = RecommendationProductSerializer(ordered_products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StoreZoneListCreateAPIView(generics.ListCreateAPIView):
    """
    GET /api/zones/
    POST /api/zones/

    List all store zones or create a new one.
    """

    permission_classes = [AllowAny]
    queryset = StoreZone.objects.all()
    serializer_class = StoreZoneSerializer


class StoreZoneRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/zones/<int:pk>/
    PUT /api/zones/<int:pk>/
    PATCH /api/zones/<int:pk>/
    DELETE /api/zones/<int:pk>/

    Retrieve, update, or delete a specific store zone.
    """

    permission_classes = [AllowAny]
    queryset = StoreZone.objects.all()
    serializer_class = StoreZoneSerializer


class StoreConfigAPIView(generics.RetrieveUpdateAPIView):
    """
    GET /api/store-config/
    PATCH /api/store-config/

    Retrieve or update the single StoreConfig instance containing
    the floor plan image URL.
    """

    permission_classes = [AllowAny]
    serializer_class = StoreConfigSerializer

    def get_object(self):
        # Always return the first/only StoreConfig instance.
        config, created = StoreConfig.objects.get_or_create(id=1)
        return config


class CartLocationRetrieveAPIView(APIView):
    """
    GET /api/location/<str:target_uuid>/
    
    Returns the current x,y position of the given cart.
    """
    permission_classes = [AllowAny]

    def get(self, request, target_uuid):
        location = CartLocation.objects.filter(target_uuid=target_uuid).first()
        if not location:
            return Response({"detail": "Location not found."}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            "target_uuid": location.target_uuid,
            "x_position": location.x_position,
            "y_position": location.y_position,
            "last_updated": location.last_updated,
            "last_seen": location.last_seen
        }, status=status.HTTP_200_OK)


class StoreConfigClearAllView(APIView):
    """
    POST /api/store-config/clear-all/
    
    Deletes all StoreZone and RoutePath records, and clears the
    floor_plan_image_url in StoreConfig.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        StoreZone.objects.all().delete()
        RoutePath.objects.all().delete()
        
        config = StoreConfig.objects.first()
        if config:
            config.floor_plan_image_url = ""
            config.save(update_fields=["floor_plan_image_url"])
            
        return Response({"detail": "Store configuration cleared."}, status=status.HTTP_200_OK)


class LiveCartsAnalyticsView(APIView):
    """
    GET /api/analytics/live-carts/
    
    Count all active carts where last_seen is within the last 30 seconds.
    Loop through these carts and check their x_position and y_position against the 
    x_min/x_max/y_min/y_max of all StoreZones (where zone_type is 'aisle').
    """
    permission_classes = [AllowAny]

    def get(self, request):
        thirty_seconds_ago = timezone.now() - timedelta(seconds=30)
        active_carts = CartLocation.objects.filter(last_seen__gte=thirty_seconds_ago)
        
        aisle_zones = StoreZone.objects.filter(zone_type='aisle')
        
        zone_counts = {zone.name: 0 for zone in aisle_zones}
        total_active_carts = active_carts.count()
        
        for cart in active_carts:
            for zone in aisle_zones:
                if (zone.x_min <= cart.x_position <= zone.x_max) and (zone.y_min <= cart.y_position <= zone.y_max):
                    zone_counts[zone.name] += 1
                    break
                    
        return Response({
            "total_active_carts": total_active_carts,
            "zone_counts": zone_counts
        }, status=status.HTTP_200_OK)


# ─── Route Path Views ──────────────────────────────────────────────────────


class RoutePathListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/routes/   — list all route-path segments
    POST /api/routes/   — create a new route-path segment
    """

    permission_classes = [AllowAny]
    queryset = RoutePath.objects.all()
    serializer_class = RoutePathSerializer


class RoutePathRetrieveDestroyView(generics.RetrieveDestroyAPIView):
    """
    GET    /api/routes/<int:pk>/   — retrieve a single route-path
    DELETE /api/routes/<int:pk>/   — delete a route-path segment
    """

    permission_classes = [AllowAny]
    queryset = RoutePath.objects.all()
    serializer_class = RoutePathSerializer


# ─── Navigation / Pathfinding ──────────────────────────────────────────────


class NavigationRouteView(APIView):
    """
    GET /api/navigation/route/?start_x=&start_y=&dest_zone_id=

    Calculates the shortest walkable path from the cart's current
    position to the centre of the requested StoreZone, using the
    retailer-drawn RoutePath network.

    Returns a JSON array of {"x": float, "y": float} waypoints.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        from .routing import compute_route  # lazy import to keep module lightweight

        # ── Validate query params ──────────────────────────────────────
        start_x = request.query_params.get("start_x")
        start_y = request.query_params.get("start_y")
        dest_zone_id = request.query_params.get("dest_zone_id")

        if not all([start_x, start_y, dest_zone_id]):
            return Response(
                {"detail": "start_x, start_y, and dest_zone_id are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            start_x = float(start_x)
            start_y = float(start_y)
            dest_zone_id = int(dest_zone_id)
        except (ValueError, TypeError):
            return Response(
                {"detail": "start_x and start_y must be numbers; dest_zone_id must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Look up destination zone ───────────────────────────────────
        zone = StoreZone.objects.filter(pk=dest_zone_id).first()
        if zone is None:
            return Response(
                {"detail": "Destination zone not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        dest_x = (zone.x_min + zone.x_max) / 2
        dest_y = (zone.y_min + zone.y_max) / 2

        # ── Compute path ──────────────────────────────────────────────
        path = compute_route(start_x, start_y, dest_x, dest_y)

        return Response(path, status=status.HTTP_200_OK)

