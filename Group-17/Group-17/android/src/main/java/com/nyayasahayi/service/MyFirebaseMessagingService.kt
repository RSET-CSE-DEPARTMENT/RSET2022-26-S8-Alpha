//package com.nyayasahayi.service
//
//import android.util.Log
//import com.google.firebase.messaging.FirebaseMessagingService
//import com.google.firebase.messaging.RemoteMessage
//import com.nyayasahayi.data.AppDatabase
//import com.nyayasahayi.data.LocalCase
//import kotlinx.coroutines.CoroutineScope
//import kotlinx.coroutines.Dispatchers
//import kotlinx.coroutines.launch
//
//class MyFirebaseMessagingService : FirebaseMessagingService() {
//
//    override fun onMessageReceived(remoteMessage: RemoteMessage) {
//        // Handle data payload of FCM messages.
//        Log.d("FCM", "From: ${remoteMessage.from}")
//
//        // Check if message contains data payload.
//        if (remoteMessage.data.isNotEmpty()) {
//            Log.d("FCM", "Message data payload: ${remoteMessage.data}")
//            handleNow(remoteMessage.data)
//        }
//    }
//
//    private fun handleNow(data: Map<String, String>) {
//         if (data["type"] == "CASE_UPDATE") {
//             val cnr = data["cnr_number"] ?: return
//             val status = data["status"]
//             val nextDate = data["new_next_date"]
//
//             // Update Local DB
//             CoroutineScope(Dispatchers.IO).launch {
//                 val db = AppDatabase.getDatabase(applicationContext)
//                 // Fetch existing or create new? Assuming update existing mainly.
//                 val existingCase = db.appDao().getCaseByCnr(cnr)
//                 if (existingCase != null) {
//                     val updatedCase = existingCase.copy(
//                         status = status ?: existingCase.status,
//                         nextDate = nextDate ?: existingCase.nextDate,
//                         lastUpdatedAt = System.currentTimeMillis().toString()
//                     )
//                     db.appDao().insertCase(updatedCase)
//                     Log.d("FCM", "Case updated locally: $cnr")
//                 }
//             }
//         }
//    }
//
//    override fun onNewToken(token: String) {
//        Log.d("FCM", "Refreshed token: $token")
//        // Send token to server
//    }
//}

package com.nyayasahayi.service // Use your package name

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import com.nyayasahayi.ui.MainActivity
import com.nyayasahayi.R
import kotlin.random.Random

class MyFirebaseMessagingService : FirebaseMessagingService() {

    // 1. Called when a new token is generated (e.g., on fresh install)
    override fun onNewToken(token: String) {
        super.onNewToken(token)
        Log.d("FCM", "Refreshed token: $token")
        // TODO: Send this token to your backend server so it knows who to send messages to
    }

    // 2. Called when a message is received
//    override fun onMessageReceived(remoteMessage: RemoteMessage) {
//        super.onMessageReceived(remoteMessage)
//
//        // Check if message contains a data payload (silently handled)
//        if (remoteMessage.data.isNotEmpty()) {
//            Log.d("FCM", "Message data payload: ${remoteMessage.data}")
//            // Handle data (e.g., update local database)
//        }
//
//        // Check if message contains a notification payload (visible to user)
//        remoteMessage.notification?.let {
//            showNotification(it.title ?: "Update", it.body ?: "New case update received")
//        }
//    }
    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        super.onMessageReceived(remoteMessage)

        // 1. Extract the real JSON data payload
        if (remoteMessage.data.isNotEmpty()) {
            val payload = remoteMessage.data.toString()

            // 2. SEND TO COMPOSE UI IN REAL-TIME
            FcmMessageRepository.addMessage("Payload Received: $payload")
        }

        // (Keep your existing notification code here if you want system tray alerts too)
        remoteMessage.notification?.let {
            FcmMessageRepository.addMessage("Notification: ${it.title} - ${it.body}")
        }
    }

    private fun showNotification(title: String, message: String) {
        val channelId = "case_updates_channel"

        // Intent to open when notification is clicked
        val intent = Intent(this, MainActivity::class.java).apply {
            addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP)
        }

        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_ONE_SHOT or PendingIntent.FLAG_IMMUTABLE
        )

        // Create Channel (Required for Android 8.0+)
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                "Case Updates",
                NotificationManager.IMPORTANCE_HIGH
            )
            notificationManager.createNotificationChannel(channel)
        }

        val notificationBuilder = NotificationCompat.Builder(this, channelId)
            .setSmallIcon(R.drawable.client_background) // Ensure you have a valid icon here
            .setContentTitle(title)
            .setContentText(message)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)

        notificationManager.notify(Random.nextInt(), notificationBuilder.build())
    }
}
