package com.sigmacoders.aichildmonitor

import android.content.Context
import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.sigmacoders.aichildmonitor.databinding.ActivityRoleSelectionBinding

class RoleSelectionActivity : AppCompatActivity() {

    private lateinit var binding: ActivityRoleSelectionBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // 1. Check if this device is already paired as a child
        val prefs = getSharedPreferences("AI_CHILD_MONITOR_PREFS", Context.MODE_PRIVATE)
        val savedParentId = prefs.getString("PARENT_ID", null)
        val savedChildId = prefs.getString("CHILD_ID", null)

        if (savedParentId != null && savedChildId != null) {
            // device is already paired, go straight to the child's home
            val intent = Intent(this, ChildHomeActivity::class.java).apply {
                putExtra("PARENT_ID", savedParentId)
                putExtra("CHILD_ID", savedChildId)
            }
            startActivity(intent)
            finish() // Close this activity so they can't go back to role selection
            return
        }

        // 2. If not paired, show the normal Role Selection UI
        binding = ActivityRoleSelectionBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.parentButton.setOnClickListener {
            val intent = Intent(this, LoginActivity::class.java)
            startActivity(intent)
        }

        binding.childButton.setOnClickListener {
            val intent = Intent(this, ChildLoginActivity::class.java)
            startActivity(intent)
        }
    }
}
