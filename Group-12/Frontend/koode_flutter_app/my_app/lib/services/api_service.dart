import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../models/geofence_model.dart';
import '../models/fall_alert_model.dart';

class ApiService {
  // ✅ MUST include http:// and port
  static const String baseUrl = 'http://172.20.10.3:5000';
  static const String notificationDocId = 'OaHeJSTziygJ8JWkepyG';
  static const String gpsTrackerApiKey = 'AIzaSyDvQn1XUafNwy6a2QB7DxEQCnM5wGZApLU';
  static const String gpsTrackerProjectId = 'alzheimers-alert';
  static const String gpsTrackerDeviceId = 'test-device';
  static const String gpsTrackerLocationDocId = 'test-doc';

  static final FirebaseFirestore _firestore = FirebaseFirestore.instance;
  static CollectionReference<Map<String, dynamic>> get _notificationLogsRef =>
      _firestore
          .collection('notification')
          .doc(notificationDocId)
          .collection('logs');
  static CollectionReference<Map<String, dynamic>> get _geofencesRef =>
      _firestore.collection('geofences');

  /// Acknowledge a fall alert
  static Future<bool> acknowledgeFallAlert(String alertId) async {
    try {
      await _notificationLogsRef
          .doc(alertId)
          .update({
        'acknowledged': true,
        'acknowledgedAt': Timestamp.now(),
      });
      return true;
    } catch (e) {
      print('Error acknowledging alert: $e');
      return false;
    }
  }

  // ================== GEOFENCES ==================

  static Future<bool> isPatientInsideFence() async {
    try {
      final res =
          await http.get(Uri.parse('$baseUrl/geofence/status'));

      if (res.statusCode != 200) return true;

      final data = jsonDecode(res.body);
      return data['inside'] == true;
    } catch (e) {
      return true; // fail-safe
    }
  }

  static Future<List<GeofenceModel>> getGeofences() async {
    try {
      final userId = FirebaseAuth.instance.currentUser?.uid;
      if (userId == null) return [];

      final snap = await _geofencesRef
          .where('userId', isEqualTo: userId)
          .get();

      final geofences = snap.docs.map((doc) {
        final data = doc.data();
        final typeRaw = (data['type'] ?? 'circle').toString();
        final pointsRaw = data['points'];
        final points = pointsRaw is List
            ? pointsRaw
                .whereType<Map>()
                .map(
                  (p) => LatLng(
                    (p['lat'] as num).toDouble(),
                    (p['lng'] as num).toDouble(),
                  ),
                )
                .toList()
            : null;

        return GeofenceModel(
          id: doc.id,
          type: typeRaw == 'polygon' ? FenceType.polygon : FenceType.circle,
          lat: (data['lat'] as num?)?.toDouble(),
          lng: (data['lng'] as num?)?.toDouble(),
          radius: (data['radius'] as num?)?.toDouble(),
          points: points,
        );
      }).toList();
      geofences.sort((a, b) => b.id.compareTo(a.id));
      return geofences;
    } catch (e) {
      print('Error fetching geofences: $e');
      return [];
    }
  }

  static Future<void> sendGeofenceAlert() async {
    await http.post(
      Uri.parse('$baseUrl/geofence-alert'),
    );
  }

  static Future<void> saveCircleFence(
      double lat, double lng, double radius) async {
    final userId = FirebaseAuth.instance.currentUser?.uid;
    if (userId == null) return;

    await _geofencesRef.add({
      'userId': userId,
      'type': 'circle',
      'lat': lat,
      'lng': lng,
      'radius': radius,
      'createdAt': FieldValue.serverTimestamp(),
    });
  }

  static Future<void> savePolygonFence(
      List<LatLng> points) async {
    final userId = FirebaseAuth.instance.currentUser?.uid;
    if (userId == null) return;

    await _geofencesRef.add({
      'userId': userId,
      'type': 'polygon',
      'points': points
          .map((p) => {'lat': p.latitude, 'lng': p.longitude})
          .toList(),
      'createdAt': FieldValue.serverTimestamp(),
    });
  }

  static Future<void> deleteGeofence(String geofenceId) async {
    await _geofencesRef.doc(geofenceId).delete();
  }

  // ================== KNOWN SPEAKERS ==================

  static Future<List<String>> getKnownSpeakers() async {
    try {
      final userId = FirebaseAuth.instance.currentUser?.uid;
      final uri = Uri.parse('$baseUrl/known-speakers').replace(
        queryParameters: userId == null ? null : {'userId': userId},
      );
      final res = await http.get(uri);
      if (res.statusCode != 200) return [];

      final data = jsonDecode(res.body) as Map<String, dynamic>;
      final speakers = data['speakers'] as List?;
      if (speakers == null) return [];

      return speakers.map((e) => e.toString()).toList();
    } catch (e) {
      print('Error fetching known speakers: $e');
      return [];
    }
  }

