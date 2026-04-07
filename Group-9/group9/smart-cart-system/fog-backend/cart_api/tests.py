from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from cart_api.models import BeaconZone, Customer, RetailerProfile, StoreZone, RoutePath

ENDPOINT = "/api/location/update/"


class LocationUpdateTests(APITestCase):
    """Tests for the /api/location/update/ endpoint (batched payload)."""

    def _make_payload(self, beacons=None, target_uuid="12345678-1234-1234-1234-123456789abc"):
        """Helper to build a valid batched payload."""
        if beacons is None:
            beacons = [
                {"major": 1, "minor": 1, "rssi": -55},
                {"major": 1, "minor": 2, "rssi": -68},
                {"major": 2, "minor": 1, "rssi": -72},
            ]
        return {"target_uuid": target_uuid, "beacons": beacons}

    # --- Happy-path ---

    def test_valid_batch_returns_201(self):
        """A well-formed 3-beacon batch should return HTTP 201."""
        payload = self._make_payload()
        response = self.client.post(ENDPOINT, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "received")
        self.assertEqual(response.data["beacon_count"], 3)

    def test_zone_resolved_from_db(self):
        """When a BeaconZone row matches the strongest beacon, the
        response should contain the correct aisle_zone."""
        BeaconZone.objects.create(major=1, minor=1, aisle_zone="Aisle 1 – Dairy")
        payload = self._make_payload()
        response = self.client.post(ENDPOINT, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["aisle_zone"], "Aisle 1 – Dairy")

    def test_unknown_zone_fallback(self):
        """When no BeaconZone row matches, aisle_zone should be 'unknown'."""
        payload = self._make_payload()
        response = self.client.post(ENDPOINT, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["aisle_zone"], "unknown")

    # --- Validation errors ---

    def test_empty_beacons_returns_400(self):
        """An empty beacons list should be rejected."""
        payload = self._make_payload(beacons=[])
        response = self.client.post(ENDPOINT, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_fields_returns_400(self):
        """A completely empty body should be rejected."""
        response = self.client.post(ENDPOINT, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AuthTests(APITestCase):
    """Tests for the authentication endpoints."""

    @classmethod
    def setUpTestData(cls):
        """Create a CEO user and a Customer for OTP tests."""
        cls.ceo_user = User.objects.create_user(
            username="testceo", password="ceopass123"
        )
        RetailerProfile.objects.create(user=cls.ceo_user, role="ceo")

        cls.manager_user = User.objects.create_user(
            username="testmanager", password="managerpass123"
        )
        RetailerProfile.objects.create(user=cls.manager_user, role="manager")

        cls.customer = Customer.objects.create(
            customer_id="CUST001",
            phone_number="9876543210",
            mobile_token="654321",
        )

    # ── Retailer Login ──

    def test_retailer_login_success(self):
        """Valid CEO credentials return 200 + tokens + role."""
        response = self.client.post(
            "/api/auth/retailer/login/",
            {"username": "testceo", "password": "ceopass123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["role"], "ceo")

    def test_retailer_login_bad_password(self):
        """Wrong password returns 401."""
        response = self.client.post(
            "/api/auth/retailer/login/",
            {"username": "testceo", "password": "wrongpass"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── Product list requires auth ──

    def test_product_list_unauthorized(self):
        """GET /api/products/ without token returns 401."""
        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_product_list_with_token(self):
        """GET /api/products/ with valid token returns 200."""
        login = self.client.post(
            "/api/auth/retailer/login/",
            {"username": "testceo", "password": "ceopass123"},
            format="json",
        )
        token = login.data["access"]
        response = self.client.get(
            "/api/products/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ── Manager CRUD (CEO only) ──

    def test_ceo_can_create_manager(self):
        """CEO can create a store manager via POST /api/auth/managers/."""
        login = self.client.post(
            "/api/auth/retailer/login/",
            {"username": "testceo", "password": "ceopass123"},
            format="json",
        )
        token = login.data["access"]
        response = self.client.post(
            "/api/auth/managers/",
            {"username": "newmanager", "password": "pass1234"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["role"], "manager")

    def test_manager_cannot_create_manager(self):
        """A store manager gets 403 when trying to create another manager."""
        login = self.client.post(
            "/api/auth/retailer/login/",
            {"username": "testmanager", "password": "managerpass123"},
            format="json",
        )
        token = login.data["access"]
        response = self.client.post(
            "/api/auth/managers/",
            {"username": "anotheruser", "password": "pass1234"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ── Shopper OTP ──

    def test_shopper_verify_otp_success(self):
        """Valid OTP returns 200 + tokens."""
        response = self.client.post(
            "/api/auth/shopper/verify-otp/",
            {"otp": "654321"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertEqual(response.data["customer_id"], "CUST001")

    def test_shopper_verify_otp_invalid(self):
        """Bad OTP returns 401."""
        response = self.client.post(
            "/api/auth/shopper/verify-otp/",
            {"otp": "000000"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class NavigationRouteTests(APITestCase):
    """Tests for the GET /api/navigation/route/ endpoint."""

    ENDPOINT = "/api/navigation/route/"

    @classmethod
    def setUpTestData(cls):
        """Create a destination zone and some route-path segments."""
        cls.zone = StoreZone.objects.create(
            name="Dairy",
            zone_type="aisle",
            x_min=0.7,
            y_min=0.7,
            x_max=0.9,
            y_max=0.9,
        )

    # ── Param validation ───────────────────────────────────────────────

    def test_missing_params_returns_400(self):
        """Omitting any required query param returns 400."""
        response = self.client.get(self.ENDPOINT, {"start_x": "0.1"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_zone_returns_404(self):
        """Non-existent dest_zone_id returns 404."""
        response = self.client.get(
            self.ENDPOINT,
            {"start_x": "0.1", "start_y": "0.1", "dest_zone_id": "99999"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ── Routing logic ──────────────────────────────────────────────────

    def test_no_routes_returns_straight_line(self):
        """With no RoutePaths, the path should be [start, dest]."""
        response = self.client.get(
            self.ENDPOINT,
            {
                "start_x": "0.1",
                "start_y": "0.1",
                "dest_zone_id": str(self.zone.pk),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        path = response.data
        self.assertEqual(len(path), 2)
        self.assertAlmostEqual(path[0]["x"], 0.1)
        self.assertAlmostEqual(path[-1]["x"], 0.8)  # zone centre

    def test_route_with_paths(self):
        """With RoutePath segments forming a network, the response
        should contain intermediate graph nodes."""
        # Build an L-shaped path:  (0.1, 0.1) ── (0.5, 0.1) ── (0.5, 0.8)
        RoutePath.objects.create(start_x=0.1, start_y=0.1, end_x=0.5, end_y=0.1)
        RoutePath.objects.create(start_x=0.5, start_y=0.1, end_x=0.5, end_y=0.8)

        response = self.client.get(
            self.ENDPOINT,
            {
                "start_x": "0.1",
                "start_y": "0.1",
                "dest_zone_id": str(self.zone.pk),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        path = response.data
        # start + at least 2 graph nodes + dest = ≥ 4 waypoints
        self.assertGreaterEqual(len(path), 4)
        # First and last are the original coordinates
        self.assertAlmostEqual(path[0]["x"], 0.1)
        self.assertAlmostEqual(path[0]["y"], 0.1)
        self.assertAlmostEqual(path[-1]["x"], 0.8)
        self.assertAlmostEqual(path[-1]["y"], 0.8)

