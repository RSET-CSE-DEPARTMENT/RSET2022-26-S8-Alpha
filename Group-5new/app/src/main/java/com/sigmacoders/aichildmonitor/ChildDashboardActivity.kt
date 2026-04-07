package com.sigmacoders.aichildmonitor

import android.content.pm.ApplicationInfo
import android.os.Bundle
import android.util.Log
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.graphics.toColorInt
import com.github.mikephil.charting.components.XAxis
import com.github.mikephil.charting.data.BarData
import com.github.mikephil.charting.data.BarDataSet
import com.github.mikephil.charting.data.BarEntry
import com.github.mikephil.charting.data.Entry
import com.github.mikephil.charting.data.LineData
import com.github.mikephil.charting.data.LineDataSet
import com.github.mikephil.charting.formatter.IndexAxisValueFormatter
import com.google.firebase.firestore.ktx.firestore
import com.google.firebase.ktx.Firebase
import com.sigmacoders.aichildmonitor.databinding.ActivityChildDashboardBinding
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException
import java.text.SimpleDateFormat
import java.util.*

class ChildDashboardActivity : AppCompatActivity() {

    private lateinit var binding: ActivityChildDashboardBinding
    private val tag = "ChildDashboardActivity"
    private var childId: String? = null
    private var parentId: String? = null
    private val client = OkHttpClient()

    private val BASE_URL: String
        get() {
            val isEmulator = (android.os.Build.FINGERPRINT.startsWith("generic")
                    || android.os.Build.FINGERPRINT.startsWith("unknown")
                    || android.os.Build.MODEL.contains("google_sdk")
                    || android.os.Build.MODEL.contains("Emulator")
                    || android.os.Build.MODEL.contains("Android SDK built for x86")
                    || android.os.Build.MANUFACTURER.contains("Genymotion")
                    || (android.os.Build.BRAND.startsWith("generic") && android.os.Build.DEVICE.startsWith("generic"))
                    || "google_sdk" == android.os.Build.PRODUCT
                    || android.os.Build.HARDWARE.contains("ranchu"))

            return if (isEmulator) "http://10.0.2.2:5000" else "http://10.177.103.166:5000"
        }
    private var childGender: String = "Boy"
    private var childAge: Int = 12
    private var childName: String = "Child"
    private val dateFormat = SimpleDateFormat("yyyy-MM-dd", Locale.US)

    private var currentDaysOffset = 0
    private var cachedUsageByDate: Map<String, Any>? = null
    private var currentJournalText = ""
    private var currentRiskLevel = "Low"
    private val attemptedDates = mutableSetOf<String>()

    private var currentJournalDialog: AlertDialog? = null

