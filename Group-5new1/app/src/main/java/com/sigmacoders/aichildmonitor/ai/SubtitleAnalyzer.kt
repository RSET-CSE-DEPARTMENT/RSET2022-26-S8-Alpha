package com.sigmacoders.aichildmonitor.ai

import android.util.Log
import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.SetOptions
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

/**
 * SubtitleAnalyzer — fetches YouTube video subtitles via the
 * Flask backend and runs sentiment + toxicity analysis on them.
 *
 * This adds a second layer of content safety analysis on top
 * of the existing title-based zero-shot classification.
 */
class SubtitleAnalyzer {

    companion object {
        private const val TAG = "SUBTITLE_ANALYZER"

        private val BACKEND_URL: String
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

                val baseUrl = if (isEmulator) "http://10.0.2.2:5000" else "http://10.177.103.166:5000"
                return "$baseUrl/analyze-subtitles"
            }
    }

    // Longer timeouts because subtitle fetching + ML inference
    // can take 10-30 seconds depending on video length
    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(90, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    private val db = FirebaseFirestore.getInstance()

    /**
     * Analyze a YouTube video's subtitles for harmful content.
     *
     * @param videoId    The 11-character YouTube video ID
     * @param title      Video title (for logging/Firestore)
     * @param parentId   Parent's Firebase user ID
     * @param childId    Child's Firebase document ID
     * @param onComplete Callback with (safety, sentimentPositive, sentimentNegative, toxicityScore)
     * @param onError    Callback if analysis fails
     */
    fun analyze(
        videoId: String,
        title: String,
        parentId: String,
        childId: String,
        onComplete: (safety: String, sentimentPos: Double, sentimentNeg: Double, toxicity: Double) -> Unit,
        onError: (Exception) -> Unit
    ) {
        val json = JSONObject().apply {
            put("video_id", videoId)
            put("title", title)
        }

        val requestBody = json.toString()
            .toRequestBody("application/json".toMediaTypeOrNull())

        val request = Request.Builder()
            .url(BACKEND_URL)
            .post(requestBody)
            .build()

        Log.d(TAG, "Requesting subtitle analysis for: $videoId ($title)")

        client.newCall(request).enqueue(object : Callback {

            override fun onFailure(call: Call, e: IOException) {
                Log.e(TAG, "Backend request failed: ${e.message}")
                onError(e)
            }

            override fun onResponse(call: Call, response: Response) {
                val body = response.body?.string() ?: ""

                try {
                    val result = JSONObject(body)

                    val subtitlesFound = result.optBoolean("subtitles_found", false)

                    if (!subtitlesFound) {
                        Log.w(TAG, "No subtitles available for $videoId")
                        // Return "unknown" safety — title classification alone will decide
                        onComplete("unknown", 0.0, 0.0, 0.0)
                        return
                    }

                    val safety = result.optString("safety", "unknown")
                    val sentimentPos = result.optDouble("sentiment_positive", 0.0)
                    val sentimentNeg = result.optDouble("sentiment_negative", 0.0)
                    val toxicity = result.optDouble("toxicity_score", 0.0)
                    val chunksAnalyzed = result.optInt("chunks_analyzed", 0)

                    Log.i(
                        TAG,
                        "Video: $videoId | Safety: $safety | " +
                                "Sentiment: +$sentimentPos / -$sentimentNeg | " +
                                "Toxicity: $toxicity | Chunks: $chunksAnalyzed"
                    )

                    // Save subtitle analysis results to Firestore
                    if (parentId.isNotEmpty() && childId.isNotEmpty()) {
                        val subtitleData = hashMapOf(
                            "videoId" to videoId,
                            "title" to title,
                            "subtitleSafety" to safety,
                            "sentimentPositive" to sentimentPos,
                            "sentimentNegative" to sentimentNeg,
                            "toxicityScore" to toxicity,
                            "chunksAnalyzed" to chunksAnalyzed,
                            "timestamp" to System.currentTimeMillis()
                        )

                        val update = hashMapOf(
                            "lastSubtitleAnalysis" to subtitleData
                        )

                        db.collection("users").document(parentId)
                            .collection("children").document(childId)
                            .set(update, SetOptions.merge())
                            .addOnSuccessListener {
                                Log.d(TAG, "Firestore: subtitle analysis saved")
                            }
                            .addOnFailureListener { e ->
                                Log.e(TAG, "Firestore write failed: ${e.message}")
                            }
                    }

                    onComplete(safety, sentimentPos, sentimentNeg, toxicity)

                } catch (e: Exception) {
                    Log.e(TAG, "Response parsing error: ${e.message}")
                    onError(e)
                }
            }
        })
    }
}
