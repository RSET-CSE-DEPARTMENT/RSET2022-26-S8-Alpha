import 'dart:async';
import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:geolocator/geolocator.dart';

import 'models/geofence_model.dart';
import 'services/api_service.dart';
import 'utils/geofence_utils.dart';

enum DrawMode { none, drawCircle }

class GpsPage extends StatefulWidget {
  const GpsPage({super.key});

  @override
  State<GpsPage> createState() => _GpsPageState();
}

class _GpsPageState extends State<GpsPage> {
  final MapController _mapController = MapController();
  final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();

  DrawMode _mode = DrawMode.none;

  LatLng? _circleCenter;
  double _circleRadius = 5;

  LatLng? _patientLocation;
  LatLng? _caregiverLocation;

  List<GeofenceModel> _fences = [];

  bool _isViolated = false;
  bool _lastViolationState = false;

  Timer? _pollTimer;
  StreamSubscription<Position>? _caregiverLocationSub;
  bool _mapReady = false;

  @override
  void initState() {
    super.initState();
    _initLocalNotifications();
    _startCaregiverLocationTracking();
    _loadFences();
    _startPolling();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _caregiverLocationSub?.cancel();
    super.dispose();
  }

  Future<void> _initLocalNotifications() async {
    const settings = InitializationSettings(
      android: AndroidInitializationSettings('@mipmap/ic_launcher'),
    );
    await _localNotifications.initialize(settings);
  }

