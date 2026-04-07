package com.nyayasahayi.ui

import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.nyayasahayi.R
import com.nyayasahayi.data.AppDatabase
import com.nyayasahayi.data.ClientCaseMap
import com.nyayasahayi.data.LocalCase
import com.nyayasahayi.data.LocalClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class AddDataActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_add_data)

        val etName = findViewById<EditText>(R.id.et_client_name)
        val etPhone = findViewById<EditText>(R.id.et_client_phone)
        val etCnr = findViewById<EditText>(R.id.et_case_cnr)
        val etNextDate = findViewById<EditText>(R.id.et_next_date)
        val etStatus = findViewById<EditText>(R.id.et_status)
        val btnSave = findViewById<Button>(R.id.btn_save_data)

        btnSave.setOnClickListener {
            val name = etName.text.toString()
            val phone = etPhone.text.toString()
            val cnr = etCnr.text.toString()
            val date = etNextDate.text.toString()
            val status = etStatus.text.toString()

            if (name.isBlank() || phone.isBlank() || cnr.isBlank()) {
                Toast.makeText(this, "Please fill required fields (Name, Phone, CNR)", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            lifecycleScope.launch(Dispatchers.IO) {
                val db = AppDatabase.getDatabase(applicationContext)
                
                // 1. Handle Client (Check existence first to prevent cascading delete on REPLACE)
                val existingClient = db.appDao().getClientByPhone(phone)
                val clientId = if (existingClient != null) {
                    // Update name if needed, or just keep existing ID
                    // For now, let's assume we keep the ID and maybe update the name
                    // If we wanted to update, we'd need an @Update method or insert with same ID
                    existingClient.id
                } else {
                    val newClient = LocalClient(name = name, phoneNumber = phone, email = null, notes = "Manual Entry")
                    db.appDao().insertClient(newClient)
                }

                // 2. Handle Case
                val existingCase = db.appDao().getCaseByCnr(cnr)
                val caseId = if (existingCase != null) {
                    existingCase.id
                } else {
                    val newCase = LocalCase(
                        cnrNumber = cnr, 
                        nextDate = date, 
                        status = status, 
                        historyJson = "{\"manual_entry\": true, \"details\": \"Added manually\"}", 
                        lastUpdatedAt = System.currentTimeMillis().toString()
                    )
                    db.appDao().insertCase(newCase)
                }

                // 3. Map them (ignoring uniqueness constraints since we manually handled IDs, but good to be safe)
                // We need to check if map exists to avoid duplicate work or unique constraint errors if defined
                // But REPLACE on map is fine since it's just a link table with no cascade children usually
                val map = ClientCaseMap(clientId = clientId, caseId = caseId, role = "Petitioner")
                db.appDao().insertClientCaseMap(map)

                withContext(Dispatchers.Main) {
                    Toast.makeText(this@AddDataActivity, "Data Saved Safely!\nClient ID: $clientId, Case ID: $caseId", Toast.LENGTH_LONG).show()
                    finish()
                }
            }
        }
    }
}
