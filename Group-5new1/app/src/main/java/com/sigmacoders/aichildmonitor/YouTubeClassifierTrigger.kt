package com.sigmacoders.aichildmonitor

import android.content.Context
import android.util.Log
import com.sigmacoders.aichildmonitor.ai.VideoClassifier
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.async

object YouTubeClassifierTrigger {

    private var lastClassifiedTitle: String? = null

    fun classifyIfNeeded(
        context: Context,
        title: String,
        videoId: String?,
        parentId: String,
        childId: String
    ) {
        if (title == lastClassifiedTitle) return
        lastClassifiedTitle = title

        val apiKeyProvider = ApiKeyProvider()

        apiKeyProvider.getHuggingFaceKey(
            onSuccess = { hfApiKey ->
                CoroutineScope(Dispatchers.IO).launch {
                    Log.d("YT_CLASSIFIER", "Starting Dual-Layer Classification for: $title")

                    val titleSafetyDeferred = async {
                        kotlin.coroutines.suspendCoroutine { cont ->
                            VideoClassifier().classify(
                                title = title,
                                channel = "YouTube",
                                parentId = parentId,
                                childId = childId,
                                apiKey = hfApiKey,
                                onComplete = { category, confidence, safety ->
                                    cont.resumeWith(Result.success(safety))
                                },
                                onError = { e ->
                                    Log.e("YT_CLASSIFIER", "Title check failed", e)
                                    cont.resumeWith(Result.success("unknown"))
                                }
                            )
                        }
                    }

                    val subtitleSafetyDeferred = async {
                        kotlin.coroutines.suspendCoroutine { cont ->
                            com.sigmacoders.aichildmonitor.ai.SubtitleAnalyzer().analyze(
                                videoId = videoId ?: "",
                                title = title,
                                parentId = parentId,
                                childId = childId,
                                onComplete = { safety, pos, neg, tox ->
                                    cont.resumeWith(Result.success(safety))
                                },
                                onError = { e ->
                                    Log.e("YT_CLASSIFIER", "Subtitle check failed", e)
                                    cont.resumeWith(Result.success("unknown"))
                                }
                            )
                        }
                    }

                    val titleSafety = titleSafetyDeferred.await()
                    val subtitleSafety = subtitleSafetyDeferred.await()

                    // Unified strict safety logic
                    val combinedSafety = if (titleSafety == "unsafe" || subtitleSafety == "unsafe") {
                        "unsafe"
                    } else if (titleSafety == "safe" || subtitleSafety == "safe") {
                        "safe"
                    } else {
                        "unknown"
                    }

                    Log.i("YT_CLASSIFIER", "\n-----------------------------------------\n" +
                            "▶ Layer 1 (Title): $titleSafety\n" +
                            "▶ Layer 2 (Subtitle): $subtitleSafety\n" +
                            "→ Combined Decision: ${combinedSafety.uppercase()}\n" +
                            "-----------------------------------------")
                }
            },
            onFailure = { e ->
                Log.e("YT_CLASSIFIER", "Failed to fetch AI key", e)
            }
        )
    }
}
