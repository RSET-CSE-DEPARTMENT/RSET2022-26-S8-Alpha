from django.urls import path

from .views import (
    CartStartView,
    LocationUpdateView,
    CartLocationRetrieveAPIView,
    ManagerDeleteView,
    ManagerListCreateView,
    ProductListView,
    ProductDetailView,
    RetailerLoginView,
    ShopperVerifyOtpView,
    CheckoutView,
    RecommendationView,
    StoreZoneListCreateAPIView,
    StoreZoneRetrieveUpdateDestroyAPIView,
    StoreConfigAPIView,
    StoreConfigClearAllView,
    LiveCartsAnalyticsView,
    RoutePathListCreateView,
    RoutePathRetrieveDestroyView,
    NavigationRouteView,
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # ── Auth ──
    path("auth/retailer/login/", RetailerLoginView.as_view(), name="retailer-login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/shopper/verify-otp/", ShopperVerifyOtpView.as_view(), name="shopper-verify-otp"),
    # ── Manager CRUD (CEO only) ──
    path("auth/managers/", ManagerListCreateView.as_view(), name="manager-list-create"),
    path("auth/managers/<int:pk>/", ManagerDeleteView.as_view(), name="manager-delete"),
    # ── Existing ──
    path("location/update/", LocationUpdateView.as_view(), name="location-update"),
    path("location/<str:target_uuid>/", CartLocationRetrieveAPIView.as_view(), name="location-detail"),
    path("products/", ProductListView.as_view(), name="product-list"),
    path("products/<str:product_id>/", ProductDetailView.as_view(), name="product-detail"),
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("recommend/", RecommendationView.as_view(), name="recommend"),
    path("zones/", StoreZoneListCreateAPIView.as_view(), name="zone-list-create"),
    path("zones/<int:pk>/", StoreZoneRetrieveUpdateDestroyAPIView.as_view(), name="zone-detail"),
    path("store-config/", StoreConfigAPIView.as_view(), name="store-config"),
    path("store-config/clear-all/", StoreConfigClearAllView.as_view(), name="store-config-clear-all"),
    path("analytics/live-carts/", LiveCartsAnalyticsView.as_view(), name="analytics-live-carts"),
    # ── Route Paths ──
    path("routes/", RoutePathListCreateView.as_view(), name="route-list-create"),
    path("routes/<int:pk>/", RoutePathRetrieveDestroyView.as_view(), name="route-detail"),
    # ── Navigation ──
    path("navigation/route/", NavigationRouteView.as_view(), name="navigation-route"),
    # ── Cart Session ──
    path("cart/start/", CartStartView.as_view(), name="cart-start"),
]
