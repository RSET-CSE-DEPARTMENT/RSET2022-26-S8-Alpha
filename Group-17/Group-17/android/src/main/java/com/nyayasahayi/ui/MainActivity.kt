//
//package com.nyayasahayi.ui
//
//import android.content.Intent
//import android.content.pm.PackageManager
//import android.os.Build
//import android.os.Bundle
//import android.widget.Toast
//import androidx.activity.ComponentActivity
//import androidx.activity.compose.setContent
//import androidx.activity.enableEdgeToEdge
//import androidx.appcompat.app.AppCompatActivity // You can switch to ComponentActivity if you don't use Fragments
//import androidx.core.app.ActivityCompat
//import androidx.core.content.ContextCompat
//import com.nyayasahayi.NyayaGPTHomeScreen // Import your Compose Screen
//
//class MainActivity : AppCompatActivity() {
//
//    override fun onCreate(savedInstanceState: Bundle?) {
////        enableEdgeToEdge()
//        super.onCreate(savedInstanceState)
//
//        // 1. Setup Permissions (Your existing logic)
//        checkPermissions()
//
//        // 2. Load the New Compose UI
//        setContent {
//            // This loads the screen we designed earlier
//            NyayaGPTHomeScreen()
//        }
//    }
//
//    // Keep this for Overlay Permission results (Request Code 102)
//    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
//        if (requestCode == 102) {
//            // Check if overlay permission was granted after returning from settings
//            checkOverlayPermission()
//        } else {
//            super.onActivityResult(requestCode, resultCode, data)
//        }
//    }
//
//    private fun checkPermissions() {
//        val permissions = mutableListOf<String>()
//
//        if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.READ_PHONE_STATE) != PackageManager.PERMISSION_GRANTED) {
//            permissions.add(android.Manifest.permission.READ_PHONE_STATE)
//        }
//        if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.READ_CALL_LOG) != PackageManager.PERMISSION_GRANTED) {
//            permissions.add(android.Manifest.permission.READ_CALL_LOG)
//        }
//        if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
//            permissions.add(android.Manifest.permission.CAMERA)
//        }
//        if (Build.VERSION.SDK_INT >= 33) {
//            if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
//                permissions.add(android.Manifest.permission.POST_NOTIFICATIONS)
//            }
//        }
//        if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.SEND_SMS) != PackageManager.PERMISSION_GRANTED) {
//            permissions.add(android.Manifest.permission.SEND_SMS)
//        }
//
//        if (permissions.isNotEmpty()) {
//            ActivityCompat.requestPermissions(this, permissions.toTypedArray(), 101)
//        } else {
//            checkOverlayPermission()
//        }
//    }
//
//    private fun checkOverlayPermission() {
//        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
//            if (!android.provider.Settings.canDrawOverlays(this)) {
//                Toast.makeText(this, "Please grant 'Display over other apps' permission for Caller ID", Toast.LENGTH_LONG).show()
//                val intent = Intent(android.provider.Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
//                    android.net.Uri.parse("package:$packageName"))
//                startActivityForResult(intent, 102)
//            }
//        }
//    }
//
//    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
//        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
//        if (requestCode == 101) {
//            checkOverlayPermission()
//        }
//    }
//}
package com.nyayasahayi.ui

import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.compose.setContent
import androidx.appcompat.app.AppCompatActivity
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.google.firebase.auth.FirebaseAuth
import com.nyayasahayi.NyayaGPTHomeScreen
import com.google.firebase.FirebaseApp

class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // 2. ADD THIS LINE HERE (Must be before setContent)
        FirebaseApp.initializeApp(this)

        // 3. Setup Permissions
        checkPermissions()

        // 4. Load the UI

        setContent {
            // Now this won't crash!
            val auth = com.google.firebase.auth.FirebaseAuth.getInstance()
            // Check if a user is currently logged in
            var isLoggedIn by remember { mutableStateOf(auth.currentUser != null) }

            if (!isLoggedIn) {
                // If NOT logged in, show ONLY the Login Screen (Takes up the whole screen)
                com.nyayasahayi.ui.RealLoginScreen(
                    onLoginSuccess = {
                        isLoggedIn = true
                    }
                )
            } else {
                // If logged in, show the Home Screen with the bottom navigation
                NyayaGPTHomeScreen()
            }
        }
    }
