package com.nyayasahayi.service

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.telephony.TelephonyManager
import android.util.Log
import kotlinx.coroutines.launch

class CallReceiver : BroadcastReceiver() {

    companion object {
        private const val TAG = "CallReceiver"
        private var isIncoming = false
        private var isAnswered = false
        private var lastIncomingNumber: String? = null
    }

    override fun onReceive(context: Context, intent: Intent) {
        Log.d(TAG, "onReceive() called - Action: ${intent.action}")
        
        if (intent.action == TelephonyManager.ACTION_PHONE_STATE_CHANGED) {
            val state = intent.getStringExtra(TelephonyManager.EXTRA_STATE)
            Log.d(TAG, "Phone state changed to: $state")
            
            if (state == TelephonyManager.EXTRA_STATE_RINGING) {
                isIncoming = true
                isAnswered = false
                val incomingNumber = intent.getStringExtra(TelephonyManager.EXTRA_INCOMING_NUMBER)
                lastIncomingNumber = incomingNumber
                
                Log.d(TAG, "RINGING detected - Incoming number: ${incomingNumber ?: "NULL"}")

                if (!incomingNumber.isNullOrEmpty()) {
                    Log.d(TAG, "Starting OverlayService for number: $incomingNumber")
                    val serviceIntent = Intent(context,
                        OverlayService::class.java).apply {
                        putExtra("PHONE_NUMBER", incomingNumber)
                    }
                    
                    try {
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                            context.startForegroundService(serviceIntent)
                        } else {
                            context.startService(serviceIntent)
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "Failed to start service", e)
                    }
                }
            } else if (state == TelephonyManager.EXTRA_STATE_OFFHOOK) {
                if (isIncoming) {
                    isAnswered = true
                    Log.d(TAG, "Call answered (OFFHOOK)")
                }
            } else if (state == TelephonyManager.EXTRA_STATE_IDLE) {
                Log.d(TAG, "Call ended (IDLE)")
                
                // Stop Overlay
                val serviceIntent = Intent(context, OverlayService::class.java)
                context.stopService(serviceIntent)
                Log.d(TAG, "Overlay stopped")

                // Check for Missed Call
                if (isIncoming && !isAnswered) {
                    val number = lastIncomingNumber
                    Log.d(TAG, "Missed call detected from: $number")
                    
                    if (!number.isNullOrEmpty()) {
                        handleMissedCall(context, number)
                    }
                }
                
                // Reset state
                isIncoming = false
                isAnswered = false
                lastIncomingNumber = null
            }
        }
    }

    private fun handleMissedCall(context: Context, phoneNumber: String) {
        val pendingResult = goAsync()
        val asyncScope = kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.Dispatchers.IO)
        
        asyncScope.launch {
            try {
                Log.d(TAG, "Checking database for missed call number: $phoneNumber")
                val db = com.nyayasahayi.data.AppDatabase.getDatabase(context)
                val client = db.appDao().getClientByPhone(phoneNumber)
                
                if (client != null) {
                    Log.d(TAG, "Client found: ${client.name}. Sending SMS...")
                    sendSms(phoneNumber)
                } else {
                    Log.d(TAG, "Number not found in database. No SMS sent.")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error handling missed call", e)
            } finally {
                pendingResult.finish()
            }
        }
    }

    private fun sendSms(phoneNumber: String) {
        try {
            val smsManager = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                android.telephony.SmsManager.getDefault()
            } else {
                android.telephony.SmsManager.getDefault()
            }
            
            // "uniquelink" placeholder as requested
            val message = "Could not answer the call. Visit the link for more details : https://nyayasahayi-sms.netlify.app/?token=testclient"
            smsManager.sendTextMessage(phoneNumber, null, message, null, null)
            Log.d(TAG, "SMS sent to $phoneNumber: $message")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to send SMS", e)
        }
    }
}
