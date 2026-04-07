package com.nyayasahayi.ui

import android.os.Bundle
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.nyayasahayi.R
import com.nyayasahayi.data.AppDatabase
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
//
//class CaseDetailActivity : AppCompatActivity() {
//
//    override fun onCreate(savedInstanceState: Bundle?) {
//        super.onCreate(savedInstanceState)
//        setContentView(R.layout.activity_case_detail)
//
//        val cnr = intent.getStringExtra("CNR_NUMBER") ?: return
//        val rawScanContent = intent.getStringExtra("RAW_SCAN_CONTENT")
//
//        val tvCnr = findViewById<TextView>(R.id.tv_detail_cnr)
//        val tvStatus = findViewById<TextView>(R.id.tv_detail_status)
//        val tvClient = findViewById<TextView>(R.id.tv_detail_client)
//        val tvHistory = findViewById<TextView>(R.id.tv_detail_history)
//        val btnAdd = findViewById<android.widget.Button>(R.id.btn_add_to_mycase)
//
//        tvCnr.text = "CNR: $cnr"
//
//        lifecycleScope.launch(Dispatchers.IO) {
//            val db = AppDatabase.getDatabase(applicationContext)
//            val caseItem = db.appDao().getCaseByCnr(cnr)
//
//            withContext(Dispatchers.Main) {
//                if (caseItem != null) {
//                    // Case Exists locally
//                    val clients = withContext(Dispatchers.IO) { db.appDao().getClientsForCase(caseItem.id) }
//                    val clientInfo = if (clients.isNotEmpty()) {
//                        clients.joinToString("\n") { "Client: ${it.name}\nPhone: ${it.phoneNumber}" }
//                    } else {
//                        "No Client Linked"
//                    }
//
//                    tvStatus.text = "Status: ${caseItem.status ?: "N/A"}\nNext Date: ${caseItem.nextDate ?: "N/A"}"
//                    tvClient.text = clientInfo
//                    tvHistory.text = "History/Details:\n${caseItem.historyJson}"
//                    btnAdd.visibility = android.view.View.GONE
//                } else {
//                    // Case NOT found locally
//                    tvStatus.text = "Case not found locally."
//                    btnAdd.visibility = android.view.View.VISIBLE
//
//                    if (rawScanContent != null && rawScanContent.startsWith("{")) {
//                        try {
//                            // Parse JSON from QR
//                            val jsonObject = org.json.JSONObject(rawScanContent)
//                            val status = jsonObject.optString("status")
//                            val nextDate = jsonObject.optString("next_date")
//                            val history = jsonObject.optString("history", "{}")
//
//                            tvStatus.text = "Status: $status\nNext Date: $nextDate"
//                            tvClient.text = "Details from Scan"
//                            tvHistory.text = "History/Details:\n$history"
//
//                            btnAdd.setOnClickListener {
//                                saveCase(cnr, status, nextDate, history)
//                            }
//                        } catch (e: Exception) {
//                            tvHistory.text = "Error parsing QR data: ${e.message}"
//                        }
//                    } else {
//                        tvHistory.text = "No local data and valid QR data found."
//                    }
//                }
//            }
//        }
//    }
//
//    private fun saveCase(cnr: String, status: String, nextDate: String, history: String) {
//        val btnAdd = findViewById<android.widget.Button>(R.id.btn_add_to_mycase)
//        btnAdd.isEnabled = false
//        btnAdd.text = "Saving..."
//
//        lifecycleScope.launch(Dispatchers.IO) {
//            try {
//                // 1. Save to Local DB (No FCM Token)
//                val db = AppDatabase.getDatabase(applicationContext)
//                val newCase = com.nyayasahayi.data.LocalCase(
//                    cnrNumber = cnr,
//                    status = status,
//                    nextDate = nextDate,
//                    historyJson = history,
//                    lastUpdatedAt = System.currentTimeMillis().toString()
//                )
//                db.appDao().insertCase(newCase)
//
//                // 2. Get FCM Token
//                val token = try {
//                    com.google.android.gms.tasks.Tasks.await(com.google.firebase.messaging.FirebaseMessaging.getInstance().token)
//                } catch (e: Exception) {
//                    "token_failed"
//                }
//
//                // 3. Save to MongoDB via MongoRepository (With FCM Token)
//                try {
//                     com.nyayasahayi.data.MongoRepository.insertCase(
//                         cnr = cnr,
//                         status = status,
//                         nextDate = nextDate,
//                         history = history,
//                         fcmToken = token
//                     )
//
//                     withContext(Dispatchers.Main) {
//                         android.widget.Toast.makeText(this@CaseDetailActivity, "Saved to MyCase & MongoDB", android.widget.Toast.LENGTH_SHORT).show()
//                         btnAdd.visibility = android.view.View.GONE
//                     }
//                } catch (e: Exception) {
//                    withContext(Dispatchers.Main) {
//                         android.widget.Toast.makeText(this@CaseDetailActivity, "Saved Locally but Mongo Error: ${e.message}", android.widget.Toast.LENGTH_LONG).show()
//                         btnAdd.visibility = android.view.View.GONE // Still hide as it's local now
//                    }
//                }
//
//            } catch (e: Exception) {
//                withContext(Dispatchers.Main) {
//                    android.widget.Toast.makeText(this@CaseDetailActivity, "Error calling API: ${e.message}", android.widget.Toast.LENGTH_LONG).show()
//                    btnAdd.isEnabled = true
//                    btnAdd.text = "Add to MyCase"
//                }
//            }
//        }
//    }
//}
class CaseDetailActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // 1. Get Data from Intent (passed from Scan or List)
        val cnr = intent.getStringExtra("CNR_NUMBER") ?: "Unknown"
        val rawJson = intent.getStringExtra("RAW_SCAN_CONTENT")

        // 2. Parse JSON to CaseRoot object (Pseudo-code)
        // val caseData = parseMyJson(rawJson)

        // For now, use the Mock Data so you can see the UI immediately
        val dummyData = getMockData() // Copy the mock data from the Preview above

        setContent {
            CaseDetailScreen(
                caseData = dummyData,
                onBackClick = { finish() } // Handle back button
            )
        }
    }
}

