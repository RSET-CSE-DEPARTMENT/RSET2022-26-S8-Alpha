import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:geolocator/geolocator.dart';

import '../models/geofence_model.dart';
import '../services/api_service.dart';
import '../utils/geofence_utils.dart';

bool _isInsideSafeZone = true;

enum DrawMode { none, circle, polygon }

class GeofenceMapPage extends StatefulWidget {
  const GeofenceMapPage({super.key});

  @override
  State<GeofenceMapPage> createState() => _GeofenceMapPageState();
}

class _GeofenceMapPageState extends State<GeofenceMapPage> {
  final MapController _mapController = MapController();

  /// 🔥 REQUIRED to force map rebuild
  Key _mapKey = UniqueKey();

  DrawMode _mode = DrawMode.none;

  LatLng? _circleCenter;
  double _circleRadius = 150;
  final List<LatLng> _polygonPoints = [];

  LatLng? _userLocation; // caregiver
  LatLng? _espLocation; // patient

  List<GeofenceModel> _fences = [];
  Timer? _pollTimer;

  @override
  void initState() {
    super.initState();
    _loadUserLocation();
    _loadFences();
    _startPolling();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  // ================= LOCATION =================

  Future<void> _loadUserLocation() async {
    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) return;

    final pos = await Geolocator.getCurrentPosition();
    setState(() {
      _userLocation = LatLng(pos.latitude, pos.longitude);
    });

    _mapController.move(_userLocation!, 16);
  }

  void _startPolling() {
    _pollTimer = Timer.periodic(const Duration(seconds: 3), (_) async {
      final loc = await ApiService.getLatestLocation();
      final inside = await ApiService.isPatientInsideFence();

      if (loc != null && mounted) {
        setState(() {
          _espLocation = loc;
          _isInsideSafeZone = inside;
        });
      }
    });
  }

  // ================= GEOFENCE =================

  Future<void> _loadFences() async {
    final fences = await ApiService.getGeofences();
    if (!mounted) return;

    setState(() {
      _fences = fences;
      _mapKey = UniqueKey(); // 🔥 force redraw when fences load
    });
  }

  void _onMapTap(LatLng p) {
    if (_mode == DrawMode.circle) {
      setState(() => _circleCenter = p);
    } else if (_mode == DrawMode.polygon) {
      setState(() => _polygonPoints.add(p));
    }
  }

  Future<void> _saveFence() async {
    if (_mode == DrawMode.circle && _circleCenter != null) {
      await ApiService.saveCircleFence(
        _circleCenter!.latitude,
        _circleCenter!.longitude,
        _circleRadius,
      );
    }

    if (_mode == DrawMode.polygon && _polygonPoints.length >= 3) {
      await ApiService.savePolygonFence(_polygonPoints);
    }

    setState(() {
      _mode = DrawMode.none;
      _circleCenter = null;
      _polygonPoints.clear();
      _mapKey = UniqueKey(); // 💥 THIS makes fence appear instantly
    });

    await _loadFences();

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Geofence saved')),
    );
  }

  void _resetDrawing() {
    setState(() {
      _mode = DrawMode.none;
      _circleCenter = null;
      _polygonPoints.clear();
    });
  }

  // ================= UI =================

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Geofencing')),
      floatingActionButton: FloatingActionButton(
        onPressed: _showFenceOptions,
        child: const Icon(Icons.add),
      ),
      body: Stack(
        children: [
          FlutterMap(
            key: _mapKey, // 🔥 REQUIRED
            mapController: _mapController,
            options: MapOptions(
              initialCenter: _userLocation ?? const LatLng(9.93, 76.26),
              initialZoom: 15,
              onTap: (_, p) => _onMapTap(p),
            ),
            children: [
              TileLayer(
                urlTemplate:
                    'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              ),

              // ===== SAVED FENCES =====
              CircleLayer(
                circles: _fences
                    .where((f) => f.type == FenceType.circle)
                    .map((f) => CircleMarker(
                          point: LatLng(f.lat!, f.lng!),
                          radius: f.radius!,
                          useRadiusInMeter: true,
                          color: Colors.green.withOpacity(0.25),
                          borderColor: Colors.green,
                          borderStrokeWidth: 2,
                        ))
                    .toList(),
              ),

              PolygonLayer(
                polygons: _fences
                    .where((f) => f.type == FenceType.polygon)
                    .map((f) => Polygon(
                          points: f.points!,
                          color: Colors.green.withOpacity(0.25),
                          borderColor: Colors.green,
                          borderStrokeWidth: 2,
                        ))
                    .toList(),
              ),

              // ===== PREVIEW =====
              if (_circleCenter != null)
                CircleLayer(
                  circles: [
                    CircleMarker(
                      point: _circleCenter!,
                      radius: _circleRadius,
                      useRadiusInMeter: true,
                      color: Colors.blue.withOpacity(0.3),
                    )
                  ],
                ),

              if (_polygonPoints.isNotEmpty)
                PolygonLayer(
                  polygons: [
                    Polygon(
                      points: _polygonPoints,
                      color: Colors.blue.withOpacity(0.3),
                    )
                  ],
                ),

              // ===== MARKERS =====
              MarkerLayer(
                markers: [
                  if (_userLocation != null)
                    Marker(
                      point: _userLocation!,
                      width: 20,
                      height: 20,
                      child: const DecoratedBox(
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: Colors.blue,
                        ),
                      ),
                    ),
                  if (_espLocation != null)
                    Marker(
                      point: _espLocation!,
                      width: 40,
                      height: 40,
                      child: Icon(
                        Icons.location_on,
                        color:
                            _isInsideSafeZone ? Colors.green : Colors.red,
                        size: 40,
                      ),
                    ),
                ],
              ),
            ],
          ),

          if (_mode != DrawMode.none)
            Positioned(
              left: 12,
              right: 12,
              bottom: 12,
              child: Material(
                elevation: 8,
                borderRadius: BorderRadius.circular(16),
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (_mode == DrawMode.circle)
                        Slider(
                          min: 10,
                          max: 500,
                          value: _circleRadius,
                          onChanged: (v) =>
                              setState(() => _circleRadius = v),
                        ),
                      Row(
                        mainAxisAlignment:
                            MainAxisAlignment.spaceBetween,
                        children: [
                          TextButton(
                            onPressed: _resetDrawing,
                            child: const Text('Cancel'),
                          ),
                          ElevatedButton(
                            onPressed: _saveFence,
                            child: const Text('Save'),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  void _showFenceOptions() {
    showModalBottomSheet(
      context: context,
      builder: (_) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          ListTile(
            title: const Text('Circle Fence'),
            onTap: () {
              Navigator.pop(context);
              setState(() {
                _mode = DrawMode.circle;
                _circleCenter =
                    _userLocation ?? _mapController.camera.center;
              });
            },
          ),
          ListTile(
            title: const Text('Polygon Fence'),
            onTap: () {
              Navigator.pop(context);
              setState(() => _mode = DrawMode.polygon);
            },
          ),
        ],
      ),
    );
  }
}
