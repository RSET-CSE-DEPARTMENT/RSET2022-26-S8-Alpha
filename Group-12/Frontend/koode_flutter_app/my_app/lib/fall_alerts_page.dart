import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../models/fall_alert_model.dart';
import '../services/api_service.dart';

class FallAlertsPage extends StatefulWidget {
  const FallAlertsPage({Key? key}) : super(key: key);

  @override
  State<FallAlertsPage> createState() => _FallAlertsPageState();
}

class _FallAlertsPageState extends State<FallAlertsPage> {
  final FirebaseAuth _auth = FirebaseAuth.instance;
  late Stream<List<FallAlert>> _alertsStream;
  bool _filterUnacknowledged = false;

  @override
  void initState() {
    super.initState();
    _setupStream();
  }

  void _setupStream() {
    final userId = _auth.currentUser?.uid ?? '';
    if (userId.isEmpty) {
      _alertsStream = const Stream<List<FallAlert>>.empty();
      return;
    }
    _alertsStream = ApiService.streamFallAlerts(userId);

  }

  Future<void> _acknowledgeAlert(FallAlert alert) async {
    final success = await ApiService.acknowledgeFallAlert(alert.id);
    if (success && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Alert acknowledged')),
      );
    }
  }

  Future<void> _deleteAlert(FallAlert alert) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Alert'),
        content: const Text('Are you sure you want to delete this alert?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      final success = await ApiService.deleteFallAlert(alert.id);
      if (success && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Alert deleted')),
        );
      }
    }
  }

  void _showAlertDetails(FallAlert alert) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Fall Alert Details',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: () => Navigator.pop(context),
                ),
              ],
            ),
            const SizedBox(height: 16),
            _DetailRow(
              label: 'Device',
              value: alert.deviceId,
            ),
            _DetailRow(
              label: 'Confidence',
              value: alert.getConfidencePercentage(),
            ),
            _DetailRow(
              label: 'Time',
              value: alert.timestamp.toString().split('.')[0],
            ),
            _DetailRow(
              label: 'Status',
              value: alert.getStatus(),
            ),
            if (alert.reasoning.isNotEmpty) ...[
              const SizedBox(height: 16),
              Text(
                'Detection Reasons:',
                style: Theme.of(context).textTheme.titleSmall,
              ),
              const SizedBox(height: 8),
              ...alert.reasoning.map((reason) => Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Row(
                      children: [
                        const Text('• ', style: TextStyle(fontSize: 16)),
                        Expanded(child: Text(reason)),
                      ],
                    ),
                  )),
            ],
            const SizedBox(height: 24),
            if (!alert.acknowledged && alert.isFall)
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () {
                    _acknowledgeAlert(alert);
                    Navigator.pop(context);
                  },
                  child: const Text('Acknowledge Alert'),
                ),
              ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Fall Alerts'),
        centerTitle: true,
        elevation: 0,
        actions: [
          IconButton(
            icon: Icon(
              _filterUnacknowledged ? Icons.filter_list : Icons.filter_list_off,
              color: _filterUnacknowledged ? Colors.blue : null,
            ),
            onPressed: () {
              setState(() {
                _filterUnacknowledged = !_filterUnacknowledged;
              });
            },
            tooltip: _filterUnacknowledged
                ? 'Show all alerts'
                : 'Show unacknowledged only',
          ),
        ],
      ),
      body: StreamBuilder<List<FallAlert>>(
        stream: _alertsStream,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.error, size: 48, color: Colors.red),
                  const SizedBox(height: 16),
                  Text('Error: ${snapshot.error}'),
                ],
              ),
            );
          }

          var alerts = snapshot.data ?? [];

          // Apply filter
          if (_filterUnacknowledged) {
            alerts = alerts.where((a) => !a.acknowledged && a.isFall).toList();
          }

          if (alerts.isEmpty) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    _filterUnacknowledged
                        ? Icons.check_circle
                        : Icons.notifications_none,

                    size: 64,
                    color: Colors.grey[400],
                  ),
                  const SizedBox(height: 16),
                  Text(
                    _filterUnacknowledged
                        ? 'No unacknowledged alerts'
                        : 'No fall alerts',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ],
              ),
            );
          }

          return ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: alerts.length,
            itemBuilder: (context, index) {
              final alert = alerts[index];
              return _FallAlertCard(
                alert: alert,
                onTap: () => _showAlertDetails(alert),
                onAcknowledge: () => _acknowledgeAlert(alert),
                onDelete: () => _deleteAlert(alert),
              );
            },
          );
        },
      ),
    );
  }
}

/// Reusable fall alert card widget
class _FallAlertCard extends StatelessWidget {
  final FallAlert alert;
  final VoidCallback onTap;
  final VoidCallback onAcknowledge;
  final VoidCallback onDelete;

  const _FallAlertCard({
    required this.alert,
    required this.onTap,
    required this.onAcknowledge,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final isFallDetected = alert.isFall;
    final isAcknowledged = alert.acknowledged;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header with status
              Row(
                children: [
                  // Icon based on status
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: isFallDetected
                          ? Colors.red.withOpacity(0.1)
                          : Colors.green.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Icon(
                      isFallDetected ? Icons.warning : Icons.check,
                      color:
                          isFallDetected ? Colors.red : Colors.green,
                      size: 24,
                    ),
                  ),
                  const SizedBox(width: 12),
                  // Title and status
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          isFallDetected ? '⚠️ Fall Detected' : '✓ No Fall',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          isAcknowledged ? 'Acknowledged' : 'Unacknowledged',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                color: isAcknowledged ? Colors.grey : Colors.orange,
                                fontWeight: FontWeight.w600,
                              ),
                        ),
                      ],
                    ),
                  ),
                  // Confidence badge
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: _getConfidenceColor(alert.confidence),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      alert.getConfidencePercentage(),
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              // Device and time info
              Row(
                children: [
                  Icon(Icons.devices, size: 16, color: Colors.grey[600]),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      alert.deviceId,
                      style: Theme.of(context).textTheme.bodySmall,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 16),
                  Icon(Icons.access_time, size: 16, color: Colors.grey[600]),
                  const SizedBox(width: 8),
                  Text(
                    alert.getFormattedTime(),
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
              const SizedBox(height: 12),
              // Action buttons
              if (isFallDetected && !isAcknowledged)
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: onAcknowledge,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.blue,
                    ),
                    child: const Text('Acknowledge'),
                  ),
                )
              else
                SizedBox(
                  width: double.infinity,
                  child: TextButton(
                    onPressed: onDelete,
                    child: const Text('Delete'),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Color _getConfidenceColor(double confidence) {
    if (confidence >= 0.8) return Colors.red;
    if (confidence >= 0.6) return Colors.orange;
    if (confidence >= 0.4) return Colors.amber;
    return Colors.yellow;
  }
}

/// Detail row widget for alert details
class _DetailRow extends StatelessWidget {
  final String label;
  final String value;

  const _DetailRow({
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: Theme.of(context).textTheme.labelMedium,
          ),
          Expanded(
            child: Text(
              value,
              textAlign: TextAlign.end,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
        ],
      ),
    );
  }
}
