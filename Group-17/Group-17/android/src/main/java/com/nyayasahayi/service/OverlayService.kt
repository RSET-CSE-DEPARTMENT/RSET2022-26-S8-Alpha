package com.nyayasahayi.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.PixelFormat
import android.os.Build
import android.os.IBinder
import android.util.Log
import android.view.Gravity
import android.view.View
import android.view.WindowManager
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.platform.ComposeView
import androidx.compose.ui.platform.ViewCompositionStrategy
import androidx.core.app.NotificationCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.LifecycleRegistry
import androidx.lifecycle.ViewModelStore
import androidx.lifecycle.ViewModelStoreOwner
import androidx.lifecycle.setViewTreeLifecycleOwner
import androidx.lifecycle.setViewTreeViewModelStoreOwner
import androidx.savedstate.SavedStateRegistry
import androidx.savedstate.SavedStateRegistryController
import androidx.savedstate.SavedStateRegistryOwner
import androidx.savedstate.setViewTreeSavedStateRegistryOwner
import com.nyayasahayi.R
import com.nyayasahayi.data.AppDatabase
import com.nyayasahayi.ui.CallOverlay
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlin.math.roundToInt

class OverlayService : Service(), LifecycleOwner, ViewModelStoreOwner, SavedStateRegistryOwner {

    private lateinit var windowManager: WindowManager
    private var overlayView: View? = null
    private var layoutParams: WindowManager.LayoutParams? = null
    
    private val serviceScope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    // Lifecycle and State management
    private val lifecycleRegistry = LifecycleRegistry(this)
    private val savedStateRegistryController = SavedStateRegistryController.create(this)
    private val store = ViewModelStore()

    // Compose State
    private val clientNameState = mutableStateOf("Loading...")
    private val caseStatusState = mutableStateOf("...")
    private val nextDateState = mutableStateOf("...")

    companion object {
        private const val TAG = "OverlayService"
        private const val CHANNEL_ID = "OverlayServiceChannel"
        private const val NOTIFICATION_ID = 1001
    }

    override val lifecycle: Lifecycle get() = lifecycleRegistry
    override val savedStateRegistry: SavedStateRegistry get() = savedStateRegistryController.savedStateRegistry
    override val viewModelStore: ViewModelStore get() = store

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        savedStateRegistryController.performRestore(null)
        lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_CREATE)
        
        Log.d(TAG, "onCreate() called")
        windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        
        createNotificationChannel()
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startForeground(
                NOTIFICATION_ID, 
                createNotification(), 
                ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE
            )
        } else {
            startForeground(NOTIFICATION_ID, createNotification())
        }
        
        lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_START)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val phoneNumber = intent?.getStringExtra("PHONE_NUMBER")
        Log.d(TAG, "onStartCommand() - Phone number: $phoneNumber")

        if (!phoneNumber.isNullOrEmpty()) {
            showOverlay(phoneNumber)
        }

        return START_NOT_STICKY
    }

    private fun showOverlay(phoneNumber: String) {
        if (overlayView != null) {
            // If already showing, just update the data
            queryClientInfo(phoneNumber)
            return
        }

        try {
            val composeView = ComposeView(this).apply {
                setViewTreeLifecycleOwner(this@OverlayService)
                setViewTreeViewModelStoreOwner(this@OverlayService)
                setViewTreeSavedStateRegistryOwner(this@OverlayService)
                
                // Dispose composition when view is detached
                setViewCompositionStrategy(ViewCompositionStrategy.DisposeOnViewTreeLifecycleDestroyed)
            }

            composeView.setContent {
                CallOverlay(
                    clientName = clientNameState.value,
                    caseStatus = caseStatusState.value,
                    nextHearingDate = nextDateState.value,
                    onClose = { stopSelf() },
                    onWindowDrag = { dragAmount ->
                        val params = layoutParams
                        if (params != null) {
                            params.x += dragAmount.x.roundToInt()
                            params.y += dragAmount.y.roundToInt()
                            try {
                                windowManager.updateViewLayout(composeView, params)
                            } catch (e: Exception) {
                                Log.e(TAG, "Error updating overlay layout", e)
                            }
                        }
                    }
                )
            }

            layoutParams = WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
                } else {
                    WindowManager.LayoutParams.TYPE_PHONE
                },
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                        WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or
                        WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON,
                PixelFormat.TRANSLUCENT
            ).apply {
                gravity = Gravity.TOP or Gravity.START
                x = 100
                y = 100
            }

            overlayView = composeView
            windowManager.addView(overlayView, layoutParams)
            
            // Initial data set
            caseStatusState.value = "Checking..."
            nextDateState.value = ""
            queryClientInfo(phoneNumber)

        } catch (e: Exception) {
            Log.e(TAG, "Error showing overlay", e)
        }
    }

    private fun queryClientInfo(phoneNumber: String) {
        serviceScope.launch(Dispatchers.IO) {
            try {
                val db = AppDatabase.getDatabase(applicationContext)
                val client = db.appDao().getClientByPhone(phoneNumber)
                
                withContext(Dispatchers.Main) {
                    if (client != null) {
                        clientNameState.value = client.name
                        
                        launch(Dispatchers.IO) {
                            val cases = db.appDao().getCasesForClient(client.id)
                            
                            withContext(Dispatchers.Main) {
                                if (cases.isNotEmpty()) {
                                    // Take the first case for now (or improve logic to find most relevant)
                                    val firstCase = cases[0]
                                    caseStatusState.value = firstCase.status ?: "N/A"
                                    nextDateState.value = firstCase.nextDate ?: "N/A"
                                    if (cases.size > 1) {
                                        caseStatusState.value = "${firstCase.status} (+${cases.size - 1} more)"
                                    }
                                } else {
                                    caseStatusState.value = "No Active Case"
                                    nextDateState.value = "-"
                                }
                            }
                        }
                    } else {
                        clientNameState.value = "Unknown Caller"
                        caseStatusState.value = "No Record"
                        nextDateState.value = "-"
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Database query error", e)
                withContext(Dispatchers.Main) {
                    clientNameState.value = "Error"
                    caseStatusState.value = "Err"
                    nextDateState.value = "Err"
                }
            }
        }
    }

    override fun onDestroy() {
        lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_DESTROY)
        store.clear()
        
        if (overlayView != null) {
            try {
                windowManager.removeView(overlayView)
            } catch (e: Exception) {
                Log.e(TAG, "Error removing overlay", e)
            }
            overlayView = null
        }
        super.onDestroy()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Call Overlay Service",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Shows caller information overlay"
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun createNotification(): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Nyaya Sahayi")
            .setContentText("Call monitoring active")
            .setSmallIcon(R.mipmap.ic_launcher)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }
}
