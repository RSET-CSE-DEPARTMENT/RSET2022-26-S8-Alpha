import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'services/database_service.dart';
import 'services/api_service.dart';
import 'members_page.dart';
import 'profile_page.dart';

class SchedulePage extends StatefulWidget {
  final DateTime? initialDate;
  const SchedulePage({super.key, this.initialDate});

  @override
  State<SchedulePage> createState() => _SchedulePageState();
}

enum ActivityType { geoFenceCross, voiceRecognized, fallConfirmed }

class ActivityEvent {
  final String title;
  final DateTime timestamp;
  final ActivityType type;

  ActivityEvent({
    required this.title,
    required this.timestamp,
    required this.type,
  });
}

class _SchedulePageState extends State<SchedulePage> {
  int selectedTab = 0;
  late int selectedDay;
  late DateTime currentMonth;

  final DatabaseService _databaseService = DatabaseService();

  List<Map<String, dynamic>> _events = [];
  List<Map<String, dynamic>> _medications = [];
  List<ActivityEvent> _activityEvents = [];

  static const List<String> _medicationTimings = [
    'Morning Before Food',
    'Morning After Food',
    'Afternoon Before Food',
    'Afternoon After Food',
    'Night Before Food',
    'Night After Food',
  ];

  @override
  void initState() {
    super.initState();
    final now = widget.initialDate ?? DateTime.now();
    currentMonth = DateTime(now.year, now.month, 1);
    selectedDay = now.day;
    _loadData();
  }

  Future<void> _loadData() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;

    final date = DateTime(currentMonth.year, currentMonth.month, selectedDay);

    List<Map<String, dynamic>> events = [];
    List<Map<String, dynamic>> meds = [];
    try {
      events = await _databaseService.getEvents(user.uid, date);
      meds = await _databaseService.getMedications(user.uid, date);
    } catch (e) {
      debugPrint('Error loading schedule data: $e');
    }
    final activity = await _loadActivityEvents();