    // Cached values for Journal API
    private var lastTotalHours = 0.0
    private var lastSocialHours = 0.0
    private var lastGamingHours = 0.0
    private var lastPhoneChecks = 0
    private var lastNightUsageMinutes = 0.0
    private var lastNightUsageRatio = 0.0
    private var lastEntertainmentRatio = 0.0
    private var lastGamingRatio = 0.0
    private var lastSocialRatio = 0.0
    private var lastDateKey = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityChildDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)

        childId = intent.getStringExtra("CHILD_ID")
        parentId = intent.getStringExtra("PARENT_ID")

        if (parentId == null || childId == null) {
            Log.e(tag, "Parent ID or Child ID is null.")
            finish()
            return
        }

        setupNavigation()
        setupFirestoreListener(parentId!!, childId!!)

        binding.setLimitButton.setOnClickListener {
            showSetLimitDialog()
        }
    }

    private fun showSetLimitDialog() {
        val input = EditText(this)
        input.hint = "Enter limit in minutes (e.g. 120)"
        input.inputType = android.text.InputType.TYPE_CLASS_NUMBER

        AlertDialog.Builder(this)
            .setTitle("Set Daily Screen Time Limit")
            .setMessage("The parent will be notified if the child exceeds this many minutes today.")
            .setView(input)
            .setPositiveButton("Save") { _, _ ->
                val limitStr = input.text.toString()
                if (limitStr.isNotEmpty()) {
                    val limitMinutes = limitStr.toLong()
                    saveLimitToFirestore(limitMinutes)
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun saveLimitToFirestore(minutes: Long) {
        if (parentId != null && childId != null) {
            Firebase.firestore.collection("users").document(parentId!!).collection("children").document(childId!!)
                .update("screenTimeLimit", minutes)
                .addOnSuccessListener {
                    Toast.makeText(this, "Limit set to $minutes minutes.", Toast.LENGTH_SHORT).show()
                }
        }
    }

    private fun setupNavigation() {
        updateDateDisplay()

        binding.btnPrevDay.setOnClickListener {
            if (currentDaysOffset < 6) {
                currentDaysOffset++
                updateDateDisplay()
                refreshData()
            } else {
                Toast.makeText(this, "Only past 7 days available", Toast.LENGTH_SHORT).show()
            }
        }

        binding.btnNextDay.setOnClickListener {
            if (currentDaysOffset > 0) {
                currentDaysOffset--
                updateDateDisplay()
                refreshData()
            }
        }
    }

    private fun updateDateDisplay() {
        val calendar = Calendar.getInstance()
        calendar.add(Calendar.DAY_OF_YEAR, -currentDaysOffset)
        val dateKey = dateFormat.format(calendar.time)

        binding.usageDateLabel.text = when (currentDaysOffset) {
            0 -> "Today"
            1 -> "Yesterday"
            else -> dateKey
        }

        binding.btnNextDay.isEnabled = currentDaysOffset > 0
        binding.btnNextDay.alpha = if (currentDaysOffset > 0) 1.0f else 0.3f
    }

    private fun refreshData() {
        val calendar = Calendar.getInstance()
        calendar.add(Calendar.DAY_OF_YEAR, -currentDaysOffset)
        val dateKey = dateFormat.format(calendar.time)

        cachedUsageByDate?.let {
            renderUsageForDate(it, dateKey)
        }
    }

    private fun setupFirestoreListener(parentId: String, childId: String) {
        val db = Firebase.firestore
        val childRef = db.collection("users").document(parentId).collection("children").document(childId)

        childRef.addSnapshotListener { snapshot, error ->
            if (error != null) {
                Log.e(tag, "Listen failed.", error)
                return@addSnapshotListener
            }

            if (snapshot != null && snapshot.exists()) {
                childName = snapshot.getString("name") ?: "Child"
                val riskLevelString = snapshot.getString("riskLevel") ?: "Low"
                childGender = snapshot.getString("gender") ?: "Boy"
                childAge = snapshot.getLong("age")?.toInt() ?: 12
                currentJournalText = snapshot.getString("journalText") ?: getString(R.string.no_journal_entry)

                val limit = snapshot.getLong("screenTimeLimit")
                if (limit != null) {
                    binding.limitTextView.text = getString(R.string.limit_min, limit)
                } else {
                    binding.limitTextView.text = getString(R.string.limit_not_set)
                }

                binding.childNameTextView.text = childName
                binding.riskLevelValue.text = getString(R.string.risk_level, riskLevelString)
                updateAvatar(riskLevelString, childGender)

                @Suppress("UNCHECKED_CAST")
                val usageByDate = snapshot.get("usageByDate") as? Map<String, Any>

                if (usageByDate != null) {
                    cachedUsageByDate = usageByDate
                    renderWeeklyTrend(usageByDate)

                    val weeklyRisk = computeWeeklyRisk(usageByDate)
                    binding.weeklyRiskText.text = "Weekly Risk: $weeklyRisk"

                    Firebase.firestore.collection("users")
                        .document(parentId)
                        .collection("children")
                        .document(childId)
                        .update("weeklyRiskLevel", weeklyRisk)

                    refreshData()
                }
            }
        }

        binding.journalButton.setOnClickListener {
            val title = if (currentDaysOffset == 0) "Today's Wellness Journal" else "${binding.usageDateLabel.text}'s Wellness Journal"

            val hasRealJournal = currentJournalText.isNotEmpty() &&
                    !currentJournalText.startsWith("Generating") &&
                    !currentJournalText.startsWith("No ") &&
                    !currentJournalText.startsWith("Analyzing")

            if (!hasRealJournal && lastDateKey.isNotEmpty()) {
                currentJournalText = "Generating your wellness journal, please wait..."
                Toast.makeText(this@ChildDashboardActivity, "Requesting AI Journal...", Toast.LENGTH_SHORT).show()
                val riskInt = when (currentRiskLevel) {
                    "High" -> 2
                    "Medium" -> 1
                    else -> 0
                }
                sendJournalRequest(
                    dateKey = lastDateKey,
                    riskLevel = riskInt,
                    totalHours = lastTotalHours,
                    socialHours = lastSocialHours,
                    gamingHours = lastGamingHours,
                    phoneChecks = lastPhoneChecks,
                    nightUsage = lastNightUsageMinutes,
                    nightRatio = lastNightUsageRatio,
                    entertainmentRatio = lastEntertainmentRatio,
                    gamingRatio = lastGamingRatio,
                    socialRatio = lastSocialRatio
                )
            }

            val dialog = AlertDialog.Builder(this)
                .setTitle(title)
                .setMessage(currentJournalText)
                .setPositiveButton(getString(R.string.close), null)
                .create()

            dialog.show()
            currentJournalDialog = dialog
        }
    }

    private fun computeWeeklyRisk(usageByDate: Map<String, Any>): String {
        var totalMinutes = 0.0
        var totalNightMinutes = 0.0
        var totalPhoneChecks = 0
        var daysCount = 0

        val calendar = Calendar.getInstance()
        calendar.firstDayOfWeek = Calendar.SUNDAY
        calendar.set(Calendar.DAY_OF_WEEK, Calendar.SUNDAY)

        val weekStart = calendar.clone() as Calendar
        val today = Calendar.getInstance()

        while (!weekStart.after(today)) {
            val key = dateFormat.format(weekStart.time)
            val dayData = usageByDate[key] as? Map<String, Any>

            if (dayData != null) {
                val minutes = (dayData["totalMinutes"] as? Number)?.toDouble() ?: 0.0
                val night = (dayData["nightUsageMinutes"] as? Number)?.toDouble() ?: 0.0
                val checks = (dayData["phoneChecks"] as? Number)?.toInt() ?: 0

                totalMinutes += minutes
                totalNightMinutes += night
                totalPhoneChecks += checks
                daysCount++
            }

            weekStart.add(Calendar.DAY_OF_YEAR, 1)
        }

        if (daysCount == 0) return "Low"

        val avgDailyHours = (totalMinutes / daysCount) / 60.0
        val nightRatio = if (totalMinutes > 0) totalNightMinutes / totalMinutes else 0.0
        val avgChecks = totalPhoneChecks / daysCount.toDouble()

        val riskScore = 0.5 * (avgDailyHours / 6.0) + 0.3 * nightRatio + 0.2 * (avgChecks / 80.0)

        return when {
            riskScore < 0.33 -> "Low"
            riskScore < 0.66 -> "Medium"
            else -> "High"
        }
    }

    private fun renderWeeklyTrend(usageByDate: Map<String, Any>) {
        val entries = ArrayList<Entry>()
        val labels = ArrayList<String>()

        val calendar = Calendar.getInstance()
        calendar.firstDayOfWeek = Calendar.SUNDAY
        calendar.set(Calendar.DAY_OF_WEEK, Calendar.SUNDAY)

        val today = Calendar.getInstance()
        var index = 0

        while (!calendar.after(today)) {
            val key = dateFormat.format(calendar.time)
            val dayData = usageByDate[key] as? Map<String, Any>
            val minutes = (dayData?.get("totalMinutes") as? Number)?.toFloat() ?: 0f

            entries.add(Entry(index.toFloat(), minutes))
            labels.add(SimpleDateFormat("EEE", Locale.US).format(calendar.time))

            calendar.add(Calendar.DAY_OF_YEAR, 1)
            index++
        }

        val dataSet = LineDataSet(entries, "Weekly Screen Time")
        dataSet.lineWidth = 3f
        dataSet.circleRadius = 4f
        dataSet.color = "#673AB7".toColorInt()
        dataSet.setCircleColor("#673AB7".toColorInt())

        binding.weeklyTrendChart.apply {
            this.data = LineData(dataSet)
            xAxis.valueFormatter = IndexAxisValueFormatter(labels)
            xAxis.position = XAxis.XAxisPosition.BOTTOM
            xAxis.granularity = 1f
            axisLeft.axisMinimum = 0f
            axisRight.isEnabled = false
            description.isEnabled = false
            invalidate()
        }
    }

    @Suppress("UNCHECKED_CAST")
    private fun renderUsageForDate(usageByDate: Map<String, Any>, dateKey: String) {
        val dayData = usageByDate[dateKey] as? Map<String, Any>

        if (dayData == null) {
            binding.totalTimeTextView.text = getString(R.string.no_data_day)
            binding.appUsageBarChart.clear()
            binding.appUsageBarChart.invalidate()
            currentJournalText = "No data available for this date."
            binding.riskLevelValue.text = getString(R.string.risk_level, "N/A")
            return
        }

        val totalMinutes = (dayData["totalMinutes"] as? Number)?.toLong() ?: 0L
        val phoneChecks = (dayData["phoneChecks"] as? Number)?.toInt() ?: 0
        val nightUsageMinutes = (dayData["nightUsageMinutes"] as? Number)?.toDouble() ?: 0.0
        val nightUsageRatio = (dayData["nightUsageRatio"] as? Number)?.toDouble() ?: 0.0
        val topApps = (dayData["topApps"] as? List<Map<String, Any>>) ?: emptyList()

        // Load persisted risk & journal from Firestore (written back by Flask)
        currentRiskLevel = dayData["riskLevel"] as? String ?: "Calculating..."
        currentJournalText = dayData["journalText"] as? String ?: ""

        binding.riskLevelValue.text = getString(R.string.risk_level, currentRiskLevel)
        updateAvatar(currentRiskLevel, childGender)

        val hours = totalMinutes / 60
        val minutes = totalMinutes % 60
        binding.totalTimeTextView.text = getString(R.string.total_hm, hours, minutes)

        var socialMinutes = 0L
        var gamingMinutes = 0L

        val entries = ArrayList<BarEntry>()
        val labels = ArrayList<String>()

        topApps.forEachIndexed { index, app ->
            val appName = app["appName"] as? String ?: "Unknown"
            val usageMinutesLong = (app["usageMinutes"] as? Number)?.toLong() ?: 0L
            val category = (app["category"] as? Number)?.toInt() ?: -1

            entries.add(BarEntry(index.toFloat(), usageMinutesLong.toFloat()))
            labels.add(appName)

            val name = appName.lowercase()
            val isSocialManual = name.contains("instagram") || name.contains("facebook") ||
                    name.contains("whatsapp") || name.contains("youtube") ||
                    name.contains("snapchat") || name.contains("tiktok")
            val isGamingManual = name.contains("pubg") || name.contains("free fire") ||
                    name.contains("cod") || name.contains("minecraft") ||
                    name.contains("roblox") || name.contains("hungryshark") || name.contains("juggle")

            if (isSocialManual || category == ApplicationInfo.CATEGORY_SOCIAL || category == ApplicationInfo.CATEGORY_VIDEO) {
                socialMinutes += usageMinutesLong
            } else if (isGamingManual || category == ApplicationInfo.CATEGORY_GAME) {
                gamingMinutes += usageMinutesLong
            }
        }

        if (entries.isNotEmpty()) {
            setupBarChart(entries, labels)
        }

        val totalHours = totalMinutes / 60.0
        val socialHours = socialMinutes / 60.0
        val gamingHours = gamingMinutes / 60.0
        val entertainmentRatio = if (totalHours > 0) (socialHours + gamingHours) / totalHours else 0.0
        val gamingRatio = if (totalHours > 0) gamingHours / totalHours else 0.0
        val socialRatio = if (totalHours > 0) socialHours / totalHours else 0.0

        // Save metrics for journal generation if requested by user
        lastTotalHours = totalHours
        lastSocialHours = socialHours
        lastGamingHours = gamingHours
        lastPhoneChecks = phoneChecks
        lastNightUsageMinutes = nightUsageMinutes / 60.0
        lastNightUsageRatio = nightUsageRatio
        lastEntertainmentRatio = entertainmentRatio
        lastGamingRatio = gamingRatio
        lastSocialRatio = socialRatio
        lastDateKey = dateKey

        // Automatically predict risk on load, but wait for user click to generate Journal
        sendPredictOnly(
            dateKey = dateKey,
            totalHours = totalHours,
            socialHours = socialHours,
            gamingHours = gamingHours,
            phoneChecks = phoneChecks,
            nightUsage = nightUsageMinutes / 60.0,
            nightRatio = nightUsageRatio,
            entertainmentRatio = entertainmentRatio,
            gamingRatio = gamingRatio,
            socialRatio = socialRatio
        )
    }


    // POST to /journal → get AI journal text
    private fun sendJournalRequest(
        dateKey: String,
        riskLevel: Int,
        totalHours: Double,
        socialHours: Double,
        gamingHours: Double,
        phoneChecks: Int,
        nightUsage: Double,
        nightRatio: Double,
        entertainmentRatio: Double,
        gamingRatio: Double,
        socialRatio: Double
    ) {
        val journalJson = buildUsageJson(
            totalHours, socialHours, gamingHours, phoneChecks,
            nightUsage, nightRatio, entertainmentRatio, gamingRatio, socialRatio
        ).apply {
            put("risk_level", riskLevel) // /journal needs risk_level
        }

        val journalRequest = Request.Builder()
            .url("$BASE_URL/journal")
            .post(journalJson.toString().toRequestBody("application/json".toMediaTypeOrNull()))
            .build()

        client.newCall(journalRequest).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                Log.e("API_ERROR", "Failed to connect to /journal: ${e.message}")
                runOnUiThread {
                    currentJournalText = getString(R.string.no_journal_entry)
                    currentJournalDialog?.setMessage(currentJournalText)
                }
            }

            override fun onResponse(call: Call, response: Response) {
                val body = response.body?.string()
                Log.d("API_RESPONSE", "/journal response: $body")

                if (response.isSuccessful && body != null) {
                    val aiJournal = JSONObject(body).optString("journal", getString(R.string.no_journal_entry))
                    val riskString = when (riskLevel) {
                        1 -> "Medium"
                        2 -> "High"
                        else -> "Low"
                    }

                    saveToFirestore(dateKey, riskString, aiJournal)
                    runOnUiThread {
                        updateCurrentViewIfMatch(dateKey, aiJournal, riskString)
                        currentJournalDialog?.setMessage(aiJournal)
                    }
                } else {
                    runOnUiThread {
                        currentJournalText = "Failed to generate journal. Server returned error."
                        currentJournalDialog?.setMessage(currentJournalText)
                    }
                }
            }
        })
    }

    // Only refresh risk level (no journal needed — already stored)
    private fun sendPredictOnly(
        dateKey: String,
        totalHours: Double,
        socialHours: Double,
        gamingHours: Double,
        phoneChecks: Int,
        nightUsage: Double,
        nightRatio: Double,
        entertainmentRatio: Double,
        gamingRatio: Double,
        socialRatio: Double
    ) {
        val json = buildUsageJson(
            totalHours, socialHours, gamingHours, phoneChecks,
            nightUsage, nightRatio, entertainmentRatio, gamingRatio, socialRatio
        )

        val request = Request.Builder()
            .url("$BASE_URL/predict")
            .post(json.toString().toRequestBody("application/json".toMediaTypeOrNull()))
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                Log.e("API_ERROR", "Failed to connect to /predict: ${e.message}")
            }

            override fun onResponse(call: Call, response: Response) {
                val body = response.body?.string()
                Log.d("API_RESPONSE", "/predict (only) response: $body")

                if (response.isSuccessful && body != null) {
                    val riskInt = JSONObject(body).optInt("risk_level", 0)
                    val riskString = when (riskInt) {
                        1 -> "Medium"
                        2 -> "High"
                        else -> "Low"
                    }

                    saveToFirestore(dateKey, riskString, null)
                    runOnUiThread {
                        updateCurrentViewIfMatch(dateKey, currentJournalText, riskString)
                    }
                }
            }
        })
    }

    // Shared helper to build the usage JSON body
    private fun buildUsageJson(
        totalHours: Double,
        socialHours: Double,
        gamingHours: Double,
        phoneChecks: Int,
        nightUsage: Double,
        nightRatio: Double,
        entertainmentRatio: Double,
        gamingRatio: Double,
        socialRatio: Double
    ): JSONObject {
        return JSONObject().apply {
            put("avg_screen_time", totalHours)
            put("social_media_hours", socialHours)
            put("gaming_hours", gamingHours)
            put("night_usage", nightUsage)
            put("phone_checks_per_day", phoneChecks)
            put("Age", childAge)
            put("entertainment_ratio", entertainmentRatio)
            put("night_usage_ratio", nightRatio)
            put("engagement_intensity", totalHours * 50)
            put("gaming_ratio", gamingRatio)
            put("social_ratio", socialRatio)
        }
    }

    // Save risk and/or journal back to Firestore
    private fun saveToFirestore(dateKey: String, riskLevel: String, journal: String?) {
        if (parentId == null || childId == null) return
        val ref = Firebase.firestore.collection("users").document(parentId!!)
            .collection("children").document(childId!!)

        val updates = mutableMapOf<String, Any>(
            "usageByDate.$dateKey.riskLevel" to riskLevel,
            "riskLevel" to riskLevel
        )
        if (journal != null) {
            updates["usageByDate.$dateKey.journalText"] = journal
        }

        ref.update(updates)
    }

    private fun updateCurrentViewIfMatch(dateKey: String, journal: String, risk: String) {
        val displayedDate = dateFormat.format(
            Calendar.getInstance().apply { add(Calendar.DAY_OF_YEAR, -currentDaysOffset) }.time
        )
        if (displayedDate == dateKey) {
            currentJournalText = journal
            currentRiskLevel = risk
            binding.riskLevelValue.text = getString(R.string.risk_level, risk)
            updateAvatar(risk, childGender)
        }
    }

    private fun updateAvatar(riskLevel: String, gender: String) {
        val level = riskLevel.lowercase()
        if (gender == "Girl") {
            when {
                level.contains("low") -> binding.emotionalAvatar.setImageResource(R.drawable.girl_smile)
                level.contains("high") -> binding.emotionalAvatar.setImageResource(R.drawable.girl_sad)
                else -> binding.emotionalAvatar.setImageResource(R.drawable.girl_mid)
            }
        } else {
            when {
                level.contains("low") -> binding.emotionalAvatar.setImageResource(R.drawable.boy_smile)
                level.contains("high") -> binding.emotionalAvatar.setImageResource(R.drawable.boy_sad)
                else -> binding.emotionalAvatar.setImageResource(R.drawable.boy_mid)
            }
        }
    }

    private fun setupBarChart(entries: ArrayList<BarEntry>, labels: ArrayList<String>) {
        val dataSet = BarDataSet(entries, "App Usage (min)")
        dataSet.color = "#673AB7".toColorInt()
        val barData = BarData(dataSet)
        barData.barWidth = 0.5f
        binding.appUsageBarChart.apply {
            data = barData
            setFitBars(true)
            description.isEnabled = false
            legend.isEnabled = false
            xAxis.valueFormatter = IndexAxisValueFormatter(labels)
            xAxis.position = XAxis.XAxisPosition.BOTTOM
            xAxis.granularity = 1f
            xAxis.labelRotationAngle = -45f
            axisLeft.axisMinimum = 0f
            axisRight.isEnabled = false
            invalidate()
        }
    }
}