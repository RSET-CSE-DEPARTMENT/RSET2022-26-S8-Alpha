import 'dart:math';

enum GeofenceStatus {
  inside,
  outside,
}

class GeofenceService {
  final double centerLat;
  final double centerLng;
  final double radiusMeters;

  GeofenceService({
    required this.centerLat,
    required this.centerLng,
    required this.radiusMeters,
  });

  double _toRad(double deg) => deg * pi / 180;

  double _distanceMeters(
    double lat1,
    double lon1,
    double lat2,
    double lon2,
  ) {
    const r = 6371000;
    final dLat = _toRad(lat2 - lat1);
    final dLon = _toRad(lon2 - lon1);

    final a = sin(dLat / 2) * sin(dLat / 2) +
        cos(_toRad(lat1)) *
            cos(_toRad(lat2)) *
            sin(dLon / 2) *
            sin(dLon / 2);

    return 2 * r * atan2(sqrt(a), sqrt(1 - a));
  }

  GeofenceStatus check(
    double deviceLat,
    double deviceLng,
  ) {
    final distance = _distanceMeters(
      deviceLat,
      deviceLng,
      centerLat,
      centerLng,
    );

    return distance <= radiusMeters
        ? GeofenceStatus.inside
        : GeofenceStatus.outside;
  }
}
