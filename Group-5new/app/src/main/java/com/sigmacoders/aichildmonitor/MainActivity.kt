package com.sigmacoders.aichildmonitor

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.LinearLayoutManager
import com.google.firebase.auth.ktx.auth
import com.google.firebase.firestore.ListenerRegistration
import com.google.firebase.firestore.ktx.firestore
import com.google.firebase.firestore.toObject
import com.google.firebase.ktx.Firebase
import com.sigmacoders.aichildmonitor.adapter.ChildrenAdapter
import com.sigmacoders.aichildmonitor.databinding.ActivityMainBinding
import com.sigmacoders.aichildmonitor.model.Child
import com.sigmacoders.aichildmonitor.utils.NotificationHelper
import java.text.SimpleDateFormat
import java.util.*

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val tag = "MainActivity"
    private val childrenList = mutableListOf<Child>()
    private lateinit var childrenAdapter: ChildrenAdapter
    
    private lateinit var notificationHelper: NotificationHelper
    private val activeChildListeners = mutableMapOf<String, ListenerRegistration>()
    private val lastProcessedVideoTs = mutableMapOf<String, Long>()
    private val sessionStartTime = System.currentTimeMillis()
    
    private val limitAlertTriggeredToday = mutableMapOf<String, String>() // ChildId to Date string

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted: Boolean ->
        Log.d(tag, "Notification permission result: $isGranted")
        if (!isGranted) {
            Toast.makeText(this, "Notifications disabled. You won't get safety alerts.", Toast.LENGTH_LONG).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        notificationHelper = NotificationHelper(this)
        checkNotificationPermission()

        val auth = Firebase.auth
        val userId = auth.currentUser?.uid

        if (userId == null) {
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
            return
        }

        setupRecyclerView()
        setupClickListeners(userId)
        fetchChildren(userId)
    }

    private fun checkNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            val status = ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
            if (status != PackageManager.PERMISSION_GRANTED) {
                requestPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        }
    }

    private fun setupRecyclerView() {
        childrenAdapter = ChildrenAdapter(childrenList) { child ->
            val intent = Intent(this, ChildDashboardActivity::class.java)
            intent.putExtra("PARENT_ID", child.parentId)
            intent.putExtra("CHILD_ID", child.id)
            startActivity(intent)
        }
        binding.childrenRecyclerView?.adapter = childrenAdapter
        binding.childrenRecyclerView?.layoutManager = LinearLayoutManager(this)
    }

    private fun setupClickListeners(userId: String) {
        binding.logoutButton.setOnClickListener {
            Firebase.auth.signOut()
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
        }

        binding.addChildButton.setOnClickListener {
            generateAndSavePairingKey(userId)
        }
    }

    private fun generateAndSavePairingKey(userId: String) {
        val pairingKey = (1000..9999).random().toString()
        val db = Firebase.firestore
        val pairingRef = db.collection("pairingKeys").document(pairingKey)
        pairingRef.set(hashMapOf("parentId" to userId))
            .addOnSuccessListener { showPairingKeyDialog(pairingKey) }
    }

    private fun showPairingKeyDialog(pairingKey: String) {
        AlertDialog.Builder(this)
            .setTitle("Pairing Key")
            .setMessage("Key: $pairingKey")
            .setPositiveButton("OK", null)
            .show()
    }

    private fun fetchChildren(userId: String) {
        val db = Firebase.firestore
        db.collection("users").document(userId).collection("children")
            .whereEqualTo("isPaired", true)
            .addSnapshotListener { snapshots, e ->
                if (e != null) return@addSnapshotListener
                childrenList.clear()
                snapshots?.forEach { doc ->
                    val child = doc.toObject<Child>().copy(id = doc.id, parentId = userId)
                    childrenList.add(child)
                    setupChildMonitor(child)
                }
                childrenAdapter.notifyDataSetChanged()
            }
    }

    @Suppress("UNCHECKED_CAST")
    private fun setupChildMonitor(child: Child) {
        if (activeChildListeners.containsKey(child.id)) return

        val db = Firebase.firestore
        val childRef = db.collection("users").document(child.parentId).collection("children").document(child.id)

        val listener = childRef.addSnapshotListener { snapshot, _ ->
            if (snapshot == null || !snapshot.exists()) return@addSnapshotListener

            // 1. Unsafe Videos
            val lastLog = snapshot.get("lastUnsafeVideo") as? Map<String, Any>
            if (lastLog != null) {
                val ts = lastLog["timestamp"] as? Long ?: 0L
                val title = lastLog["title"] as? String ?: "Unknown Video"
                if (ts > (lastProcessedVideoTs[child.id] ?: sessionStartTime)) {
                    lastProcessedVideoTs[child.id] = ts
                    notificationHelper.showUnsafeContentAlert(child.name, title)
                }
            }

            // 2. Screen Time Limit
            val limit = snapshot.getLong("screenTimeLimit") ?: 0L
            val usageByDate = snapshot.get("usageByDate") as? Map<String, Any>
            val todayKey = SimpleDateFormat("yyyy-MM-dd", Locale.US).format(Date())
            val todayData = usageByDate?.get(todayKey) as? Map<String, Any>
            val totalToday = (todayData?.get("totalMinutes") as? Number)?.toLong() ?: 0L

            if (limit > 0 && totalToday > limit) {
                if (limitAlertTriggeredToday[child.id] != todayKey) {
                    limitAlertTriggeredToday[child.id] = todayKey
                    notificationHelper.showScreenTimeLimitAlert(child.name, totalToday, limit)
                }
            }
        }
        activeChildListeners[child.id] = listener
    }

    override fun onDestroy() {
        super.onDestroy()
        activeChildListeners.values.forEach { it.remove() }
    }
}