  Future<void> _startCaregiverLocationTracking() async {
    var permission = await Geolocator.checkPermission();

    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      permission = await Geolocator.requestPermission();
    }

    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      return;
    }

    final pos = await Geolocator.getCurrentPosition();
    if (!mounted) return;

    final caregiver = LatLng(pos.latitude, pos.longitude);
    setState(() => _caregiverLocation = caregiver);
    _centerMapOnCaregiver(caregiver);

    _caregiverLocationSub = Geolocator.getPositionStream(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.high,
        distanceFilter: 5,
      ),
    ).listen((position) {
      if (!mounted) return;
      final updated = LatLng(position.latitude, position.longitude);
      setState(() => _caregiverLocation = updated);
      _centerMapOnCaregiver(updated);
    });
  }

  void _centerMapOnCaregiver(LatLng caregiverLocation) {
    if (!_mapReady) return;
    final zoom = _mapController.camera.zoom;
    _mapController.move(caregiverLocation, zoom.isFinite ? zoom : 17);
  }

  Future<void> _loadFences() async {
    final fences = await ApiService.getGeofences();
    if (!mounted) return;
    setState(() => _fences = fences.where((f) => f.type == FenceType.circle).toList());
  }

  void _startPolling() {
    _pollTimer = Timer.periodic(
      const Duration(seconds: 3),
      (_) async {
        final loc = await ApiService.getLatestLocation();
        if (loc != null && mounted) {
          setState(() {
            _patientLocation = loc;
            _checkViolations();
          });
        }
      },
    );
  }

  void _checkViolations() {
    if (_patientLocation == null || _fences.isEmpty) {
      _isViolated = false;
      _lastViolationState = false;
      return;
    }

    var anyInside = false;

    for (final fence in _fences) {
      final isInside = GeofenceUtils.isPointInCircle(
        _patientLocation!,
        LatLng(fence.lat!, fence.lng!),
        fence.radius!,
      );

      fence.status = isInside ? FenceStatus.inside : FenceStatus.outside;
      if (isInside) anyInside = true;
    }

    _isViolated = !anyInside;
    if (_isViolated && !_lastViolationState) {
      _handleBoundaryCrossed();
    }
    _lastViolationState = _isViolated;
  }

  void _onMapTap(LatLng point) {
    if (_mode != DrawMode.drawCircle) return;
    setState(() => _circleCenter = point);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('GPS Tracking'),
        actions: [
          if (_fences.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.delete_outline),
              tooltip: 'Remove Fence',
              onPressed: _removeFence,
            ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _showAddFenceSheet,
        child: const Icon(Icons.add),
      ),
      body: Stack(
        children: [
          FlutterMap(
            mapController: _mapController,
            options: MapOptions(
              initialCenter: _caregiverLocation ?? const LatLng(9.931233, 76.267303),
              initialZoom: 15,
              onTap: _mode != DrawMode.none ? (_, point) => _onMapTap(point) : null,
              onMapReady: () {
                _mapReady = true;
                if (_caregiverLocation != null) {
                  _centerMapOnCaregiver(_caregiverLocation!);
                }
              },
            ),
            children: [
              TileLayer(
                urlTemplate: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
                subdomains: const ['a', 'b', 'c'],
                userAgentPackageName: 'com.koode.app',
              ),

              CircleLayer(
                circles: _fences.map((f) {
                  final violated = f.status == FenceStatus.outside;
                  final color = violated ? Colors.red : Colors.green;
                  return CircleMarker(
                    point: LatLng(f.lat!, f.lng!),
                    radius: f.radius!,
                    useRadiusInMeter: true,
                    color: color.withValues(alpha: 0.25),
                    borderColor: color,
                    borderStrokeWidth: 2,
                  );
                }).toList(),
              ),

              if (_circleCenter != null)
                CircleLayer(
                  circles: [
                    CircleMarker(
                      point: _circleCenter!,
                      radius: _circleRadius,
                      useRadiusInMeter: true,
                      color: Colors.blue.withValues(alpha: 0.3),
                      borderColor: Colors.blue,
                      borderStrokeWidth: 2,
                    ),
                  ],
                ),

              if (_caregiverLocation != null)
                MarkerLayer(
                  markers: [
                    Marker(
                      point: _caregiverLocation!,
                      width: 30,
                      height: 30,
                      child: const Icon(
                        Icons.person_pin_circle,
                        color: Colors.red,
                        size: 30,
                      ),
                    ),
                  ],
                ),

              if (_patientLocation != null)
                MarkerLayer(
                  markers: [
                    Marker(
                      point: _patientLocation!,
                      width: 24,
                      height: 24,
                      child: Container(
                        width: 16,
                        height: 16,
                        decoration: BoxDecoration(
                          color: Colors.blue,
                          shape: BoxShape.circle,
                          border: Border.all(color: Colors.white, width: 2),
                        ),
                      ),
                    ),
                  ],
                ),
            ],
          ),

          if (_mode != DrawMode.none) _buildBottomControls(),
        ],
      ),
    );
  }

  void _showAddFenceSheet() {
    showModalBottomSheet(
      context: context,
      builder: (_) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          ListTile(
            leading: const Icon(Icons.radio_button_checked),
            title: const Text('Circle Fence'),
            onTap: () {
              Navigator.pop(context);
              setState(() {
                _reset();
                _mode = DrawMode.drawCircle;
              });
            },
          ),
        ],
      ),
    );
  }

  Widget _buildBottomControls() {
    return Positioned(
      left: 0,
      right: 0,
      bottom: 0,
      child: Card(
        margin: EdgeInsets.zero,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('Tap map to set center'),
              Slider(
                min: 5,
                max: 500,
                value: _circleRadius,
                label: '${_circleRadius.toInt()} m',
                onChanged: (v) => setState(() => _circleRadius = v),
              ),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  TextButton(
                    onPressed: _reset,
                    child: const Text('Cancel'),
                  ),
                  ElevatedButton(
                    onPressed: _canConfirm() ? _confirmFence : null,
                    child: const Text('Confirm'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  bool _canConfirm() => _mode == DrawMode.drawCircle && _circleCenter != null;

  Future<void> _confirmFence() async {
    if (_circleCenter != null) {
      await ApiService.saveCircleFence(
        _circleCenter!.latitude,
        _circleCenter!.longitude,
        _circleRadius,
      );
    }

    _reset();
    await _loadFences();

    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Geofence saved')),
    );
  }

  Future<void> _removeFence() async {
    if (_fences.isEmpty) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Remove Fence'),
        content: const Text('Do you want to remove the saved boundary?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Remove'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      for (final fence in _fences) {
        await ApiService.deleteGeofence(fence.id);
      }
      await _loadFences();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Geofence removed')),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Failed to remove geofence')),
      );
    }
  }

  void _reset() {
    setState(() {
      _mode = DrawMode.none;
      _circleCenter = null;
      _circleRadius = 5;
    });
  }

  void _showBoundaryCrossedAlert() {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Geofence crossed: patient is outside boundary'),
        backgroundColor: Colors.red,
      ),
    );
  }

  Future<void> _handleBoundaryCrossed() async {
    _showBoundaryCrossedAlert();
    await _showBoundaryCrossedLocalNotification();
    await _logGeofenceCross();
    try {
      await ApiService.sendGeofenceAlert();
    } catch (_) {
      // backend endpoint may be unavailable
    }
  }

  Future<void> _showBoundaryCrossedLocalNotification() async {
    const details = NotificationDetails(
      android: AndroidNotificationDetails(
        'high_importance_channel',
        'High Importance Notifications',
        importance: Importance.high,
        priority: Priority.high,
      ),
    );

    await _localNotifications.show(
      DateTime.now().millisecondsSinceEpoch.remainder(100000),
      'Geofence Alert',
      'Patient exited safe zone',
      details,
    );
  }

  Future<void> _logGeofenceCross() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null || user.isAnonymous) return;

    try {
      await FirebaseFirestore.instance
          .collection('notification')
          .doc(ApiService.notificationDocId)
          .collection('logs')
          .add({
        'alertType': 'geofence',
        'deliveryEvent': 'crossed_in_gps_page',
        'title': 'Geofence Alert',
        'body': 'Patient exited safe zone',
        'userId': user.uid,
        'firebaseUid': user.uid,
        'lat': _patientLocation?.latitude,
        'lon': _patientLocation?.longitude,
        'receivedAt': FieldValue.serverTimestamp(),
        'platform': 'flutter_app',
      });
    } catch (e) {
      debugPrint('Error logging geofence crossing: $e');
    }
  }
}