//    override fun onCreate(savedInstanceState: Bundle?) {
//        super.onCreate(savedInstanceState)
//
//        // 1. Setup Permissions (Your existing logic)
//        checkPermissions()
//
//        // 2. Load the UI with the Auth Gatekeeper
//        setContent {
//            // Check if user is already logged in
//            val auth = FirebaseAuth.getInstance()
//            var isLoggedIn by remember { mutableStateOf(auth.currentUser != null) }
//
//            if (isLoggedIn) {
//                // User is authenticated -> Show existing Home Screen
//                NyayaGPTHomeScreen()
//            } else {
//                // User is NOT authenticated -> Show Login Screen
//                RealLoginScreen(
//                    onLoginSuccess = {
//                        isLoggedIn = true
//                    }
//                )
//            }
//        }
//    }

    // Keep this for Overlay Permission results (Request Code 102)
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        if (requestCode == 102) {
            checkOverlayPermission()
        } else {
            super.onActivityResult(requestCode, resultCode, data)
        }
    }

    private fun checkPermissions() {
        val permissions = mutableListOf<String>()

        if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.READ_PHONE_STATE) != PackageManager.PERMISSION_GRANTED) {
            permissions.add(android.Manifest.permission.READ_PHONE_STATE)
        }
        if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.READ_CALL_LOG) != PackageManager.PERMISSION_GRANTED) {
            permissions.add(android.Manifest.permission.READ_CALL_LOG)
        }
        if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            permissions.add(android.Manifest.permission.CAMERA)
        }
        if (Build.VERSION.SDK_INT >= 33) {
            if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                permissions.add(android.Manifest.permission.POST_NOTIFICATIONS)
            }
        }
        if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.SEND_SMS) != PackageManager.PERMISSION_GRANTED) {
            permissions.add(android.Manifest.permission.SEND_SMS)
        }

        if (permissions.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, permissions.toTypedArray(), 101)
        } else {
            checkOverlayPermission()
        }
    }

    private fun checkOverlayPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            if (!android.provider.Settings.canDrawOverlays(this)) {
                Toast.makeText(this, "Please grant 'Display over other apps' permission for Caller ID", Toast.LENGTH_LONG).show()
                val intent = Intent(android.provider.Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    android.net.Uri.parse("package:$packageName"))
                startActivityForResult(intent, 102)
            }
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 101) {
            checkOverlayPermission()
        }
    }
}

// --- COMPOSE LOGIN SCREEN ---
// You can keep this here in MainActivity.kt or move it to a separate file.

@Composable
fun RealLoginScreen(onLoginSuccess: (String) -> Unit) {
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var isLoading by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    val auth = FirebaseAuth.getInstance()

    // Theme Colors
    val darkBg = Color(0xFF0D0D0D)
    val surfaceColor = Color(0xFF1E1E1E)
    val primaryBlue = Color(0xFF3B82F6)

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(darkBg)
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text("NyayaSahayi", color = Color.White, fontSize = 32.sp, fontWeight = FontWeight.Bold)
        Text("Lawyer Login", color = primaryBlue, fontSize = 16.sp)

        Spacer(modifier = Modifier.height(32.dp))

        Card(colors = CardDefaults.cardColors(containerColor = surfaceColor)) {
            Column(modifier = Modifier.padding(24.dp)) {

                if (errorMessage != null) {
                    Text(errorMessage!!, color = Color.Red, fontSize = 12.sp, modifier = Modifier.padding(bottom = 8.dp))
                }

                OutlinedTextField(
                    value = email,
                    onValueChange = { email = it },
                    label = { Text("Email", color = Color.Gray) },
                    leadingIcon = { Icon(Icons.Default.Person, null, tint = Color.Gray) },
                    colors = OutlinedTextFieldDefaults.colors(focusedTextColor = Color.White, unfocusedTextColor = Color.White),
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(modifier = Modifier.height(16.dp))

                OutlinedTextField(
                    value = password,
                    onValueChange = { password = it },
                    label = { Text("Password", color = Color.Gray) },
                    leadingIcon = { Icon(Icons.Default.Lock, null, tint = Color.Gray) },
                    visualTransformation = PasswordVisualTransformation(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                    colors = OutlinedTextFieldDefaults.colors(focusedTextColor = Color.White, unfocusedTextColor = Color.White),
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(modifier = Modifier.height(24.dp))

                Button(
                    onClick = {
                        if (email.isBlank() || password.isBlank()) {
                            errorMessage = "Fields cannot be blank"
                            return@Button
                        }

                        isLoading = true
                        errorMessage = null

                        auth.signInWithEmailAndPassword(email.trim(), password.trim())
                            .addOnCompleteListener { task ->
                                isLoading = false
                                if (task.isSuccessful) {
                                    onLoginSuccess(email)
                                } else {
                                    errorMessage = task.exception?.localizedMessage ?: "Login failed"
                                }
                            }
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(50.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = primaryBlue),
                    enabled = !isLoading
                ) {
                    if (isLoading) {
                        CircularProgressIndicator(color = Color.White, modifier = Modifier.size(24.dp))
                    } else {
                        Text("Secure Login", color = Color.White, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }
}