  static String normalizeMemberKey(String name) {
    final lowered = name.trim().toLowerCase();
    return lowered.replaceAll(RegExp(r'[^a-z0-9]+'), '-').replaceAll(
          RegExp(r'^-+|-+$'),
          '',
        );
  }

  static Future<void> saveMemberProfile({
    required String name,
    required String description,
    required String source,
  }) async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      throw StateError('User must be logged in to save a member.');
    }

    final normalized = normalizeMemberKey(name);
    if (normalized.isEmpty) {
      throw StateError('Member name is required.');
    }

    final response = await http.post(
      Uri.parse('$baseUrl/members/profile'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'userId': user.uid,
        'name': name.trim(),
        'description': description.trim(),
        'source': source,
      }),
    );

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw StateError('Failed to save member profile: ${response.body}');
    }
  }

  static Future<bool> enrollMemberFromPhone({
    required File audioFile,
    required String memberName,
    required String description,
  }) async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return false;

    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/members/enroll'),
      )
        ..fields['userId'] = user.uid
        ..fields['memberName'] = memberName.trim()
        ..fields['description'] = description.trim()
        ..fields['source'] = 'phone'
        ..files.add(
          await http.MultipartFile.fromPath('audio', audioFile.path),
        );

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);
      if (response.statusCode < 200 || response.statusCode >= 300) {
        print('Error enrolling member from phone: ${response.body}');
        return false;
      }

      return true;
    } catch (e) {
      print('Error enrolling member from phone: $e');
      return false;
    }
  }

  static Future<bool> startIotMemberEnrollment({
    required String memberName,
  }) async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return false;

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/members/enroll/iot/start'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'userId': user.uid,
          'memberName': memberName.trim(),
        }),
      );
      return response.statusCode >= 200 && response.statusCode < 300;
    } catch (e) {
      print('Error starting IoT enrollment: $e');
      return false;
    }
  }

  static Future<Map<String, dynamic>?> getIotMemberEnrollmentStatus() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return null;

    try {
      final uri = Uri.parse('$baseUrl/members/enroll/iot/status').replace(
        queryParameters: {'userId': user.uid},
      );
      final response = await http.get(uri);
      if (response.statusCode != 200) return null;
      return jsonDecode(response.body) as Map<String, dynamic>;
    } catch (e) {
      print('Error checking IoT enrollment status: $e');
      return null;
    }
  }

  static Future<bool> completeIotMemberEnrollment({
    required String memberName,
    required String description,
  }) async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return false;

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/members/enroll/iot/complete'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'userId': user.uid,
          'memberName': memberName.trim(),
          'description': description.trim(),
          'source': 'iot',
        }),
      );
      if (response.statusCode < 200 || response.statusCode >= 300) {
        print('Error completing IoT enrollment: ${response.body}');
        return false;
      }
      return true;
    } catch (e) {
      print('Error completing IoT enrollment: $e');
      return false;
    }
  }

  // ================== LOCATION ==================
  // ✅ MATCHES FLASK BACKEND

  static Future<LatLng?> getLatestLocation() async {
    try {
      final uri = Uri.https(
        'firestore.googleapis.com',
        '/v1/projects/$gpsTrackerProjectId/databases/(default)/documents/devices/$gpsTrackerDeviceId/location/$gpsTrackerLocationDocId',
        {'key': gpsTrackerApiKey},
      );
      final res = await http.get(uri);
      if (res.statusCode != 200) return null;

      final data = jsonDecode(res.body) as Map<String, dynamic>;
      final fields = (data['fields'] as Map<String, dynamic>?);
      if (fields == null) return null;

      final lat = _parseFirestoreNumber(fields['latitude']);
      final lon = _parseFirestoreNumber(fields['longitude']);
      if (lat == null || lon == null) return null;

      return LatLng(lat, lon);
    } catch (e) {
      print('❌ Error fetching GPS: $e');
      return null;
    }
  }

  static double? _parseFirestoreNumber(dynamic value) {
    if (value is! Map<String, dynamic>) return null;
    if (value['doubleValue'] != null) {
      return (value['doubleValue'] as num).toDouble();
    }
    if (value['integerValue'] != null) {
      return double.tryParse(value['integerValue'].toString());
    }
    return null;
  }

  // ================== SENSOR READINGS ==================

  static Future<bool> sendSensorReadings({
    required String deviceId,
    required String userId,
    required double gyroX,
    required double gyroY,
    required double gyroZ,
    required double accelX,
    required double accelY,
    required double accelZ,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/sensor-readings'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'deviceId': deviceId,
          'userId': userId,
          'gyroX': gyroX,
          'gyroY': gyroY,
          'gyroZ': gyroZ,
          'accelX': accelX,
          'accelY': accelY,
          'accelZ': accelZ,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['status'] == 'success';
      }
      return false;
    } catch (e) {
      print('Error sending sensor readings: $e');
      return false;
    }
  }

  // ================== FALL DETECTION ==================

  static Future<Map<String, dynamic>?> predictFallSingle({
    required String deviceId,
    required String userId,
    required double gyroX,
    required double gyroY,
    required double gyroZ,
    required double accelX,
    required double accelY,
    required double accelZ,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/predict-fall'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'deviceId': deviceId,
          'userId': userId,
          'gyroX': gyroX,
          'gyroY': gyroY,
          'gyroZ': gyroZ,
          'accelX': accelX,
          'accelY': accelY,
          'accelZ': accelZ,
        }),
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body)
            as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      print('Error predicting fall: $e');
      return null;
    }
  }

  static Future<Map<String, dynamic>?> predictFallBatch({
    required String deviceId,
    required String userId,
    required List<Map<String, double>> readings,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/predict-fall'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'deviceId': deviceId,
          'userId': userId,
          'readings': readings,
        }),
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body)
            as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      print('Error predicting fall (batch): $e');
      return null;
    }
  }

  // ================== FALL ALERTS (Firestore) ==================

  static Future<List<FallAlert>> getFallAlerts(
      String userId) async {
    try {
      final snapshot = await _firestore
          .collection('fall_alerts')
          .where('userId', isEqualTo: userId)
          .orderBy('timestamp', descending: true)
          .get();

      return snapshot.docs
          .map((doc) =>
              FallAlert.fromFirestore(doc))
          .toList();
    } catch (e) {
      print('Error getting fall alerts: $e');
      return [];
    }
  }

  static Stream<List<FallAlert>> streamFallAlerts(String userId) {
    return _notificationLogsRef
        .where('alertType', isEqualTo: 'fall')
        .snapshots()
        .map((snapshot) {
          final alerts = snapshot.docs
              .where((doc) {
                final ownerId = (doc.data()['userId'] ?? '').toString().trim();
                // include legacy logs with missing userId
                return ownerId.isEmpty || ownerId == userId;
              })
              .map((doc) => _fallAlertFromNotificationLog(doc))
              .toList();
          alerts.sort((a, b) => b.timestamp.compareTo(a.timestamp));
          return alerts;
        });
  }

  static Future<bool> deleteFallAlert(
      String alertId) async {
    try {
      await _notificationLogsRef
          .doc(alertId)
          .delete();
      return true;
    } catch (e) {
      print('Error deleting alert: $e');
      return false;
    }
  }

  static FallAlert _fallAlertFromNotificationLog(
      DocumentSnapshot<Map<String, dynamic>> doc) {
    final data = doc.data() ?? {};
    final nestedData = data['data'];
    final payload = nestedData is Map
        ? Map<String, dynamic>.from(nestedData)
        : <String, dynamic>{};

    final alertType = (data['alertType'] ??
            payload['alertType'] ??
            payload['type'] ??
            '')
        .toString()
        .toLowerCase();

    final timestamp = (data['receivedAt'] as Timestamp?) ??
        (data['sentTime'] as Timestamp?) ??
        (data['timestamp'] as Timestamp?);

    return FallAlert(
      id: doc.id,
      deviceId:
          (payload['deviceId'] ?? data['deviceId'] ?? 'notification_log')
              .toString(),
      userId:
          (data['firebaseUid'] ?? payload['userId'] ?? data['userId'] ?? '')
              .toString(),
      confidence: alertType == 'fall' ? 1.0 : 0.0,
      isFall: alertType == 'fall',
      timestamp: timestamp?.toDate() ?? DateTime.now(),
      acknowledged: data['acknowledged'] as bool? ?? false,
      acknowledgedAt: (data['acknowledgedAt'] as Timestamp?)?.toDate(),
      reasoning: <String>[
        if ((data['deliveryEvent'] ?? '').toString().isNotEmpty)
          'Delivery event: ${data['deliveryEvent']}',
        if ((data['title'] ?? '').toString().isNotEmpty)
          'Title: ${data['title']}',
        if ((data['body'] ?? '').toString().isNotEmpty)
          'Body: ${data['body']}',
      ],
    );
  }
}
