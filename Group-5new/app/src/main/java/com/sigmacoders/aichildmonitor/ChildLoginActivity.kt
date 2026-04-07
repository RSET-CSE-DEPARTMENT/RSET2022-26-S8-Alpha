package com.sigmacoders.aichildmonitor

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.widget.ArrayAdapter
import android.widget.EditText
import android.widget.Spinner
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.google.firebase.auth.ktx.auth
import com.google.firebase.firestore.ktx.firestore
import com.google.firebase.ktx.Firebase
import com.sigmacoders.aichildmonitor.databinding.ActivityChildLoginBinding

class ChildLoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityChildLoginBinding
    private val tag = "ChildLoginActivity"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityChildLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.pairButton.isEnabled = false
        binding.pairButton.text = "Authenticating..."

        if (Firebase.auth.currentUser == null) {
            authenticateAnonymously()
        } else {
            binding.pairButton.isEnabled = true
            binding.pairButton.text = "Pair Device"
        }

        binding.pairButton.setOnClickListener {
            if (Firebase.auth.currentUser == null) {
                binding.pairButton.isEnabled = false
                binding.pairButton.text = "Authenticating..."
                authenticateAnonymously()
                return@setOnClickListener
            }

            val pairingKey = binding.pairingKeyEditText.text.toString().trim()
            if (pairingKey.length == 4) {
                pairDevice(pairingKey)
            } else {
                Toast.makeText(this, "Please enter a valid 4-digit key", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun authenticateAnonymously() {
        Firebase.auth.signInAnonymously()
            .addOnSuccessListener {
                Log.d(tag, "Anonymous sign-in successful.")
                binding.pairButton.isEnabled = true
                binding.pairButton.text = "Pair Device"
            }
            .addOnFailureListener { e ->
                Log.e(tag, "Anonymous sign-in failed.", e)
                binding.pairButton.isEnabled = true
                binding.pairButton.text = "Retry Auth"
                val errorMsg = if (e.message?.contains("disabled") == true || e.message?.contains("configuration") == true) {
                    "Enable Anonymous Sign-In in Firebase Console!"
                } else {
                    "Authentication failed. Check connection."
                }
                Toast.makeText(this, errorMsg, Toast.LENGTH_LONG).show()
            }
    }

    private fun pairDevice(pairingKey: String) {
        val db = Firebase.firestore
        val pairingKeyRef = db.collection("pairingKeys").document(pairingKey)

        pairingKeyRef.get()
            .addOnSuccessListener { document ->
                if (!document.exists()) {
                    Toast.makeText(this, "Invalid pairing key.", Toast.LENGTH_SHORT).show()
                    return@addOnSuccessListener
                }

                val parentId = document.getString("parentId")
                if (parentId != null) {
                    showChildDetailsDialog(parentId, pairingKeyRef)
                } else {
                    Toast.makeText(this, "Invalid pairing data.", Toast.LENGTH_SHORT).show()
                }
            }
            .addOnFailureListener { e ->
                Log.w(tag, "Error checking pairing key", e)
                Toast.makeText(this, "Failed to pair device: ${e.message}", Toast.LENGTH_SHORT).show()
            }
    }

    private fun showChildDetailsDialog(parentId: String, pairingKeyRef: com.google.firebase.firestore.DocumentReference) {
        val dialogView = LayoutInflater.from(this).inflate(R.layout.dialog_child_details, null)
        val nameEditText = dialogView.findViewById<EditText>(R.id.childNameEditText)
        val ageEditText = dialogView.findViewById<EditText>(R.id.childAgeEditText)
        val genderSpinner = dialogView.findViewById<Spinner>(R.id.genderSpinner)

        // Populate the gender spinner
        val genders = arrayOf("Boy", "Girl")
        val adapter = ArrayAdapter(this, android.R.layout.simple_spinner_item, genders)
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        genderSpinner.adapter = adapter

        AlertDialog.Builder(this)
            .setTitle("Enter Your Details")
            .setView(dialogView)
            .setCancelable(false)
            .setPositiveButton("Confirm") { dialog, _ ->
                val childName = nameEditText.text.toString().trim()
                val childAgeStr = ageEditText.text.toString().trim()
                val gender = genderSpinner.selectedItem.toString()

                if (childName.isNotEmpty() && childAgeStr.isNotEmpty()) {
                    val childAge = childAgeStr.toInt()
                    createChildRecord(parentId, childName, childAge, gender, pairingKeyRef)
                } else {
                    Toast.makeText(this, "Please enter your name and age.", Toast.LENGTH_SHORT).show()
                }
                dialog.dismiss()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun createChildRecord(parentId: String, childName: String, age: Int, gender: String, pairingKeyRef: com.google.firebase.firestore.DocumentReference) {
        val db = Firebase.firestore
        val childData = hashMapOf(
            "name" to childName,
            "age" to age,
            "gender" to gender,
            "isPaired" to true,
            "parentId" to parentId,
            "riskLevel" to "Low",
            "journalText" to "No entry yet."
        )

        db.collection("users").document(parentId).collection("children")
            .add(childData)
            .addOnSuccessListener { childDocRef ->
                pairingKeyRef.delete()

                // Store IDs locally for the background service
                val prefs = getSharedPreferences("AI_CHILD_MONITOR_PREFS", Context.MODE_PRIVATE).edit()
                prefs.putString("PARENT_ID", parentId)
                prefs.putString("CHILD_ID", childDocRef.id)
                prefs.apply()

                Toast.makeText(this, "Device paired successfully!", Toast.LENGTH_SHORT).show()

                val intent = Intent(this, ChildHomeActivity::class.java)
                intent.putExtra("PARENT_ID", parentId)
                intent.putExtra("CHILD_ID", childDocRef.id)
                startActivity(intent)
                finishAffinity()
            }
            .addOnFailureListener { e ->
                Log.w(tag, "Failed to create child record", e)
                Toast.makeText(this, "Failed to finalize pairing: ${e.message}", Toast.LENGTH_SHORT).show()
            }
    }
}
