class DeviceLocation {
  final double latitude;
  final double longitude;
  final String deviceId;

  DeviceLocation({
    required this.latitude,
    required this.longitude,
    required this.deviceId,
  });

  Map<String, dynamic> toJson() {
    return {
      'latitude': latitude,
      'longitude': longitude,
      'deviceId': deviceId,
    };
  }
}