    if (!mounted) return;
    setState(() {
      _events = events;
      _medications = meds;
      _activityEvents = activity;
    });
  }

  String _monthName(int month) =>
      ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][month - 1];

  int _daysInMonth(int m, int y) {
    if (m == 2) {
      return (y % 4 == 0 && (y % 100 != 0 || y % 400 == 0)) ? 29 : 28;
    }
    return [31, 31, 30, 31, 30, 31, 31, 31, 30, 31, 30, 31][m - 1];
  }

  Color _activityColor(ActivityType type) {
    switch (type) {
      case ActivityType.geoFenceCross:
        return Colors.green;
      case ActivityType.voiceRecognized:
        return Colors.orange;
      case ActivityType.fallConfirmed:
        return Colors.red;
    }
  }

  Future<List<ActivityEvent>> _loadActivityEvents() async {
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) return [];

      final snapshot = await FirebaseFirestore.instance
          .collection('notification')
          .doc(ApiService.notificationDocId)
          .collection('logs')
          .get();

      final events = snapshot.docs.map((doc) {
        final data = doc.data();
        final ownerId = (data['userId'] ?? '').toString().trim();
        if (ownerId.isNotEmpty && ownerId != user.uid) {
          return null;
        }

        final alertType = _resolveAlertType(data);
        if (alertType != 'fall' &&
            alertType != 'speaker' &&
            alertType != 'geofence') {
          return null;
        }

        final receivedAt = data['receivedAt'] as Timestamp?;
        final sentTime = data['sentTime'] as Timestamp?;
        final timestamp = (receivedAt ?? sentTime)?.toDate() ?? DateTime.now();

        if (alertType == 'fall') {
          return ActivityEvent(
            title: 'Fall Detected',
            timestamp: timestamp,
            type: ActivityType.fallConfirmed,
          );
        }
        if (alertType == 'speaker') {
          final personName = _extractSpeakerName(data);
          return ActivityEvent(
            title: '$personName has interacted',
            timestamp: timestamp,
            type: ActivityType.voiceRecognized,
          );
        }
        return ActivityEvent(
          title: 'Geofence Crossed',
          timestamp: timestamp,
          type: ActivityType.geoFenceCross,
        );
      }).whereType<ActivityEvent>().toList();

      events.sort((a, b) => b.timestamp.compareTo(a.timestamp));
      return events;
    } catch (e) {
      debugPrint('Error loading activity logs: $e');
      return [];
    }
  }

  String _formatDate(DateTime dt) {
    final d = dt.day.toString().padLeft(2, '0');
    final m = dt.month.toString().padLeft(2, '0');
    final y = dt.year.toString();
    return '$d/$m/$y';
  }

  String _formatTimeOfDay(TimeOfDay t) {
    final hour = t.hourOfPeriod == 0 ? 12 : t.hourOfPeriod;
    final minute = t.minute.toString().padLeft(2, '0');
    final period = t.period == DayPeriod.am ? 'AM' : 'PM';
    return '$hour:$minute $period';
  }

  String _formatTime(DateTime dt) {
    final t = TimeOfDay.fromDateTime(dt);
    return _formatTimeOfDay(t);
  }

  DateTime _parseDateKeyOrDefault(String value, DateTime fallback) {
    final parsed = DateTime.tryParse(value);
    if (parsed == null) return fallback;
    return DateTime(parsed.year, parsed.month, parsed.day);
  }

  String _extractSpeakerName(Map<String, dynamic> logData) {
    final nestedRaw = logData['data'];
    final nested = nestedRaw is Map
        ? Map<String, dynamic>.from(nestedRaw)
        : <String, dynamic>{};

    final direct = (nested['detectedSpeaker'] ??
            nested['speakerName'] ??
            nested['speaker'] ??
            logData['detectedSpeaker'] ??
            logData['speakerName'] ??
            logData['speaker'])
        ?.toString()
        .trim();

    if (direct != null && direct.isNotEmpty) {
      if (direct.toUpperCase() == 'UNKNOWN') {
        return 'Unknown person';
      }
      return direct;
    }

    final body = (logData['body'] ?? '').toString().trim();
    final speakingMatch = RegExp(r'^(.+?)\s+is speaking\.?$', caseSensitive: false)
        .firstMatch(body);
    if (speakingMatch != null) {
      final candidate = (speakingMatch.group(1) ?? '').trim();
      if (candidate.isNotEmpty) return candidate;
    }

    if (body.toLowerCase().contains('unknown person')) {
      return 'Unknown person';
    }

    return 'Someone';
  }

  String _resolveAlertType(Map<String, dynamic> data) {
    final nestedRaw = data['data'];
    final nested = nestedRaw is Map
        ? Map<String, dynamic>.from(nestedRaw)
        : <String, dynamic>{};

    final raw = (data['alertType'] ??
            data['type'] ??
            nested['alertType'] ??
            nested['type'] ??
            '')
        .toString()
        .toLowerCase()
        .trim();

    if (raw.contains('fall')) return 'fall';
    if (raw.contains('speaker') || raw.contains('voice')) return 'speaker';
    if (raw.contains('geofence') || raw.contains('fence')) return 'geofence';

    final title = (data['title'] ?? '').toString().toLowerCase();
    final body = (data['body'] ?? '').toString().toLowerCase();
    final text = '$title $body';
    if (text.contains('fall')) return 'fall';
    if (text.contains('speaking') ||
        text.contains('speaker') ||
        text.contains('voice')) {
      return 'speaker';
    }
    if (text.contains('geofence') || text.contains('safe zone')) {
      return 'geofence';
    }

    return 'unknown';
  }

  Future<void> _showAddEventDialog() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please sign in to add events')),
      );
      return;
    }

    final titleCtrl = TextEditingController();
    final descCtrl = TextEditingController();
    DateTime eventDate =
        DateTime(currentMonth.year, currentMonth.month, selectedDay);
    TimeOfDay eventTime = TimeOfDay.now();

    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setLocalState) => SafeArea(
            child: SingleChildScrollView(
              padding: EdgeInsets.only(
                left: 16,
                right: 16,
                top: 16,
                bottom: MediaQuery.of(ctx).viewInsets.bottom + 16,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                const Text(
                  'Add Event',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: titleCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Event title',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: descCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Description',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(child: Text('Date: ${_formatDate(eventDate)}')),
                    TextButton(
                      onPressed: () async {
                        final picked = await showDatePicker(
                          context: ctx,
                          initialDate: eventDate,
                          firstDate: DateTime(2020),
                          lastDate: DateTime(2100),
                        );
                        if (picked != null) {
                          setLocalState(() => eventDate = picked);
                        }
                      },
                      child: const Text('Pick Date'),
                    ),
                  ],
                ),
                Row(
                  children: [
                    Expanded(child: Text('Time: ${_formatTimeOfDay(eventTime)}')),
                    TextButton(
                      onPressed: () async {
                        final picked = await showTimePicker(
                          context: ctx,
                          initialTime: eventTime,
                        );
                        if (picked != null) {
                          setLocalState(() => eventTime = picked);
                        }
                      },
                      child: const Text('Pick Time'),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: () async {
                      final title = titleCtrl.text.trim();
                      if (title.isEmpty) return;

                      try {
                        await _databaseService.addEvent(
                          userId: user.uid,
                          title: title,
                          description: descCtrl.text.trim(),
                          time: _formatTimeOfDay(eventTime),
                          date: eventDate,
                        );

                        if (!mounted) return;
                        Navigator.pop(ctx);
                        await _loadData();
                      } catch (e) {
                        if (!mounted) return;
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text('Failed to save event: $e')),
                        );
                      }
                    },
                    child: const Text('Save Event'),
                  ),
                ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Future<void> _showEditEventDialog(Map<String, dynamic> event) async {
    final eventId = (event['id'] ?? '').toString();
    if (eventId.isEmpty) return;

    final titleCtrl = TextEditingController(text: (event['title'] ?? '').toString());
    final descCtrl =
        TextEditingController(text: (event['description'] ?? '').toString());
    DateTime eventDate = _parseDateKeyOrDefault(
      (event['date'] ?? '').toString(),
      DateTime(currentMonth.year, currentMonth.month, selectedDay),
    );
    TimeOfDay eventTime = TimeOfDay.now();

    final existingTime = (event['time'] ?? '').toString();
    final match = RegExp(r'^(\d{1,2}):(\d{2})\s*(AM|PM)$', caseSensitive: false)
        .firstMatch(existingTime);
    if (match != null) {
      var hour = int.tryParse(match.group(1) ?? '0') ?? 0;
      final minute = int.tryParse(match.group(2) ?? '0') ?? 0;
      final period = (match.group(3) ?? 'AM').toUpperCase();
      if (period == 'PM' && hour != 12) hour += 12;
      if (period == 'AM' && hour == 12) hour = 0;
      eventTime = TimeOfDay(hour: hour, minute: minute);
    }

    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setLocalState) => SafeArea(
            child: SingleChildScrollView(
              padding: EdgeInsets.only(
                left: 16,
                right: 16,
                top: 16,
                bottom: MediaQuery.of(ctx).viewInsets.bottom + 16,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Edit Event',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: titleCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Event title',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: descCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Description',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(child: Text('Date: ${_formatDate(eventDate)}')),
                      TextButton(
                        onPressed: () async {
                          final picked = await showDatePicker(
                            context: ctx,
                            initialDate: eventDate,
                            firstDate: DateTime(2020),
                            lastDate: DateTime(2100),
                          );
                          if (picked != null) setLocalState(() => eventDate = picked);
                        },
                        child: const Text('Pick Date'),
                      ),
                    ],
                  ),
                  Row(
                    children: [
                      Expanded(child: Text('Time: ${_formatTimeOfDay(eventTime)}')),
                      TextButton(
                        onPressed: () async {
                          final picked = await showTimePicker(
                            context: ctx,
                            initialTime: eventTime,
                          );
                          if (picked != null) setLocalState(() => eventTime = picked);
                        },
                        child: const Text('Pick Time'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: () async {
                        final title = titleCtrl.text.trim();
                        if (title.isEmpty) return;
                        try {
                          await _databaseService.updateEvent(
                            eventId: eventId,
                            title: title,
                            description: descCtrl.text.trim(),
                            time: _formatTimeOfDay(eventTime),
                            date: eventDate,
                          );
                          if (!mounted) return;
                          Navigator.pop(ctx);
                          await _loadData();
                        } catch (e) {
                          if (!mounted) return;
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text('Failed to update event: $e')),
                          );
                        }
                      },
                      child: const Text('Update Event'),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Future<void> _deleteEvent(Map<String, dynamic> event) async {
    final eventId = (event['id'] ?? '').toString();
    if (eventId.isEmpty) return;
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Event'),
        content: const Text('Are you sure you want to delete this event?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Delete')),
        ],
      ),
    );
    if (confirm != true) return;
    try {
      await _databaseService.deleteEvent(eventId);
      if (!mounted) return;
      await _loadData();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to delete event: $e')),
      );
    }
  }

  Future<void> _showAddMedicationDialog() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please sign in to add medication')),
      );
      return;
    }

    final nameCtrl = TextEditingController();
    final dosageCtrl = TextEditingController();
    final Set<String> selectedTimings = {_medicationTimings.first};
    DateTime startDate = DateTime(currentMonth.year, currentMonth.month, selectedDay);
    DateTime? endDate = DateTime(currentMonth.year, currentMonth.month, selectedDay);
    bool useDateRange = true;
    final daysController = TextEditingController(text: '1');

    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setLocalState) => SafeArea(
            child: SingleChildScrollView(
              padding: EdgeInsets.only(
                left: 16,
                right: 16,
                top: 16,
                bottom: MediaQuery.of(ctx).viewInsets.bottom + 16,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                const Text(
                  'Add Medication',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: nameCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Medication name',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: dosageCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Dosage (optional)',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 10),
                const Text('Timing'),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: List.generate(_medicationTimings.length, (index) {
                    final timing = _medicationTimings[index];
                    return FilterChip(
                      label: Text(timing),
                      selected: selectedTimings.contains(timing),
                      onSelected: (selected) => setLocalState(() {
                        if (selected) {
                          selectedTimings.add(timing);
                        } else {
                          selectedTimings.remove(timing);
                        }
                      }),
                    );
                  }),
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: RadioListTile<bool>(
                        value: true,
                        groupValue: useDateRange,
                        onChanged: (value) =>
                            setLocalState(() => useDateRange = value ?? true),
                        title: const Text('Date range'),
                        dense: true,
                      ),
                    ),
                    Expanded(
                      child: RadioListTile<bool>(
                        value: false,
                        groupValue: useDateRange,
                        onChanged: (value) =>
                            setLocalState(() => useDateRange = value ?? true),
                        title: const Text('No. of days'),
                        dense: true,
                      ),
                    ),
                  ],
                ),
                Row(
                  children: [
                    Expanded(child: Text('Start: ${_formatDate(startDate)}')),
                    TextButton(
                      onPressed: () async {
                        final picked = await showDatePicker(
                          context: ctx,
                          initialDate: startDate,
                          firstDate: DateTime(2020),
                          lastDate: DateTime(2100),
                        );
                        if (picked != null) {
                          setLocalState(() {
                            startDate = picked;
                            if (endDate != null && endDate!.isBefore(startDate)) {
                              endDate = startDate;
                            }
                          });
                        }
                      },
                      child: const Text('Pick Start'),
                    ),
                  ],
                ),
                if (useDateRange)
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          'End: ${_formatDate(endDate ?? startDate)}',
                        ),
                      ),
                      TextButton(
                        onPressed: () async {
                          final picked = await showDatePicker(
                            context: ctx,
                            initialDate: endDate ?? startDate,
                            firstDate: startDate,
                            lastDate: DateTime(2100),
                          );
                          if (picked != null) {
                            setLocalState(() => endDate = picked);
                          }
                        },
                        child: const Text('Pick End'),
                      ),
                    ],
                  )
                else
                  TextField(
                    controller: daysController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Number of days',
                      border: OutlineInputBorder(),
                    ),
                  ),
                const SizedBox(height: 10),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: () async {
                      final name = nameCtrl.text.trim();
                      if (name.isEmpty) return;
                      if (selectedTimings.isEmpty) {
                        if (!mounted) return;
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('Select at least one timing'),
                          ),
                        );
                        return;
                      }

                      try {
                        final days = int.tryParse(daysController.text.trim());
                        await _databaseService.addMedication(
                          userId: user.uid,
                          name: name,
                          dosage: dosageCtrl.text.trim(),
                          timings: selectedTimings.toList(),
                          startDate: startDate,
                          endDate: useDateRange ? (endDate ?? startDate) : null,
                          numberOfDays: useDateRange ? null : (days ?? 1),
                        );

                        if (!mounted) return;
                        Navigator.pop(ctx);
                        await _loadData();
                      } catch (e) {
                        if (!mounted) return;
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text('Failed to save medication: $e'),
                          ),
                        );
                      }
                    },
                    child: const Text('Save Medication'),
                  ),
                ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Future<void> _showEditMedicationDialog(Map<String, dynamic> medication) async {
    final medicationId = (medication['id'] ?? '').toString();
    if (medicationId.isEmpty) return;

    final nameCtrl = TextEditingController(text: (medication['name'] ?? '').toString());
    final dosageCtrl =
        TextEditingController(text: (medication['dosage'] ?? '').toString());

    final existingTimings = (medication['timings'] is List)
        ? (medication['timings'] as List).map((e) => e.toString()).toSet()
        : <String>{};
    final Set<String> selectedTimings =
        existingTimings.isEmpty ? {_medicationTimings.first} : existingTimings;

    DateTime startDate = _parseDateKeyOrDefault(
      (medication['startDate'] ?? '').toString(),
      DateTime(currentMonth.year, currentMonth.month, selectedDay),
    );
    DateTime? endDate = (medication['endDate'] ?? '').toString().isNotEmpty
        ? _parseDateKeyOrDefault(
            (medication['endDate'] ?? '').toString(),
            startDate,
          )
        : null;
    final rawDays = medication['numberOfDays'];
    final hasDays = rawDays is num && rawDays > 0;
    bool useDateRange = endDate != null || !hasDays;
    final daysController = TextEditingController(
      text: hasDays ? rawDays.toInt().toString() : '1',
    );

    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setLocalState) => SafeArea(
            child: SingleChildScrollView(
              padding: EdgeInsets.only(
                left: 16,
                right: 16,
                top: 16,
                bottom: MediaQuery.of(ctx).viewInsets.bottom + 16,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Edit Medication',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: nameCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Medication name',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: dosageCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Dosage (optional)',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 10),
                  const Text('Timing'),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: List.generate(_medicationTimings.length, (index) {
                      final timing = _medicationTimings[index];
                      return FilterChip(
                        label: Text(timing),
                        selected: selectedTimings.contains(timing),
                        onSelected: (selected) => setLocalState(() {
                          if (selected) {
                            selectedTimings.add(timing);
                          } else {
                            selectedTimings.remove(timing);
                          }
                        }),
                      );
                    }),
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: RadioListTile<bool>(
                          value: true,
                          groupValue: useDateRange,
                          onChanged: (value) =>
                              setLocalState(() => useDateRange = value ?? true),
                          title: const Text('Date range'),
                          dense: true,
                        ),
                      ),
                      Expanded(
                        child: RadioListTile<bool>(
                          value: false,
                          groupValue: useDateRange,
                          onChanged: (value) =>
                              setLocalState(() => useDateRange = value ?? true),
                          title: const Text('No. of days'),
                          dense: true,
                        ),
                      ),
                    ],
                  ),
                  Row(
                    children: [
                      Expanded(child: Text('Start: ${_formatDate(startDate)}')),
                      TextButton(
                        onPressed: () async {
                          final picked = await showDatePicker(
                            context: ctx,
                            initialDate: startDate,
                            firstDate: DateTime(2020),
                            lastDate: DateTime(2100),
                          );
                          if (picked != null) {
                            setLocalState(() {
                              startDate = picked;
                              if (endDate != null && endDate!.isBefore(startDate)) {
                                endDate = startDate;
                              }
                            });
                          }
                        },
                        child: const Text('Pick Start'),
                      ),
                    ],
                  ),
                  if (useDateRange)
                    Row(
                      children: [
                        Expanded(
                          child: Text('End: ${_formatDate(endDate ?? startDate)}'),
                        ),
                        TextButton(
                          onPressed: () async {
                            final picked = await showDatePicker(
                              context: ctx,
                              initialDate: endDate ?? startDate,
                              firstDate: startDate,
                              lastDate: DateTime(2100),
                            );
                            if (picked != null) {
                              setLocalState(() => endDate = picked);
                            }
                          },
                          child: const Text('Pick End'),
                        ),
                      ],
                    )
                  else
                    TextField(
                      controller: daysController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Number of days',
                        border: OutlineInputBorder(),
                      ),
                    ),
                  const SizedBox(height: 10),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: () async {
                        final name = nameCtrl.text.trim();
                        if (name.isEmpty) return;
                        if (selectedTimings.isEmpty) return;
                        try {
                          final days = int.tryParse(daysController.text.trim());
                          await _databaseService.updateMedication(
                            medicationId: medicationId,
                            name: name,
                            dosage: dosageCtrl.text.trim(),
                            timings: selectedTimings.toList(),
                            startDate: startDate,
                            endDate: useDateRange ? (endDate ?? startDate) : null,
                            numberOfDays: useDateRange ? null : (days ?? 1),
                          );
                          if (!mounted) return;
                          Navigator.pop(ctx);
                          await _loadData();
                        } catch (e) {
                          if (!mounted) return;
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text('Failed to update medication: $e'),
                            ),
                          );
                        }
                      },
                      child: const Text('Update Medication'),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Future<void> _deleteMedication(Map<String, dynamic> medication) async {
    final medicationId = (medication['id'] ?? '').toString();
    if (medicationId.isEmpty) return;
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Medication'),
        content: const Text('Are you sure you want to delete this medication?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Delete')),
        ],
      ),
    );
    if (confirm != true) return;
    try {
      await _databaseService.deleteMedication(medicationId);
      if (!mounted) return;
      await _loadData();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to delete medication: $e')),
      );
    }
  }

  Future<void> _onAddPressed() async {
    if (selectedTab == 0) {
      await _showAddEventDialog();
    } else if (selectedTab == 1) {
      await _showAddMedicationDialog();
    }
  }

  Widget _calendar() {
    final days = _daysInMonth(currentMonth.month, currentMonth.year);
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: days,
      gridDelegate:
          const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 7),
      itemBuilder: (_, i) {
        final day = i + 1;
        final selected = day == selectedDay;
        return GestureDetector(
          onTap: () {
            setState(() => selectedDay = day);
            _loadData();
          },
          child: Center(
            child: Container(
              width: 36,
              height: 36,
              alignment: Alignment.center,
              decoration: selected
                  ? const BoxDecoration(
                      color: Colors.blue, shape: BoxShape.circle)
                  : null,
              child: Text(
                '$day',
                style: TextStyle(
                  color: selected ? Colors.white : Colors.black,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xfff7f7f7),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Schedule',
                  style: TextStyle(
                      fontSize: 32, fontWeight: FontWeight.bold)),

              const SizedBox(height: 12),

              Row(
                children: [
                  Text(
                    '${_monthName(currentMonth.month)} ${currentMonth.year}',
                    style: const TextStyle(
                        fontSize: 20, fontWeight: FontWeight.w600),
                  ),
                ],
              ),

              const SizedBox(height: 12),
              _calendar(),

              const SizedBox(height: 20),

              Row(
                children: [
                  _tab('Events', 0),
                  _tab('Medication', 1),
                  _tab('Activity', 2),
                ],
              ),

              const SizedBox(height: 16),

              if (selectedTab != 2)
                Align(
                  alignment: Alignment.centerRight,
                  child: ElevatedButton.icon(
                    onPressed: _onAddPressed,
                    icon: const Icon(Icons.add),
                    label: Text(selectedTab == 0 ? 'Add Event' : 'Add Medication'),
                  ),
                ),

              if (selectedTab != 2) const SizedBox(height: 12),

              if (selectedTab == 0)
                _events.isEmpty
                    ? const Text('No events')
                    : Column(
                        children: _events
                            .map((e) => _card(
                                  title: e['title'] ?? '',
                                  subtitle: e['description'] ?? '',
                                  time: e['time'] ?? '',
                                  icon: Icons.event,
                                  accent: Colors.blue,
                                  onEdit: () => _showEditEventDialog(e),
                                  onDelete: () => _deleteEvent(e),
                                ))
                            .toList(),
                      ),

              if (selectedTab == 1)
                _medications.isEmpty
                    ? const Text('No medication')
                    : Column(
                        children: _medications
                            .map((m) => _card(
                                  title: m['name'] ?? '',
                                  subtitle: _buildMedicationSubtitle(m),
                                  time: m['time'] ?? '',
                                  icon: Icons.medication,
                                  accent: Colors.teal,
                                  onEdit: () => _showEditMedicationDialog(m),
                                  onDelete: () => _deleteMedication(m),
                                ))
                            .toList(),
                      ),

              if (selectedTab == 2)
                Column(
                  children: _activityEvents
                      .map((a) => ListTile(
                            leading: CircleAvatar(
                              radius: 6,
                              backgroundColor: _activityColor(a.type),
                            ),
                            title: Text(a.title),
                            subtitle: Text(_formatDate(a.timestamp)),
                            trailing: Text(_formatTime(a.timestamp)),
                          ))
                      .toList(),
                ),
            ],
          ),
        ),
      ),
      // Bottom nav: Schedule selected
      bottomNavigationBar: BottomNavigationBar(
        type: BottomNavigationBarType.fixed,
        currentIndex: 1,
        selectedItemColor: Colors.blue,
        unselectedItemColor: Colors.grey,
        onTap: (index) {
          if (index == 0) {
            Navigator.popUntil(context, (route) => route.isFirst);
          } else if (index == 2) {
            Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const MembersPage()),
            );
          } else if (index == 3) {
            Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) =>
                    const ProfilePage(userName: 'Mr. Augustine', imageUrl: ''),
              ),
            );
          }
          // index 1 = Schedule (current)
        },
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.home), label: 'Home'),
          BottomNavigationBarItem(
            icon: Icon(Icons.calendar_month),
            label: 'Schedule',
          ),
          BottomNavigationBarItem(icon: Icon(Icons.people), label: 'Members'),
          BottomNavigationBarItem(icon: Icon(Icons.person), label: 'Profile'),
        ],
      ),
    );
  }

  Widget _tab(String label, int index) {
    final selected = selectedTab == index;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => selectedTab = index),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10),
          margin: const EdgeInsets.symmetric(horizontal: 4),
          decoration: BoxDecoration(
            color: selected ? Colors.white : Colors.transparent,
            borderRadius: BorderRadius.circular(20),
          ),
          child: Center(
            child: Text(label,
                style: TextStyle(
                    fontWeight: FontWeight.w600,
                    color: selected ? Colors.black : Colors.grey)),
          ),
        ),
      ),
    );
  }

  Widget _card({
    required String title,
    required String subtitle,
    required String time,
    IconData? icon,
    Color? accent,
    VoidCallback? onEdit,
    VoidCallback? onDelete,
  }) {
    final iconColor = accent ?? Colors.blue;
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: iconColor.withOpacity(0.2)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.04),
            blurRadius: 8,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Row(
        children: [
          if (icon != null) ...[
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: iconColor.withOpacity(0.12),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon, color: iconColor, size: 20),
            ),
            const SizedBox(width: 12),
          ],
          Expanded(
            child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title,
                      style: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 4),
                  Text(subtitle,
                      style:
                          const TextStyle(fontSize: 14, color: Colors.grey)),
                ]),
          ),
          if (onEdit != null || onDelete != null)
            PopupMenuButton<String>(
              onSelected: (value) {
                if (value == 'edit') onEdit?.call();
                if (value == 'delete') onDelete?.call();
              },
              itemBuilder: (context) => [
                if (onEdit != null)
                  const PopupMenuItem(
                    value: 'edit',
                    child: Text('Edit'),
                  ),
                if (onDelete != null)
                  const PopupMenuItem(
                    value: 'delete',
                    child: Text('Delete'),
                  ),
              ],
            ),
          if (time.trim().isNotEmpty)
            Text(
              time,
              style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
        ],
      ),
    );
  }

  String _buildMedicationSubtitle(Map<String, dynamic> medication) {
    final dosage = (medication['dosage'] ?? '').toString();
    final timingsRaw = medication['timings'];
    List<String> timings = [];
    if (timingsRaw is List) {
      timings = timingsRaw.map((e) => e.toString()).toList();
    } else if ((medication['timing'] ?? '').toString().isNotEmpty) {
      timings = [(medication['timing'] ?? '').toString()];
    }

    final startDate = (medication['startDate'] ?? '').toString();
    final endDate = (medication['endDate'] ?? '').toString();
    final days = medication['numberOfDays'];

    final parts = <String>[];
    if (dosage.isNotEmpty) parts.add(dosage);
    if (timings.isNotEmpty) parts.add(timings.join(', '));
    if (startDate.isNotEmpty && endDate.isNotEmpty) {
      parts.add('$startDate to $endDate');
    } else if (startDate.isNotEmpty && days != null) {
      parts.add('$startDate for $days day(s)');
    }
    return parts.join(' • ');
  }
}
