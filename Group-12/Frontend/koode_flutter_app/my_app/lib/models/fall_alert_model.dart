import 'package:cloud_firestore/cloud_firestore.dart';

class FallAlert {
  final String id;
  final String deviceId;
  final String userId;
  final double confidence;
  final bool isFall;
  final DateTime timestamp;
  final bool acknowledged;
  final DateTime? acknowledgedAt;
  final List<String> reasoning;

  FallAlert({
    required this.id,
    required this.deviceId,
    required this.userId,
    required this.confidence,
    required this.isFall,
    required this.timestamp,
    this.acknowledged = false,
    this.acknowledgedAt,
    this.reasoning = const [],
  });

  /// Convert FallAlert to JSON for API requests
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'deviceId': deviceId,
      'userId': userId,
      'confidence': confidence,
      'isFall': isFall,
      'timestamp': timestamp.toIso8601String(),
      'acknowledged': acknowledged,
      'acknowledgedAt': acknowledgedAt?.toIso8601String(),
      'reasoning': reasoning,
    };
  }

  /// Create FallAlert from Firestore document
  factory FallAlert.fromFirestore(DocumentSnapshot doc) {
    final data = doc.data() as Map<String, dynamic>;
    return FallAlert(
      id: doc.id,
      deviceId: data['deviceId'] as String? ?? '',
      userId: data['userId'] as String? ?? '',
      confidence: (data['confidence'] as num?)?.toDouble() ?? 0.0,
      isFall: data['isFall'] as bool? ?? false,
      timestamp: (data['timestamp'] as Timestamp?)?.toDate() ?? DateTime.now(),
      acknowledged: data['acknowledged'] as bool? ?? false,
      acknowledgedAt: (data['acknowledgedAt'] as Timestamp?)?.toDate(),
      reasoning: List<String>.from(data['reasoning'] as List? ?? []),
    );
  }

  /// Create FallAlert from JSON (API response)
  factory FallAlert.fromJson(Map<String, dynamic> json) {
    return FallAlert(
      id: json['id'] as String? ?? '',
      deviceId: json['deviceId'] as String? ?? '',
      userId: json['userId'] as String? ?? '',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      isFall: json['isFall'] as bool? ?? false,
      timestamp: json['timestamp'] != null
          ? DateTime.parse(json['timestamp'] as String)
          : DateTime.now(),
      acknowledged: json['acknowledged'] as bool? ?? false,
      acknowledgedAt: json['acknowledgedAt'] != null
          ? DateTime.parse(json['acknowledgedAt'] as String)
          : null,
      reasoning: List<String>.from(json['reasoning'] as List? ?? []),
    );
  }

  /// Convert to Firestore document format
  Map<String, dynamic> toFirestore() {
    return {
      'deviceId': deviceId,
      'userId': userId,
      'confidence': confidence,
      'isFall': isFall,
      'timestamp': Timestamp.fromDate(timestamp),
      'acknowledged': acknowledged,
      'acknowledgedAt': acknowledgedAt != null ? Timestamp.fromDate(acknowledgedAt!) : null,
      'reasoning': reasoning,
    };
  }

  /// Create a copy with modified fields
  FallAlert copyWith({
    String? id,
    String? deviceId,
    String? userId,
    double? confidence,
    bool? isFall,
    DateTime? timestamp,
    bool? acknowledged,
    DateTime? acknowledgedAt,
    List<String>? reasoning,
  }) {
    return FallAlert(
      id: id ?? this.id,
      deviceId: deviceId ?? this.deviceId,
      userId: userId ?? this.userId,
      confidence: confidence ?? this.confidence,
      isFall: isFall ?? this.isFall,
      timestamp: timestamp ?? this.timestamp,
      acknowledged: acknowledged ?? this.acknowledged,
      acknowledgedAt: acknowledgedAt ?? this.acknowledgedAt,
      reasoning: reasoning ?? this.reasoning,
    );
  }

  /// Get confidence as percentage string
  String getConfidencePercentage() {
    return '${(confidence * 100).toStringAsFixed(1)}%';
  }

  /// Get user-friendly timestamp
  String getFormattedTime() {
    final now = DateTime.now();
    final difference = now.difference(timestamp);

    if (difference.inSeconds < 60) {
      return 'just now';
    } else if (difference.inMinutes < 60) {
      return '${difference.inMinutes} minute${difference.inMinutes > 1 ? 's' : ''} ago';
    } else if (difference.inHours < 24) {
      return '${difference.inHours} hour${difference.inHours > 1 ? 's' : ''} ago';
    } else {
      return '${difference.inDays} day${difference.inDays > 1 ? 's' : ''} ago';
    }
  }

  /// Get alert status string
  String getStatus() {
    if (acknowledged) {
      return 'Acknowledged';
    } else if (isFall) {
      return 'Unacknowledged - Fall Detected';
    } else {
      return 'No Fall';
    }
  }

  @override
  String toString() {
    return 'FallAlert(id: $id, device: $deviceId, confidence: ${getConfidencePercentage()}, acknowledged: $acknowledged)';
  }
}
