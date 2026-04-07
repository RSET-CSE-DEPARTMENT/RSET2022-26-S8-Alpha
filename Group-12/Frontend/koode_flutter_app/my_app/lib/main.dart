import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';
import 'dart:io';

import 'firebase_options.dart';
import 'auth_page.dart';
import 'services/api_service.dart';

/* ===================== LOCAL NOTIFICATIONS ===================== */

final FlutterLocalNotificationsPlugin flutterLocalNotificationsPlugin =
    FlutterLocalNotificationsPlugin();

const String _notificationCollection = 'notification';
const String _notificationDocId = 'OaHeJSTziygJ8JWkepyG';
const String _notificationLogsSubcollection = 'logs';
String? _lastSuccessfulTokenRegistrationKey;
String? _tokenRegistrationInFlightKey;

String _detectAlertType(RemoteMessage message) {
  final data = message.data;
  final rawType = (data['alertType'] ?? data['type'] ?? '')
      .toString()
      .toLowerCase()
      .trim();

  if (rawType.contains('fall')) {
    return 'fall';
  }
  if (rawType.contains('geofence') || rawType.contains('fence')) {
    return 'geofence';
  }
  if (rawType.contains('speaker') || rawType.contains('voice')) {
    return 'speaker';
  }

  final title = (message.notification?.title ?? '').toLowerCase();
  final body = (message.notification?.body ?? '').toLowerCase();

  final combinedText = '$title $body';
  if (combinedText.contains('fall')) {
    return 'fall';
  }
  if (combinedText.contains('geofence') ||
      combinedText.contains('safe zone') ||
      combinedText.contains('fence')) {
    return 'geofence';
  }
  if (combinedText.contains('speaker') ||
      combinedText.contains('voice') ||
      combinedText.contains('speaking') ||
      combinedText.contains('unknown person')) {
    return 'speaker';
  }

  return 'unknown';
}

Future<void> _storeNotificationLog(
  RemoteMessage message, {
  required String deliveryEvent,
}) async {
  try {
    final currentUser = FirebaseAuth.instance.currentUser;
    if (currentUser == null || currentUser.isAnonymous) {
      return;
    }

    final alertType = _detectAlertType(message);
    if (alertType == 'unknown') {
      return;
    }

    final data = message.data;
    final payloadUserId =
        (data['userId'] ?? data['firebaseUid'] ?? '').toString().trim();
    if (payloadUserId.isNotEmpty && payloadUserId != currentUser.uid) {
      return;
    }

    final title = message.notification?.title ?? '';
    final body = message.notification?.body ?? '';

    await FirebaseFirestore.instance
        .collection(_notificationCollection)
        .doc(_notificationDocId)
        .collection(_notificationLogsSubcollection)
        .add({
      'alertType': alertType,
      'deliveryEvent': deliveryEvent,
      'userId': currentUser.uid,
      'firebaseUid': currentUser.uid,
      'messageId': message.messageId,
      'title': title,
      'body': body,
      'data': data,
      'sentTime': message.sentTime == null
          ? null
          : Timestamp.fromDate(message.sentTime!.toUtc()),
      'receivedAt': FieldValue.serverTimestamp(),
      'platform': 'flutter_app',
      'notificationLogged': true,
    });
  } catch (e) {
    print('❌ Failed to store notification log: $e');
  }
}

Future<void> initializeLocalNotifications() async {
  const AndroidInitializationSettings androidSettings =
      AndroidInitializationSettings('@mipmap/ic_launcher');

  const InitializationSettings initSettings =
      InitializationSettings(android: androidSettings);

  await flutterLocalNotificationsPlugin.initialize(initSettings);
}

Future<void> setupNotificationChannel() async {
  const AndroidNotificationChannel channel = AndroidNotificationChannel(
    'high_importance_channel',
    'High Importance Notifications',
    description: 'Used for fall and geofence alerts',
    importance: Importance.high,
  );

  await flutterLocalNotificationsPlugin
      .resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin>()
      ?.createNotificationChannel(channel);
}

/* ===================== FOREGROUND HANDLER ===================== */

void setupFirebaseForegroundListener() {
  FirebaseMessaging.onMessage.listen((RemoteMessage message) async {
    final notification = message.notification;
    final android = message.notification?.android;

    await _storeNotificationLog(
      message,
      deliveryEvent: 'received_foreground',
    );

    if (notification != null && android != null) {
      flutterLocalNotificationsPlugin.show(
        notification.hashCode,
        notification.title,
        notification.body,
        const NotificationDetails(
          android: AndroidNotificationDetails(
            'high_importance_channel',
            'High Importance Notifications',
            importance: Importance.high,
            priority: Priority.high,
            icon: '@mipmap/ic_launcher',
          ),
        ),
      );
    }
  });
}

