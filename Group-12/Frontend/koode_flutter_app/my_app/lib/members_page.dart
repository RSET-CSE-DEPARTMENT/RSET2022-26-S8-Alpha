import 'dart:async';
import 'dart:io';

import 'package:audioplayers/audioplayers.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

import 'profile_page.dart';
import 'schedule_page.dart';
import 'services/api_service.dart';

class MembersPage extends StatefulWidget {
  const MembersPage({super.key});

  @override
  State<MembersPage> createState() => _MembersPageState();
}

class _MembersPageState extends State<MembersPage> {
  final TextEditingController _searchController = TextEditingController();
  List<_Member> _members = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadMembers();
  }

  Future<void> _loadMembers() async {
    final user = FirebaseAuth.instance.currentUser;
    final memberMap = <String, _Member>{};

    void upsertMember({
      required String name,
      required DateTime lastSeen,
      String? subtitle,
      String? description,
      int? recognizedCount,
    }) {
      final key = ApiService.normalizeMemberKey(name);
      if (key.isEmpty) return;

      final existing = memberMap[key];
      if (existing == null) {
        memberMap[key] = _Member(
          name: name,
          subtitle: subtitle ?? 'Ready for voice recognition',
          description: description ?? '',
          count: recognizedCount ?? 0,
          lastSeen: lastSeen,
        );
        return;
      }

      final mergedCount = recognizedCount ?? existing.count;
      final mergedLastSeen =
          lastSeen.isAfter(existing.lastSeen) ? lastSeen : existing.lastSeen;

      memberMap[key] = existing.copyWith(
        name: name,
        subtitle: subtitle ?? existing.subtitle,
        description: description ?? existing.description,
        count: mergedCount,
        lastSeen: mergedLastSeen,
      );
    }

    Future<void> collectFromQuery(
      Query<Map<String, dynamic>> query,
    ) async {
      final snapshot = await query.get();
      for (final doc in snapshot.docs) {
        final data = doc.data();
        final name = _extractSpeakerName(data);
        if (name.isEmpty || name == 'Unknown person') continue;

        final key = ApiService.normalizeMemberKey(name);
        final receivedAt = data['receivedAt'] as Timestamp?;
        final sentTime = data['sentTime'] as Timestamp?;
        final seenAt = (receivedAt ?? sentTime)?.toDate() ?? DateTime.now();
        final existing = memberMap[key];
        final updatedCount = (existing?.count ?? 0) + 1;
        upsertMember(
          name: name,
          subtitle: 'Recognized $updatedCount times',
          description: existing?.description ?? '',
          recognizedCount: updatedCount,
          lastSeen: seenAt,
        );
      }
    }

    try {
      if (user != null) {
        final knownSpeakers = await ApiService.getKnownSpeakers();
        final now = DateTime.now();
        for (final speaker in knownSpeakers) {
          final cleanedName = speaker.trim();
          if (cleanedName.isEmpty || cleanedName == 'Unknown person') continue;

          upsertMember(
            name: cleanedName,
            subtitle: 'Voice saved',
            description: '',
            recognizedCount: 0,
            lastSeen: now,
          );
        }
      }
    } catch (_) {}

    try {
      if (user != null) {
        final logsRef = FirebaseFirestore.instance
            .collection('notification')
            .doc(ApiService.notificationDocId)
            .collection('logs');
        await collectFromQuery(
          logsRef
              .where('alertType', isEqualTo: 'speaker')
              .where('userId', isEqualTo: user.uid),
        );

        final memberProfiles = await FirebaseFirestore.instance
            .collection('members')
            .where('userId', isEqualTo: user.uid)
            .get();

        for (final doc in memberProfiles.docs) {
          final data = doc.data();
          final name = (data['name'] ?? '').toString().trim();
          if (name.isEmpty) continue;

          final key = (data['normalizedName'] ?? ApiService.normalizeMemberKey(name))
              .toString();
          final description = (data['description'] ?? '').toString().trim();
          final updatedAt = (data['updatedAt'] as Timestamp?)?.toDate() ??
              (data['createdAt'] as Timestamp?)?.toDate() ??
              DateTime.now();
          final existing = memberMap[key];
          upsertMember(
            name: name,
            subtitle: existing?.subtitle ?? 'Ready for voice recognition',
            description: description,
            recognizedCount: existing?.count ?? 0,
            lastSeen: updatedAt,
          );
        }

      }
    } catch (_) {}

    try {
      if (memberMap.isEmpty) {
        final logsRef = FirebaseFirestore.instance
            .collection('notification')
            .doc(ApiService.notificationDocId)
            .collection('logs');
        await collectFromQuery(
          logsRef.where('alertType', isEqualTo: 'speaker'),
        );
      }

    } catch (_) {
      if (memberMap.isEmpty) {
        memberMap.clear();
      }
    }

    final loadedMembers = memberMap.values.toList()
      ..sort((a, b) => b.lastSeen.compareTo(a.lastSeen));

    if (!mounted) return;
    setState(() {
      _members = loadedMembers;
      _isLoading = false;
    });
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
    final speakingMatch = RegExp(
      r'^(.+?)\s+is speaking\.?$',
      caseSensitive: false,
    ).firstMatch(body);
    if (speakingMatch != null) {
      final candidate = (speakingMatch.group(1) ?? '').trim();
      if (candidate.isNotEmpty) return candidate;
    }

    if (body.toLowerCase().contains('unknown person')) {
      return 'Unknown person';
    }

    return '';
  }

  Future<void> _openAddMemberDialog() async {
    final created = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (_) => const _AddMemberDialog(),
    );

    if (created == true) {
      await _loadMembers();
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<_Member> get _filteredMembers {
    final q = _searchController.text.toLowerCase().trim();
    if (q.isEmpty) return _members;
    return _members
        .where(
          (m) =>
              m.name.toLowerCase().contains(q) ||
              m.subtitle.toLowerCase().contains(q) ||
              m.description.toLowerCase().contains(q),
        )
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xfff7f7f7),
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              child: Row(
                children: [
                  const Text(
                    'Members',
                    style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold),
                  ),
                  const Spacer(),
                  IconButton(
                    onPressed: _openAddMemberDialog,
                    icon: const Icon(Icons.add_circle_outline, size: 30),
                    tooltip: 'Add member',
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Container(
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(24),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withAlpha(13),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: TextField(
                  controller: _searchController,
                  onChanged: (_) => setState(() {}),
                  decoration: const InputDecoration(
                    hintText: 'Search',
                    prefixIcon: Icon(Icons.search),
                    border: InputBorder.none,
                    contentPadding: EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 12,
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : _filteredMembers.isEmpty
                      ? const Center(
                          child: Text(
                            'No known speakers found',
                            style: TextStyle(color: Colors.grey),
                          ),
                        )
                      : ListView.separated(
                          padding: const EdgeInsets.only(
                            left: 16,
                            right: 16,
                            bottom: 16,
                          ),
                          itemCount: _filteredMembers.length,
                          separatorBuilder: (context, index) => const Divider(
                            height: 1,
                            color: Color(0xffeeeeee),
                          ),
                          itemBuilder: (context, index) {
                            final m = _filteredMembers[index];
                            return _MemberTile(member: m);
                          },
                        ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: BottomNavigationBar(
        type: BottomNavigationBarType.fixed,
        currentIndex: 2,
        selectedItemColor: Colors.blue,
        unselectedItemColor: Colors.grey,
        onTap: (index) {
          if (index == 0) {
            Navigator.popUntil(context, (route) => route.isFirst);
          } else if (index == 1) {
            Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => SchedulePage()),
            );
          } else if (index == 3) {
            Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => const ProfilePage(
                  userName: 'Mr. Augustine',
                  imageUrl: '',
                ),
              ),
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

class _Member {
  final String name;
  final String subtitle;
  final String description;
  final int count;
  final DateTime lastSeen;

  const _Member({
    required this.name,
    required this.subtitle,
    required this.description,
    required this.count,
    required this.lastSeen,
  });

  _Member copyWith({
    String? name,
    String? subtitle,
    String? description,
    int? count,
    DateTime? lastSeen,
  }) {
    return _Member(
      name: name ?? this.name,
      subtitle: subtitle ?? this.subtitle,
      description: description ?? this.description,
      count: count ?? this.count,
      lastSeen: lastSeen ?? this.lastSeen,
    );
  }
}

class _MemberTile extends StatelessWidget {
  final _Member member;

  const _MemberTile({required this.member});

  @override
  Widget build(BuildContext context) {
    final subtitleLines = <String>[
      member.subtitle,
      if (member.description.isNotEmpty) member.description,
    ];

    return ListTile(
      contentPadding: const EdgeInsets.symmetric(vertical: 8),
      leading: CircleAvatar(
        radius: 28,
        backgroundColor: Colors.grey.shade300,
        child: Text(
          member.name.isNotEmpty ? member.name[0] : '?',
          style: const TextStyle(
            fontSize: 22,
            fontWeight: FontWeight.bold,
            color: Colors.white,
          ),
        ),
      ),
      title: Text(
        member.name,
        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
      ),
      subtitle: Text(
        subtitleLines.join('\n'),
        style: const TextStyle(fontSize: 13, color: Colors.grey),
      ),
    );
  }
}

enum _EnrollmentSource { phone, iot }

class _AddMemberDialog extends StatefulWidget {
  const _AddMemberDialog();

  @override
  State<_AddMemberDialog> createState() => _AddMemberDialogState();
}

class _AddMemberDialogState extends State<_AddMemberDialog> {
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _descriptionController = TextEditingController();
  final AudioRecorder _recorder = AudioRecorder();
  final AudioPlayer _player = AudioPlayer();

  _EnrollmentSource _source = _EnrollmentSource.phone;
  Timer? _recordTimer;
  Timer? _iotPollTimer;
  String? _recordedPath;
  Duration _recordDuration = Duration.zero;
  bool _isRecording = false;
  bool _isPaused = false;
  bool _isPlaying = false;
  bool _isSaving = false;
  bool _iotStarted = false;
  bool _iotCompleted = false;
  String _iotStatusText = 'Waiting to start IoT microphone capture';

  @override
  void initState() {
    super.initState();
    _player.onPlayerComplete.listen((_) {
      if (!mounted) return;
      setState(() {
        _isPlaying = false;
      });
    });
  }

  @override
  void dispose() {
    _recordTimer?.cancel();
    _iotPollTimer?.cancel();
    _nameController.dispose();
    _descriptionController.dispose();
    _player.dispose();
    _recorder.dispose();
    super.dispose();
  }

  Future<void> _startPhoneRecording() async {
    final hasPermission = await _recorder.hasPermission();
    if (!hasPermission) {
      _showMessage('Microphone permission is required.');
      return;
    }

    final tempDir = await getTemporaryDirectory();
    final path =
        '${tempDir.path}/member_${DateTime.now().millisecondsSinceEpoch}.wav';

    await _player.stop();
    await _recorder.start(
      const RecordConfig(
        encoder: AudioEncoder.wav,
        sampleRate: 16000,
        numChannels: 1,
      ),
      path: path,
    );

    _recordTimer?.cancel();
    _recordTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      setState(() {
        if (!_isPaused) {
          _recordDuration += const Duration(seconds: 1);
        }
      });
    });

    setState(() {
      _recordedPath = null;
      _recordDuration = Duration.zero;
      _isRecording = true;
      _isPaused = false;
      _isPlaying = false;
    });
  }

  Future<void> _pauseOrResumePhoneRecording() async {
    if (!_isRecording) return;

    if (_isPaused) {
      await _recorder.resume();
    } else {
      await _recorder.pause();
    }

    if (!mounted) return;
    setState(() {
      _isPaused = !_isPaused;
    });
  }

  Future<void> _stopPhoneRecording() async {
    final path = await _recorder.stop();
    _recordTimer?.cancel();

    if (!mounted) return;
    setState(() {
      _recordedPath = path;
      _isRecording = false;
      _isPaused = false;
    });
  }

  Future<void> _togglePlayback() async {
    final path = _recordedPath;
    if (path == null) return;

    if (_isPlaying) {
      await _player.pause();
      if (!mounted) return;
      setState(() {
        _isPlaying = false;
      });
      return;
    }

    await _player.play(DeviceFileSource(path));
    if (!mounted) return;
    setState(() {
      _isPlaying = true;
    });
  }

  Future<void> _startIotEnrollment() async {
    final name = _nameController.text.trim();
    if (name.isEmpty) {
      _showMessage('Enter the member name before starting IoT capture.');
      return;
    }

    final started = await ApiService.startIotMemberEnrollment(memberName: name);
    if (!started) {
      _showMessage('Unable to start IoT microphone capture.');
      return;
    }

    _iotPollTimer?.cancel();
    _iotPollTimer = Timer.periodic(
      const Duration(seconds: 2),
      (_) => _pollIotStatus(),
    );
    await _pollIotStatus();

    if (!mounted) return;
    setState(() {
      _iotStarted = true;
      _iotCompleted = false;
      _iotStatusText = 'Listening from the IoT microphone...';
    });
  }

  Future<void> _pollIotStatus() async {
    final status = await ApiService.getIotMemberEnrollmentStatus();
    if (status == null || !mounted) return;

    final state = (status['status'] ?? 'idle').toString();
    final collected = (status['collectedWindows'] ?? 0) as int;
    final target = (status['targetWindows'] ?? 0) as int;
    final error = (status['error'] ?? '').toString();

    if (state == 'completed') {
      _iotPollTimer?.cancel();
      setState(() {
        _iotCompleted = true;
        _iotStatusText = 'IoT voice capture completed.';
      });
      return;
    }

    if (state == 'failed') {
      _iotPollTimer?.cancel();
      setState(() {
        _iotStarted = false;
        _iotCompleted = false;
        _iotStatusText =
            error.isEmpty ? 'IoT capture failed.' : 'IoT capture failed: $error';
      });
      return;
    }

    setState(() {
      _iotStatusText = target > 0
          ? 'Listening from the IoT microphone... $collected / $target'
          : 'Listening from the IoT microphone...';
    });
  }

  Future<void> _saveMember() async {
    final name = _nameController.text.trim();
    final description = _descriptionController.text.trim();

    if (name.isEmpty) {
      _showMessage('Member name is required.');
      return;
    }

    setState(() {
      _isSaving = true;
    });

    bool success = false;

    if (_source == _EnrollmentSource.phone) {
      final path = _recordedPath;
      if (path == null) {
        _showMessage('Record the member voice first.');
        setState(() {
          _isSaving = false;
        });
        return;
      }

      success = await ApiService.enrollMemberFromPhone(
        audioFile: File(path),
        memberName: name,
        description: description,
      );
    } else {
      if (!_iotCompleted) {
        _showMessage('Finish IoT microphone capture before saving.');
        setState(() {
          _isSaving = false;
        });
        return;
      }

      try {
        success = await ApiService.completeIotMemberEnrollment(
          memberName: name,
          description: description,
        );
      } catch (_) {
        success = false;
      }
    }

    if (!mounted) return;
    setState(() {
      _isSaving = false;
    });

    if (!success) {
      _showMessage('Unable to save the member.');
      return;
    }

    Navigator.of(context).pop(true);
  }

  void _showMessage(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  String _formatDuration(Duration value) {
    final minutes = value.inMinutes.remainder(60).toString().padLeft(2, '0');
    final seconds = value.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Add Member',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            SegmentedButton<_EnrollmentSource>(
              segments: const [
                ButtonSegment(
                  value: _EnrollmentSource.phone,
                  label: Text('Phone'),
                  icon: Icon(Icons.phone_iphone),
                ),
                ButtonSegment(
                  value: _EnrollmentSource.iot,
                  label: Text('IoT Mic'),
                  icon: Icon(Icons.mic_external_on),
                ),
              ],
              selected: {_source},
              onSelectionChanged: _isSaving
                  ? null
                  : (selection) {
                      setState(() {
                        _source = selection.first;
                      });
                    },
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _nameController,
              onChanged: (_) => setState(() {}),
              decoration: const InputDecoration(
                labelText: 'Member name',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _descriptionController,
              maxLines: 3,
              decoration: const InputDecoration(
                labelText: 'Description',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xfff4f7fb),
                borderRadius: BorderRadius.circular(16),
              ),
              child: _source == _EnrollmentSource.phone
                  ? Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Record with phone microphone',
                          style: TextStyle(fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          _isRecording
                              ? 'Recording ${_formatDuration(_recordDuration)}'
                              : _recordedPath == null
                                  ? 'Record the new member voice sample.'
                                  : 'Voice sample ready.',
                        ),
                        const SizedBox(height: 12),
                        Wrap(
                          spacing: 12,
                          runSpacing: 12,
                          children: [
                            FilledButton.icon(
                              onPressed:
                                  _isSaving || _isRecording ? null : _startPhoneRecording,
                              icon: const Icon(Icons.fiber_manual_record),
                              label: const Text('Record'),
                            ),
                            OutlinedButton.icon(
                              onPressed: _isSaving || !_isRecording
                                  ? null
                                  : _pauseOrResumePhoneRecording,
                              icon: Icon(_isPaused ? Icons.play_arrow : Icons.pause),
                              label: Text(_isPaused ? 'Resume' : 'Pause'),
                            ),
                            OutlinedButton.icon(
                              onPressed:
                                  _isSaving || !_isRecording ? null : _stopPhoneRecording,
                              icon: const Icon(Icons.stop),
                              label: const Text('Stop'),
                            ),
                            OutlinedButton.icon(
                              onPressed:
                                  _isSaving || _recordedPath == null ? null : _togglePlayback,
                              icon: Icon(_isPlaying ? Icons.pause_circle : Icons.play_arrow),
                              label: Text(_isPlaying ? 'Pause audio' : 'Play audio'),
                            ),
                          ],
                        ),
                      ],
                    )
                  : Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Capture with IoT microphone',
                          style: TextStyle(fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 8),
                        Text(_iotStatusText),
                        const SizedBox(height: 12),
                        FilledButton.icon(
                          onPressed:
                              _isSaving || _iotStarted || _nameController.text.trim().isEmpty
                                  ? null
                                  : _startIotEnrollment,
                          icon: const Icon(Icons.mic),
                          label: const Text('Start capture'),
                        ),
                      ],
                    ),
            ),
            const SizedBox(height: 20),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  onPressed: _isSaving ? null : () => Navigator.of(context).pop(false),
                  child: const Text('Cancel'),
                ),
                const SizedBox(width: 8),
                FilledButton(
                  onPressed: _isSaving ? null : _saveMember,
                  child: _isSaving
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Save member'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
