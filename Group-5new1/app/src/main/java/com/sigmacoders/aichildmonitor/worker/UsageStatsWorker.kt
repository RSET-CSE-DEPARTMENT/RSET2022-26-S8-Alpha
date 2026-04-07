package com.sigmacoders.aichildmonitor.worker

import android.app.AppOpsManager
import android.app.usage.UsageEvents
import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Process
import android.util.Log
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.google.firebase.Timestamp
import com.google.firebase.firestore.FieldValue
import com.google.firebase.firestore.SetOptions
import com.google.firebase.firestore.ktx.firestore
import com.google.firebase.ktx.Firebase
import kotlinx.coroutines.tasks.await
import java.text.SimpleDateFormat
import java.util.*

class UsageStatsWorker(appContext: Context, workerParams: WorkerParameters) :
    CoroutineWorker(appContext, workerParams) {

    private val tag = "UsageStatsWorker"
    private val dateFormat = SimpleDateFormat("yyyy-MM-dd", Locale.US)

    // Packages to exclude from usage tracking
    private val excludedPackages by lazy {
        setOf(
            applicationContext.packageName,              // AI Child Monitor itself
            "com.android.launcher",                      // Generic launcher
            "com.android.launcher2",
            "com.android.launcher3",
            "com.miui.home",                             // Xiaomi
            "com.sec.android.app.launcher",              // Samsung
            "com.google.android.apps.nexuslauncher",     // Pixel
            "com.huawei.android.launcher",               // Huawei
            "com.oppo.launcher",                         // Oppo
            "com.vivo.launcher",                         // Vivo
            "com.realme.launcher",                       // Realme
            "com.oneplus.launcher",                      // OnePlus
            "com.android.systemui",                      // System UI
            "com.android.settings",                      // Settings
            "com.android.keyguard",                      // Lock screen
            "com.android.inputmethod.latin",             // Keyboard
            "com.google.android.inputmethod.latin"       // Gboard
        )
    }

    override suspend fun doWork(): Result {
        val parentId = inputData.getString("PARENT_ID")
        val childId = inputData.getString("CHILD_ID")

        if (parentId.isNullOrEmpty() || childId.isNullOrEmpty()) return Result.failure()
        if (!hasUsageStatsPermission()) return Result.failure()

        return try {
            uploadUsageStats(parentId, childId)
            Result.success()
        } catch (e: Exception) {
            Log.e(tag, "Error during usage stats upload", e)
            Result.failure()
        }
    }

    private suspend fun uploadUsageStats(parentId: String, childId: String) {
        val db = Firebase.firestore
        val childRef = db.collection("users").document(parentId).collection("children").document(childId)

        val usageByDate = hashMapOf<String, Any>()
        val activeDateKeys = mutableListOf<String>()

        for (i in 0..6) {
            val calendar = Calendar.getInstance().apply { add(Calendar.DAY_OF_YEAR, -i) }
            val dateKey = dateFormat.format(calendar.time)
            usageByDate[dateKey] = fetchDayUsage(calendar)
            activeDateKeys.add(dateKey)
        }

        usageByDate["lastUpdated"] = Timestamp.now()
        childRef.set(hashMapOf("usageByDate" to usageByDate), SetOptions.merge()).await()
        flushOldData(childRef, activeDateKeys)
    }

    private fun fetchDayUsage(dayCal: Calendar): Map<String, Any> {
        val startCal = dayCal.clone() as Calendar
        startCal.set(Calendar.HOUR_OF_DAY, 0)
        startCal.set(Calendar.MINUTE, 0)
        startCal.set(Calendar.SECOND, 0)
        startCal.set(Calendar.MILLISECOND, 0)
        val startTime = startCal.timeInMillis

        val endCal = dayCal.clone() as Calendar
        endCal.set(Calendar.HOUR_OF_DAY, 23)
        endCal.set(Calendar.MINUTE, 59)
        endCal.set(Calendar.SECOND, 59)
        endCal.set(Calendar.MILLISECOND, 999)
        val endTime = minOf(endCal.timeInMillis, System.currentTimeMillis())

        val appMap = calculateUsageFromEvents(startTime, endTime)

        val topApps = appMap.entries
            .filter { it.value > 0 }
            .sortedByDescending { it.value }
            .take(15)
            .map { entry ->
                mapOf(
                    "appName" to getAppName(entry.key),
                    "usageMinutes" to entry.value,
                    "category" to getCategory(entry.key)
                )
            }

        val totalMinutes = appMap.values.sum()

        // Night Usage: 12 AM to 6 AM
        val nightEnd = startCal.clone() as Calendar
        nightEnd.set(Calendar.HOUR_OF_DAY, 6)
        val nightMap = calculateUsageFromEvents(startTime, minOf(nightEnd.timeInMillis, endTime))
        val nightMinutes = nightMap.values.sum()

        val nightRatio = if (totalMinutes > 0) nightMinutes.toDouble() / totalMinutes else 0.0
        val phoneChecks = calculatePhoneChecks(startTime, endTime)

        Log.d(tag, "Precise Stats for ${dateFormat.format(dayCal.time)}: Total=$totalMinutes, Night=$nightMinutes")

        return mapOf(
            "totalMinutes" to totalMinutes,
            "phoneChecks" to phoneChecks,
            "nightUsageMinutes" to nightMinutes,
            "nightUsageRatio" to nightRatio,
            "topApps" to topApps
        )
    }

    private fun calculateUsageFromEvents(start: Long, end: Long): Map<String, Long> {
        val usageStatsManager = applicationContext.getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
        val events = usageStatsManager.queryEvents(start, end)
        val event = UsageEvents.Event()

        val appMsMap = mutableMapOf<String, Long>()
        val startTimes = mutableMapOf<String, Long>()

        while (events.hasNextEvent()) {
            events.getNextEvent(event)
            val pkg = event.packageName

            // Skip excluded packages (own app, launchers, system apps)
            if (pkg in excludedPackages) continue

            if (event.eventType == UsageEvents.Event.ACTIVITY_RESUMED) {
                startTimes[pkg] = event.timeStamp
            } else if (event.eventType == UsageEvents.Event.ACTIVITY_PAUSED ||
                event.eventType == UsageEvents.Event.ACTIVITY_STOPPED
            ) {
                val startTime = startTimes.remove(pkg)
                if (startTime != null) {
                    val duration = event.timeStamp - startTime
                    appMsMap[pkg] = (appMsMap[pkg] ?: 0L) + duration
                }
            }
        }

        // Handle apps still open at the end of the query window
        startTimes.forEach { (pkg, startTime) ->
            val duration = end - startTime
            if (duration > 0) {
                appMsMap[pkg] = (appMsMap[pkg] ?: 0L) + duration
            }
        }

        return appMsMap.mapValues { it.value / (1000 * 60) }
    }

    private fun calculatePhoneChecks(start: Long, end: Long): Int {
        val usageStatsManager = applicationContext.getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
        val events = usageStatsManager.queryEvents(start, end)
        val event = UsageEvents.Event()
        var count = 0
        while (events.hasNextEvent()) {
            events.getNextEvent(event)
            if (event.eventType == UsageEvents.Event.KEYGUARD_HIDDEN) count++
        }
        return count
    }

    private suspend fun flushOldData(
        childRef: com.google.firebase.firestore.DocumentReference,
        activeKeys: List<String>
    ) {
        try {
            val snapshot = childRef.get().await()
            @Suppress("UNCHECKED_CAST")
            val usageByDate = snapshot.get("usageByDate") as? Map<String, Any> ?: return
            val keysToDelete = usageByDate.keys.filter { key ->
                key != "lastUpdated" && !activeKeys.contains(key)
            }
            if (keysToDelete.isNotEmpty()) {
                val updates = keysToDelete.associate { "usageByDate.$it" to FieldValue.delete() }
                childRef.update(updates).await()
            }
        } catch (e: Exception) {
            Log.e(tag, "Error flushing old data", e)
        }
    }

    private fun getAppName(packageName: String): String {
        return try {
            val appInfo = applicationContext.packageManager.getApplicationInfo(packageName, 0)
            applicationContext.packageManager.getApplicationLabel(appInfo).toString()
        } catch (_: Exception) {
            packageName.substringAfterLast('.').replaceFirstChar { it.uppercase() }
        }
    }

    private fun getCategory(packageName: String): Int {
        return try {
            applicationContext.packageManager.getApplicationInfo(packageName, 0).category
        } catch (_: Exception) {
            -1
        }
    }

    private fun hasUsageStatsPermission(): Boolean {
        val appOps = applicationContext.getSystemService(Context.APP_OPS_SERVICE) as AppOpsManager
        val mode = appOps.checkOpNoThrow(
            AppOpsManager.OPSTR_GET_USAGE_STATS,
            Process.myUid(),
            applicationContext.packageName
        )
        return mode == AppOpsManager.MODE_ALLOWED
    }
}