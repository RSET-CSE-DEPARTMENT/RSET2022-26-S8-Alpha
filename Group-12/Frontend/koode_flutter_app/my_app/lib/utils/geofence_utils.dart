import 'dart:math';
import 'package:latlong2/latlong.dart';

/// Utility functions for geofence calculations
class GeofenceUtils {
  /// Calculate distance between two points using Haversine formula
  /// Returns distance in meters
  static double distanceInMeters(LatLng point1, LatLng point2) {
    const earthRadiusMeters = 6371000.0;
    
    final lat1Rad = _toRadians(point1.latitude);
    final lat2Rad = _toRadians(point2.latitude);
    final deltaLat = _toRadians(point2.latitude - point1.latitude);
    final deltaLng = _toRadians(point2.longitude - point1.longitude);

    final a = sin(deltaLat / 2) * sin(deltaLat / 2) +
        cos(lat1Rad) * cos(lat2Rad) *
        sin(deltaLng / 2) * sin(deltaLng / 2);

    final c = 2 * atan2(sqrt(a), sqrt(1 - a));

    return earthRadiusMeters * c;
  }

  /// Check if a point is inside a circle fence
  /// Returns true if point is inside or on the boundary
  static bool isPointInCircle(
    LatLng point,
    LatLng center,
    double radiusMeters,
  ) {
    final distance = distanceInMeters(point, center);
    return distance <= radiusMeters;
  }

  /// Check if a point is inside a polygon using ray-casting algorithm
  /// Returns true if point is inside the polygon
  static bool isPointInPolygon(LatLng point, List<LatLng> polygon) {
    if (polygon.length < 3) return false;

    bool isInside = false;
    int j = polygon.length - 1;

    for (int i = 0; i < polygon.length; i++) {
      if ((polygon[i].latitude > point.latitude) !=
              (polygon[j].latitude > point.latitude) &&
          (point.longitude <
              (polygon[j].longitude - polygon[i].longitude) *
                      (point.latitude - polygon[i].latitude) /
                      (polygon[j].latitude - polygon[i].latitude) +
                  polygon[i].longitude)) {
        isInside = !isInside;
      }
      j = i;
    }

    return isInside;
  }

  /// Convert degrees to radians
  static double _toRadians(double degrees) {
    return degrees * pi / 180.0;
  }
}
