package com.nyayasahayi.data

import com.mongodb.client.MongoClients
import com.mongodb.client.MongoCollection
import com.mongodb.client.MongoDatabase
import org.bson.Document
import android.util.Log

object MongoRepository {
    private const val TAG = "MongoRepository"
    private const val CONNECTION_STRING = "mongodb+srv://lawyer_user:12341234@casedata.trucxkk.mongodb.net/?appName=CaseData"
    
    // Lazy initialization of the client
    private val client by lazy {
        try {
            MongoClients.create(CONNECTION_STRING)
        } catch (e: Exception) {
            Log.e(TAG, "Error creating Mongo Client", e)
            null
        }
    }

    private val database: MongoDatabase?
        get() = client?.getDatabase("Case")

    private val collection: MongoCollection<Document>?
        get() = database?.getCollection("CaseDetails")

    fun insertCase(cnr: String, status: String, nextDate: String, history: String, fcmToken: String) {
        try {
            val doc = Document("cnr_number", cnr)
                .append("status", status)
                .append("next_date", nextDate)
                .append("history_json", history)
                .append("fcm_token", fcmToken)
                .append("created_at", System.currentTimeMillis())

            collection?.insertOne(doc)
            Log.d(TAG, "Document inserted successfully: $cnr")
        } catch (e: Exception) {
            Log.e(TAG, "Error inserting document", e)
            throw e // Rethrow to handle in UI
        }
    }
}
