package com.nyayasahayi.ui

import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.ktx.Firebase
import com.google.firebase.messaging.ktx.messaging
import com.nyayasahayi.service.FcmMessageRepository
import androidx.compose.ui.tooling.preview.Preview

//val DarkBg = Color(0xFF0D0D0D)
//val SurfaceColor = Color(0xFF1E1E1E)
//val PrimaryBlue = Color(0xFF3B82F6)

@Composable
fun RealFcmDemoApp() {
    var loggedInUser by remember { mutableStateOf<String?>(null) }
    val auth = FirebaseAuth.getInstance()

    // Check if user is already logged in from a previous session
    LaunchedEffect(Unit) {
        if (auth.currentUser != null) {
            loggedInUser = auth.currentUser?.email
        }
    }

    if (loggedInUser == null) {
        RealLoginScreen(
            onLoginSuccess = { email -> loggedInUser = email }
        )
    } else {
        TopicSubscriptionDashboard(
            userEmail = loggedInUser!!,
            onLogout = {
                auth.signOut()
                loggedInUser = null
            }
        )
    }
}
@Composable
fun TopicSubscriptionDashboard(userEmail: String, onLogout: () -> Unit) {
    var topicInput by remember { mutableStateOf("") }
    var activeSubscriptions by remember { mutableStateOf(listOf<String>()) }
    val context = LocalContext.current

    // Listen to real-time messages from the Repository
    val incomingMessages by FcmMessageRepository.messages.collectAsState()

    Column(modifier = Modifier.fillMaxSize().background(SurfaceColor).padding(20.dp)) {

        // --- HEADER ---
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Text("Logged in as:\n$userEmail", color = Color.Gray, fontSize = 14.sp)
            TextButton(onClick = onLogout) { Text("Sign Out", color = Color.Red) }
        }
        Spacer(modifier = Modifier.height(24.dp))

        // --- SUBSCRIPTION SECTION ---
        Text("1. Subscribe to Case Topic", color = Color.White, fontSize = 18.sp, fontWeight = FontWeight.Bold)
        Spacer(modifier = Modifier.height(8.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            OutlinedTextField(
                value = topicInput,
                onValueChange = { topicInput = it },
                placeholder = { Text("e.g. KLER630018162022", color = Color.DarkGray) },
                colors = OutlinedTextFieldDefaults.colors(focusedTextColor = Color.White, unfocusedTextColor = Color.White),
                modifier = Modifier.weight(1f)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Button(
                onClick = {
                    val topic = topicInput.trim()
                    if (topic.isNotEmpty()) {
                        // REAL FCM SUBSCRIPTION
                        Firebase.messaging.subscribeToTopic(topic).addOnCompleteListener { task ->
                            if (task.isSuccessful) {
                                activeSubscriptions = activeSubscriptions + topic
                                topicInput = ""
                                Toast.makeText(context, "Subscribed to $topic", Toast.LENGTH_SHORT).show()
                            } else {
                                Toast.makeText(context, "Subscription failed", Toast.LENGTH_SHORT).show()
                            }
                        }
                    }
                },
                colors = ButtonDefaults.buttonColors(containerColor = PrimaryBlue)
            ) {
                Icon(Icons.Default.Add, "Subscribe")
            }
        }

        // Active Subs Chips
        if (activeSubscriptions.isNotEmpty()) {
            Spacer(modifier = Modifier.height(8.dp))
            Text("Listening to:", color = Color.Gray, fontSize = 12.sp)
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                activeSubscriptions.forEach { sub ->
                    Surface(color = PrimaryBlue.copy(alpha = 0.2f), shape = RoundedCornerShape(16.dp)) {
                        Text(sub, color = PrimaryBlue, modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp), fontSize = 12.sp)
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(32.dp))

        // --- REAL-TIME RECEPTION SECTION ---
        Text("2. Live Incoming Payloads", color = Color.White, fontSize = 18.sp, fontWeight = FontWeight.Bold)
        Spacer(modifier = Modifier.height(8.dp))

        Card(
            colors = CardDefaults.cardColors(containerColor = SurfaceColor),
            modifier = Modifier.fillMaxWidth().weight(1f)
        ) {
            if (incomingMessages.isEmpty()) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("Waiting for server push...", color = Color.Gray)
                }
            } else {
                LazyColumn(contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    items(incomingMessages) { msg ->
                        Text(
                            text = msg,
                            color = Color(0xFF10B981), // Green for incoming data
                            fontSize = 14.sp,
                            modifier = Modifier.background(Color.Black.copy(alpha = 0.3f)).padding(8.dp).fillMaxWidth()
                        )
                    }
                }
            }
        }
    }
}

