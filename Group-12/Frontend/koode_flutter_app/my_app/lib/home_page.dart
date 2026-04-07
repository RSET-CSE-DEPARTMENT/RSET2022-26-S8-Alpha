import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'schedule_page.dart';
import 'members_page.dart';
import 'profile_page.dart';
import 'gps_page.dart';
import 'fall_alerts_page.dart';
import 'services/database_service.dart';
import 'services/api_service.dart';



class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  String _userName = 'User';
  final DatabaseService _databaseService = DatabaseService();
  List<Map<String, dynamic>> _eventsToday = [];
  List<Map<String, dynamic>> _medicationsToday = [];
  List<_RecognizedMember> _recentMembers = [];
  bool _loadingHomeData = true;

  static const List<Color> _memberColors = [
    Colors.blue,
    Colors.green,
    Colors.pink,
  ];

  @override
  void initState() {
    super.initState();
    _fetchUserName();
    _loadHomeData();
  }

  Future<void> _openAndRefresh(Widget page) async {
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => page),
    );
    if (!mounted) return;
    setState(() => _loadingHomeData = true);
    await _loadHomeData();
  }

  Future<void> _fetchUserName() async {
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user != null) {
        final display = (user.displayName != null &&
                user.displayName!.trim().isNotEmpty)
            ? user.displayName!.trim()
            : user.email?.split('@').first ?? 'User';
        setState(() => _userName = display);
      }
    } catch (e) {
      debugPrint('Error fetching user name: $e');
    }
  }

  Future<void> _loadHomeData() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      if (!mounted) return;
      setState(() => _loadingHomeData = false);
      return;
    }

    final today = DateTime.now();

    List<Map<String, dynamic>> events = [];
    List<Map<String, dynamic>> medications = [];
    List<_RecognizedMember> members = [];

    try {
      events = await _databaseService.getEvents(user.uid, today);
      medications = await _databaseService.getMedications(user.uid, today);
      members = await _loadRecentRecognizedMembers(user.uid);
    } catch (e) {
      debugPrint('Error loading home data: $e');
    }

    if (!mounted) return;
    setState(() {
      _eventsToday = events;
      _medicationsToday = medications;
      _recentMembers = members;
      _loadingHomeData = false;
    });
  }

  Future<List<_RecognizedMember>> _loadRecentRecognizedMembers(
    String userId,
  ) async {
    final logsRef = FirebaseFirestore.instance
        .collection('notification')
        .doc(ApiService.notificationDocId)
        .collection('logs');

    var snap = await logsRef
        .where('alertType', isEqualTo: 'speaker')
        .where('userId', isEqualTo: userId)
        .get();

    if (snap.docs.isEmpty) {
      snap = await logsRef.where('alertType', isEqualTo: 'speaker').get();
    }

    final docs = snap.docs.toList()
      ..sort((a, b) {
        final ta = ((a.data()['receivedAt'] as Timestamp?) ??
                (a.data()['sentTime'] as Timestamp?))
            ?.millisecondsSinceEpoch ??
            0;
        final tb = ((b.data()['receivedAt'] as Timestamp?) ??
                (b.data()['sentTime'] as Timestamp?))
            ?.millisecondsSinceEpoch ??
            0;
        return tb.compareTo(ta);
      });

    final seen = <String>{};
    final members = <_RecognizedMember>[];
    for (final doc in docs) {
      final data = doc.data();
      final name = _extractSpeakerName(data);
      if (name.isEmpty || name == 'Unknown person' || seen.contains(name)) {
        continue;
      }
      seen.add(name);
      members.add(
        _RecognizedMember(
          name: name,
          description: 'Recently voice recognized',
        ),
      );
      if (members.length == 3) break;
    }
    return members;
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
      if (direct.toUpperCase() == 'UNKNOWN') return 'Unknown person';
      return direct;
    }

    final body = (logData['body'] ?? '').toString().trim();
    final speakingMatch = RegExp(r'^(.+?)\s+is speaking\.?$', caseSensitive: false)
        .firstMatch(body);
    if (speakingMatch != null) {
      final candidate = (speakingMatch.group(1) ?? '').trim();
      if (candidate.isNotEmpty) return candidate;
    }
    return '';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,

      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        leading: Padding(
          padding: const EdgeInsets.only(left: 16.0),
          child: CircleAvatar(
            backgroundColor: Colors.grey[200],
            child: const Icon(Icons.person, color: Colors.grey),
          ),
        ),
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Hello,',
              style: TextStyle(fontSize: 14, color: Colors.grey),
            ),
            Text(
              _userName,
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: Colors.grey[800],
              ),
            ),
          ],
        ),
        actions: const [
          SizedBox(width: 8),
        ],
      ),

      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Overview',
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                  color: Colors.black87,
                ),
              ),
              const SizedBox(height: 20),

              // Status, GPS, Schedule, Fall Alerts Row
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: InkWell(
                      onTap: () async {
                        await _openAndRefresh(const FallAlertsPage());
                      },
                      child: _OverviewCard(
                        title: 'Fall Alerts',
                        icon: Icons.warning_amber_rounded,
                        color: Colors.red,
                      ),
                    ),
                  ),
                  SizedBox(width: 8),
                  Expanded(
                    child: InkWell(
                      onTap: () async {
                        await _openAndRefresh(const GpsPage());
                      },
                      child: _OverviewCard(
                        title: 'GPS',
                        icon: Icons.location_on,
                        color: Colors.green,
                      ),
                    ),
                  ),
                  SizedBox(width: 8),
                  Expanded(
                    child: InkWell(
                      onTap: () async {
                        await _openAndRefresh(
                          SchedulePage(initialDate: DateTime.now()),
                        );
                      },
                      child: _OverviewCard(
                        title: 'Schedule',
                        icon: Icons.calendar_today,
                        color: Colors.orange,
                      ),
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 15),

            

              const SizedBox(height: 30),
              const Text(
                'Events',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: Colors.black87,
                ),
              ),
              const SizedBox(height: 15),
              if (_loadingHomeData)
                const Center(
                  child: Padding(
                    padding: EdgeInsets.symmetric(vertical: 24),
                    child: CircularProgressIndicator(),
                  ),
                )
              else ...[
                if (_eventsToday.isEmpty)
                  const Text(
                    'No events today',
                    style: TextStyle(color: Colors.grey),
                  )
                else
                  Column(
                    children: _eventsToday
                        .map(
                          (event) => _HomeEntryCard(
                            icon: Icons.event,
                            iconColor: Colors.red,
                            title: (event['title'] ?? '').toString(),
                            time: (event['time'] ?? '').toString(),
                            subtitle: (event['description'] ?? '').toString(),
                          ),
                        )
                        .toList(),
                  ),
                const SizedBox(height: 16),
                const Text(
                  'Medication',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                    color: Colors.black87,
                  ),
                ),
                const SizedBox(height: 12),
                if (_medicationsToday.isEmpty)
                  const Text(
                    'No medication today',
                    style: TextStyle(color: Colors.grey),
                  )
                else
                  Column(
                    children: _medicationsToday
                        .map(
                          (medication) => _HomeMedicationCard(
                            name: (medication['name'] ?? '').toString(),
                            dosage: (medication['dosage'] ?? '').toString(),
                            timings: (medication['timings'] is List)
                                ? (medication['timings'] as List)
                                    .map((e) => e.toString())
                                    .toList()
                                : <String>[],
                          ),
                        )
                        .toList(),
                  ),
              ],

              const SizedBox(height: 20),
              const Text(
                'Members',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: Colors.black87,
                ),
              ),
              const SizedBox(height: 15),
              if (_loadingHomeData)
                const SizedBox.shrink()
              else if (_recentMembers.isEmpty)
                const Text(
                  'No recently recognized voices',
                  style: TextStyle(color: Colors.grey),
                )
              else
                Column(
                  children: List.generate(_recentMembers.length, (index) {
                    final member = _recentMembers[index];
                    return Padding(
                      padding: EdgeInsets.only(
                        bottom: index == _recentMembers.length - 1 ? 0 : 12,
                      ),
                      child: _MemberCard(
                        icon: Icons.person,
                        name: member.name,
                        description: member.description,
                        color: _memberColors[index % _memberColors.length],
                      ),
                    );
                  }),
                ),

              const SizedBox(height: 10),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: () {},
                  child: const Text(
                    'View All',
                    style: TextStyle(
                      color: Colors.blue,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),

      // Bottom Navigation Bar
      bottomNavigationBar: BottomNavigationBar(
        type: BottomNavigationBarType.fixed,
        currentIndex: 0,
        selectedItemColor: Colors.blue,
        unselectedItemColor: Colors.grey,
        onTap: (index) async {
          if (index == 1) {
            await _openAndRefresh(const SchedulePage());
          } else if (index == 2) {
            await _openAndRefresh(const MembersPage());
          } else if (index == 3) {
            await _openAndRefresh(
              const ProfilePage(userName: 'Mr. Augustine', imageUrl: ''),
            );
          }
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
}

// Extracted stateless widgets to prevent unnecessary rebuilds
class _OverviewCard extends StatelessWidget {
  final String title;
  final IconData icon;
  final Color color;

  const _OverviewCard({
    required this.title,
    required this.icon,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 4),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.grey.withAlpha(26),
            blurRadius: 10,
            spreadRadius: 2,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(12.0), // Reduced from 16
        child: Column( // Changed from Row to Column
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 36, // Slightly smaller
              height: 36,
              decoration: BoxDecoration(
                color: color.withAlpha(26),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, color: color, size: 20),
            ),
            const SizedBox(height: 8),
            Text(
              title,
              style: const TextStyle(
                fontSize: 12, // Reduced from 14
                fontWeight: FontWeight.w500,
                color: Colors.black87,
              ),
              textAlign: TextAlign.center,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }
}

class _RecognizedMember {
  final String name;
  final String description;

  const _RecognizedMember({
    required this.name,
    required this.description,
  });
}

class _HomeEntryCard extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String title;
  final String subtitle;
  final String time;

  const _HomeEntryCard({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.subtitle,
    required this.time,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.grey.withAlpha(26),
            blurRadius: 10,
            spreadRadius: 2,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: iconColor.withAlpha(26),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, color: iconColor),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                      color: Colors.black87,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    subtitle,
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.grey[700],
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
            if (time.trim().isNotEmpty)
              Text(
                time,
                style: TextStyle(
                  fontSize: 14,
                  color: Colors.grey[700],
                  fontWeight: FontWeight.w600,
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _HomeMedicationCard extends StatelessWidget {
  final String name;
  final String dosage;
  final List<String> timings;

  const _HomeMedicationCard({
    required this.name,
    required this.dosage,
    required this.timings,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.grey.withAlpha(26),
            blurRadius: 10,
            spreadRadius: 2,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: Colors.blue[50],
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(
                    Icons.medication,
                    color: Colors.blue,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    name,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                      color: Colors.black87,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                if (dosage.trim().isNotEmpty)
                  Text(
                    dosage,
                    style: const TextStyle(
                      fontSize: 14,
                      color: Colors.grey,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
              ],
            ),
            if (timings.isNotEmpty) ...[
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: timings
                    .map(
                      (timing) => Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 10,
                          vertical: 6,
                        ),
                        decoration: BoxDecoration(
                          color: Colors.blue.withAlpha(20),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          timing,
                          style: const TextStyle(
                            color: Colors.blue,
                            fontWeight: FontWeight.w600,
                            fontSize: 12,
                          ),
                        ),
                      ),
                    )
                    .toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _MemberCard extends StatelessWidget {
  final IconData icon;
  final String name;
  final String description;
  final Color color;

  const _MemberCard({
    required this.icon,
    required this.name,
    required this.description,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.grey.withAlpha(26),
            blurRadius: 5,
            spreadRadius: 1,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Row(
          children: [
            Container(
              width: 50,
              height: 50,
              decoration: BoxDecoration(
                color: color.withAlpha(26),
                borderRadius: BorderRadius.circular(25),
              ),
              child: Icon(icon, color: color, size: 28),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    name,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                      color: Colors.black87,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    description,
                    style: TextStyle(fontSize: 12, color: Colors.grey[700]),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
