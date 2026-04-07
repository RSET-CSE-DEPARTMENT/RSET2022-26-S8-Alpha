package com.sigmacoders.aichildmonitor.ai

import android.util.Log
import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.SetOptions
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

class VideoClassifier {

    // Increased timeout to avoid model cold-start timeout
    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    private val db = FirebaseFirestore.getInstance()

    fun classify(
        title: String,
        channel: String,
        parentId: String,
        childId: String,
        apiKey: String,
        onComplete: (String, Double, String) -> Unit,
        onError: (Exception) -> Unit
    ) {

        val text = "Video title: $title. Channel: $channel"

        val candidateLabels = listOf(
            "educational content suitable for children",
            "harmless entertainment content",
            "violent or aggressive content involving physical harm",
            "sexually explicit or pornographic material",
            "content promoting harmful or addictive behavior"
        )

        val json = JSONObject().apply {
            put("inputs", text)
            put("parameters", JSONObject().apply {
                put("candidate_labels", candidateLabels)
                put("multi_label", true)
                put("hypothesis_template", "This video contains {}.")
            })
            put("options", JSONObject().apply {
                put("wait_for_model", true)
            })
        }

        val requestBody = json.toString()
            .toRequestBody("application/json".toMediaTypeOrNull())

        // Using BASE version for faster inference
        val request = Request.Builder()
            .url("https://router.huggingface.co/hf-inference/models/MoritzLaurer/deberta-v3-base-zeroshot-v2.0")
            .addHeader("Authorization", "Bearer $apiKey")
            .addHeader("Content-Type", "application/json")
            .post(requestBody)
            .build()

        client.newCall(request).enqueue(object : Callback {

            override fun onFailure(call: Call, e: IOException) {
                onError(e)
            }

            override fun onResponse(call: Call, response: Response) {

                val body = response.body?.string() ?: ""

                try {
                    Log.d("HF_RAW", body)

                    var topCategory = ""
                    var topConfidence = 0.0

                    var adultScore = 0.0
                    var harmfulScore = 0.0
                    var violentScore = 0.0

                    // Handle BOTH possible HF response formats
                    if (body.trim().startsWith("[")) {

                        val jsonArray = JSONArray(body)

                        for (i in 0 until jsonArray.length()) {
                            val item = jsonArray.getJSONObject(i)
                            val label = item.getString("label").lowercase().trim()
                            val score = item.getDouble("score")

                            if (i == 0) {
                                topCategory = label
                                topConfidence = score
                            }

                            if (label.contains("sexual")) adultScore = score
                            if (label.contains("harmful")) harmfulScore = score
                            if (label.contains("violent")) violentScore = score
                        }

                    } else {

                        val jsonObject = JSONObject(body)
                        val labels = jsonObject.getJSONArray("labels")
                        val scores = jsonObject.getJSONArray("scores")

                        for (i in 0 until labels.length()) {
                            val label = labels.getString(i).lowercase().trim()
                            val score = scores.getDouble(i)

                            if (i == 0) {
                                topCategory = label
                                topConfidence = score
                            }

                            if (label.contains("sexual")) adultScore = score
                            if (label.contains("harmful")) harmfulScore = score
                            if (label.contains("violent")) violentScore = score
                        }
                    }

                    val safety = if (
                        adultScore > 0.6 ||
                        harmfulScore > 0.6 ||
                        violentScore > 0.6
                    ) {
                        "unsafe"
                    } else {
                        "safe"
                    }

                    Log.i(
                        "CLASSIFICATION_RESULT",
                        "Title: $title | Top: $topCategory | Safety: $safety"
                    )

                    // Save unsafe video info
                    if (safety == "unsafe" && parentId.isNotEmpty() && childId.isNotEmpty()) {

                        val lastUnsafeData = hashMapOf(
                            "title" to title,
                            "timestamp" to System.currentTimeMillis()
                        )

                        val update = hashMapOf(
                            "lastUnsafeVideo" to lastUnsafeData
                        )

                        db.collection("users").document(parentId)
                            .collection("children").document(childId)
                            .set(update, SetOptions.merge())
                            .addOnSuccessListener {
                                Log.d("FIRESTORE_WRITE", "lastUnsafeVideo updated.")
                            }
                            .addOnFailureListener { e ->
                                Log.e("FIRESTORE_WRITE", e.message ?: "Firestore error")
                            }
                    }

                    onComplete(topCategory, topConfidence, safety)

                } catch (e: Exception) {
                    Log.e("VIDEO_CLASSIFIER", "Parsing error: ${e.message}")
                    onError(e)
                }
            }
        })
    }
}