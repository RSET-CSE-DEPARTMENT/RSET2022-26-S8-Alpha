package com.sigmacoders.aichildmonitor

import android.util.Log
import com.google.firebase.firestore.FirebaseFirestore

class ApiKeyProvider {

    fun getHuggingFaceKey(
        onSuccess: (String) -> Unit,
        onFailure: (Exception) -> Unit
    ) {
        val db = FirebaseFirestore.getInstance()

        db.collection("appConfig")
            .document("huggingface")
            .get()
            .addOnSuccessListener { doc ->
                val key = doc.getString("apiKey")
                if (key != null) {
                    onSuccess(key)
                } else {
                    onFailure(Exception("API key not found in Firestore"))
                }
            }
            .addOnFailureListener { e ->
                onFailure(e)
            }
    }
    fun getYouTubeKey(
        onSuccess: (String) -> Unit,
        onFailure: (Exception) -> Unit
    ) {
        val db = FirebaseFirestore.getInstance()

        db.collection("appConfig")
            .document("youtube")
            .get()
            .addOnSuccessListener { doc ->
                val key = doc.getString("apiKey")
                if (key != null) {
                    onSuccess(key)
                } else {
                    onFailure(Exception("YouTube API key not found"))
                }
            }
            .addOnFailureListener { e ->
                onFailure(e)
            }
    }

}
