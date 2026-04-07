import 'package:latlong2/latlong.dart';

enum FenceType { circle, polygon }
enum FenceStatus { inside, outside } // 👈 ADD

class GeofenceModel {
  final String id;
  final FenceType type;

  final double? lat;
  final double? lng;
  final double? radius;

  final List<LatLng>? points;

  FenceStatus status; // 👈 MUTABLE STATE

  GeofenceModel({
    required this.id,
    required this.type,
    this.lat,
    this.lng,
    this.radius,
    this.points,
    this.status = FenceStatus.inside, // default
  });

  factory GeofenceModel.fromJson(Map<String, dynamic> json) {
    return GeofenceModel(
      id: json['id'],
      type: json['type'] == 'circle'
          ? FenceType.circle
          : FenceType.polygon,
      lat: json['lat']?.toDouble(),
      lng: json['lng']?.toDouble(),
      radius: json['radius']?.toDouble(),
      points: json['points'] != null
          ? (json['points'] as List)
              .map((p) => LatLng(
                    p['lat'].toDouble(),
                    p['lng'].toDouble(),
                  ))
              .toList()
          : null,
      status: FenceStatus.inside, // backend is source of truth later
    );
  }
}