// This helper function creates the dummy data based on your JSON
fun getMockData(): CaseRoot {
    return CaseRoot(
        clientName = "Alan J Arackal", // Or pass this as a parameter
        caseDetails = CaseDetails(
            caseType = "ST",
            caseStatus = "PendingOffline",
            caseNo = "ST/100990/2022",
            cnrNumber = "KLER630018162022",
            nextListDate = "17-01-2026",
            actsAndSection = "Negotiable Instruments Act /138",
            establishment = "Judicial First Class Magistrate",
            filingDate = "07-11-2022",
            registrationDate = "07-11-2022"
        ),
        caseHistory = listOf(
            CaseHistoryItem(
                hearingDate = "06-12-2025",
                proceedings = "Complainant present accused absent represented considering the request of counsel for accused Pw1 is bound over to appear on payment of cost of Rs 500 to",
                judicialOfficer = "Smt.Samyuktha M K",
                purpose = "For cross examination.",
                nextDate = "17-01-2026"
            ),
            CaseHistoryItem(
                hearingDate = "22-10-2025",
                proceedings = "Complainant present represented Pw1 present Accused absent represented Counsel for accused sought time for an adjournmenet Hence Pw1 is bound over...",
                judicialOfficer = "Smt.Samyuktha M K",
                purpose = "Bound over",
                nextDate = "06-12-2025"
            ),
            CaseHistoryItem(
                hearingDate = "29-08-2025",
                proceedings = "Complainant present Accused absent represented Complainant was examined as PW1 Proof affidavit filed in leu of examination in chief...",
                judicialOfficer = "Smt.Samyuktha M K",
                purpose = "For cross examination.",
                nextDate = "22-10-2025"
            ),
            CaseHistoryItem(
                hearingDate = "16-08-2025",
                proceedings = "Complainant absent represented. Accused absent. Represented. For evidence of complainant.",
                judicialOfficer = "Smt.Samyuktha M K",
                purpose = "for evidence",
                nextDate = "29-08-2025"
            ),
            CaseHistoryItem(
                hearingDate = "07-06-2025",
                proceedings = "Govt declared Holiday Hence Notified to",
                judicialOfficer = "Smt.Samyuktha M K",
                purpose = "Declared Holidays",
                nextDate = "16-08-2025"
            )
        )
    )
}