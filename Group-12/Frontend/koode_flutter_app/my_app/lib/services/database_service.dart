import 'package:cloud_firestore/cloud_firestore.dart';

class DatabaseService {
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;
  CollectionReference<Map<String, dynamic>> get _eventsRef =>
      _firestore.collection('schedule_events');
  CollectionReference<Map<String, dynamic>> get _medicationsRef =>
      _firestore.collection('schedule_medications');

  String _dateKey(DateTime date) =>
      '${date.year.toString().padLeft(4, '0')}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';

  // Events methods
  Future<List<Map<String, dynamic>>> getEvents(String userId, DateTime date) async {
    try {
      final snap = await _eventsRef
          .where('userId', isEqualTo: userId)
          .get();

      final targetDate = _dateKey(date);
      final items = snap.docs
          .where((doc) {
            final data = doc.data();
            return (data['dateKey'] ?? '') == targetDate;
          })
          .map((doc) {
            final data = doc.data();
            return <String, dynamic>{
              'id': doc.id,
              'title': data['title'] ?? '',
              'description': data['description'] ?? '',
              'time': data['time'] ?? '',
              'date': data['dateKey'] ?? '',
              'created_at': data['createdAt'],
            };
          })
          .toList();
      items.sort((a, b) => ((a['time'] ?? '') as String).compareTo((b['time'] ?? '') as String));
      return items;
    } catch (e) {
      throw Exception('Failed to load events: $e');
    }
  }

  Future<void> addEvent({
    required String userId,
    required String title,
    required String description,
    required String time,
    required DateTime date,
  }) async {
    try {
      await _eventsRef.add({
        'userId': userId,
        'firebaseUid': userId,
        'title': title,
        'description': description,
        'time': time,
        'dateKey': _dateKey(date),
        'createdAt': FieldValue.serverTimestamp(),
      });
    } catch (e) {
      throw Exception('Failed to add event: $e');
    }
  }

  Future<void> updateEvent({
    required String eventId,
    String? title,
    String? description,
    String? time,
    DateTime? date,
  }) async {
    try {
      final Map<String, dynamic> updates = {};
      
      if (title != null) updates['title'] = title;
      if (description != null) updates['description'] = description;
      if (time != null) updates['time'] = time;
      if (date != null) updates['dateKey'] = _dateKey(date);

      updates['updatedAt'] = FieldValue.serverTimestamp();

      await _eventsRef.doc(eventId).update(updates);
    } catch (e) {
      throw Exception('Failed to update event: $e');
    }
  }

  Future<void> deleteEvent(String eventId) async {
    try {
      await _eventsRef.doc(eventId).delete();
    } catch (e) {
      throw Exception('Failed to delete event: $e');
    }
  }

  // Medications methods
  Future<List<Map<String, dynamic>>> getMedications(String userId, DateTime date) async {
    try {
      final snap = await _medicationsRef
          .where('userId', isEqualTo: userId)
          .get();

      final selected = DateTime(date.year, date.month, date.day);
      final items = <Map<String, dynamic>>[];

      for (final doc in snap.docs) {
        final data = doc.data();
        final startRaw = (data['startDate'] ?? data['dateKey'])?.toString();
        if (startRaw == null || startRaw.isEmpty) continue;
        final start = DateTime.tryParse(startRaw);
        if (start == null) continue;

        final endRaw = data['endDate']?.toString();
        final daysRaw = data['numberOfDays'];
        DateTime? end;

        if (endRaw != null && endRaw.isNotEmpty) {
          end = DateTime.tryParse(endRaw);
        } else if (daysRaw is num && daysRaw > 0) {
          end = start.add(Duration(days: daysRaw.toInt() - 1));
        }

        final normalizedStart = DateTime(start.year, start.month, start.day);
        final normalizedEnd = end == null
            ? normalizedStart
            : DateTime(end.year, end.month, end.day);

        final active = !selected.isBefore(normalizedStart) &&
            !selected.isAfter(normalizedEnd);
        if (!active) continue;

        final timingsRaw = data['timings'];
        final timings = timingsRaw is List
            ? timingsRaw.map((e) => e.toString()).toList()
            : <String>[];

        items.add(<String, dynamic>{
          'id': doc.id,
          'name': data['name'] ?? '',
          'dosage': data['dosage'] ?? '',
          'time': data['time'] ?? '',
          'timings': timings,
          'timing': (data['timing'] ?? ''),
          'startDate': data['startDate'] ?? data['dateKey'],
          'endDate': data['endDate'],
          'numberOfDays': data['numberOfDays'],
          'created_at': data['createdAt'],
        });
      }

      items.sort((a, b) => ((a['time'] ?? '') as String).compareTo((b['time'] ?? '') as String));
      return items;
    } catch (e) {
      throw Exception('Failed to load medications: $e');
    }
  }

  Future<void> addMedication({
    required String userId,
    required String name,
    required String dosage,
    required List<String> timings,
    required DateTime startDate,
    DateTime? endDate,
    int? numberOfDays,
  }) async {
    try {
      final payload = <String, dynamic>{
        'userId': userId,
        'firebaseUid': userId,
        'name': name,
        'dosage': dosage,
        'timings': timings,
        // keep single field for backward compatibility in existing UI
        'timing': timings.join(', '),
        'startDate': _dateKey(startDate),
        'dateKey': _dateKey(startDate),
        'createdAt': FieldValue.serverTimestamp(),
      };
      if (endDate != null) {
        payload['endDate'] = _dateKey(endDate);
      }
      if (numberOfDays != null) {
        payload['numberOfDays'] = numberOfDays;
      }

      await _medicationsRef.add(payload);
    } catch (e) {
      throw Exception('Failed to add medication: $e');
    }
  }

  Future<void> updateMedication({
    required String medicationId,
    String? name,
    String? dosage,
    List<String>? timings,
    DateTime? startDate,
    DateTime? endDate,
    int? numberOfDays,
  }) async {
    try {
      final Map<String, dynamic> updates = {};
      
      if (name != null) updates['name'] = name;
      if (dosage != null) updates['dosage'] = dosage;
      if (timings != null) {
        updates['timings'] = timings;
        updates['timing'] = timings.join(', ');
      }
      if (startDate != null) updates['startDate'] = _dateKey(startDate);
      if (endDate != null) updates['endDate'] = _dateKey(endDate);
      if (numberOfDays != null) updates['numberOfDays'] = numberOfDays;

      updates['updatedAt'] = FieldValue.serverTimestamp();

      await _medicationsRef.doc(medicationId).update(updates);
    } catch (e) {
      throw Exception('Failed to update medication: $e');
    }
  }

  Future<void> deleteMedication(String medicationId) async {
    try {
      await _medicationsRef.doc(medicationId).delete();
    } catch (e) {
      throw Exception('Failed to delete medication: $e');
    }
  }
}