/* ===================== BACKGROUND HANDLER ===================== */

@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );

  print('🔔 Background message: ${message.notification?.title}');
  await _storeNotificationLog(
    message,
    deliveryEvent: 'received_background',
  );
}

/* ===================== SEND TOKEN TO FLASK ===================== */

Future<bool> sendTokenToServer({
  required String token,
  required String userId,
}) async {
  final uri = Uri.parse('${ApiService.baseUrl}/register_token');

  try {
    final response = await http
        .post(
      uri,
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({
        "token": token,
        "userId": userId,
        "platform": "flutter_app",
      }),
    )
        .timeout(const Duration(seconds: 10));

    if (response.statusCode >= 200 && response.statusCode < 300) {
      print(
        '📡 Token registered for user $userId '
        '(status=${response.statusCode})',
      );
      return true;
    }

    print(
      '❌ Token registration failed '
      '(status=${response.statusCode}, body=${response.body})',
    );
    return false;
  } on TimeoutException {
    print('❌ Token registration timed out after 10s for $uri');
    return false;
  } on SocketException catch (e) {
    print('❌ Could not reach $uri: $e');
    return false;
  } on HttpException catch (e) {
    print('❌ HTTP error while sending token to $uri: $e');
    return false;
  } catch (e) {
    print('❌ Failed to send token to $uri: $e');
    return false;
  }
}

Future<void> _registerFcmTokenForCurrentUser() async {
  final user = FirebaseAuth.instance.currentUser;
  if (user == null || user.isAnonymous) return;

  final token = await FirebaseMessaging.instance.getToken();
  if (token == null || token.isEmpty) return;

  final registrationKey = '${user.uid}:$token';
  if (_lastSuccessfulTokenRegistrationKey == registrationKey ||
      _tokenRegistrationInFlightKey == registrationKey) {
    return;
  }

  _tokenRegistrationInFlightKey = registrationKey;

  final didRegister = await sendTokenToServer(
    token: token,
    userId: user.uid,
  );

  if (didRegister) {
    _lastSuccessfulTokenRegistrationKey = registrationKey;
  }

  if (_tokenRegistrationInFlightKey == registrationKey) {
    _tokenRegistrationInFlightKey = null;
  }
}

/* ===================== MAIN ===================== */

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // 🔥 Firebase init
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );

  // 🔔 Local notifications
  await initializeLocalNotifications();
  await setupNotificationChannel();
  setupFirebaseForegroundListener();

  // 🔔 Background handler
  FirebaseMessaging.onBackgroundMessage(
    firebaseMessagingBackgroundHandler,
  );

  // 📡 Firebase Messaging
  FirebaseMessaging messaging = FirebaseMessaging.instance;

  // 🔔 Permissions
  NotificationSettings settings = await messaging.requestPermission(
    alert: true,
    badge: true,
    sound: true,
  );

  print('🔔 Permission status: ${settings.authorizationStatus}');

  // Register token for already signed-in user (if any)
  unawaited(_registerFcmTokenForCurrentUser());

  // Re-register token whenever Firebase rotates it.
  FirebaseMessaging.instance.onTokenRefresh.listen((token) async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null || user.isAnonymous) return;
    unawaited(
      sendTokenToServer(
        token: token,
        userId: user.uid,
      ),
    );
  });

  // Register token immediately after user signs in.
  FirebaseAuth.instance.authStateChanges().listen((user) async {
    if (user == null || user.isAnonymous) return;
    unawaited(_registerFcmTokenForCurrentUser());
  });

  FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) async {
    await _storeNotificationLog(
      message,
      deliveryEvent: 'opened_from_background',
    );
  });

  final initialMessage = await FirebaseMessaging.instance.getInitialMessage();
  if (initialMessage != null) {
    await _storeNotificationLog(
      initialMessage,
      deliveryEvent: 'opened_from_terminated',
    );
  }

  runApp(const MyApp());
}

/* ===================== APP ===================== */

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Medication App',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        primarySwatch: Colors.blue,
        fontFamily: 'Inter',
      ),
      home: const AuthPage(),
    );
  }
}
