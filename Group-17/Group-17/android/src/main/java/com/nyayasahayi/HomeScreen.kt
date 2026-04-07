//package com.nyayasahayi
//
//import android.app.Activity
//import android.content.Intent
//import android.widget.Toast
//import androidx.activity.compose.rememberLauncherForActivityResult
//import androidx.compose.foundation.background
//import androidx.compose.foundation.layout.*
//import androidx.compose.foundation.shape.CircleShape
//import androidx.compose.foundation.shape.RoundedCornerShape
//import androidx.compose.material.icons.Icons
//import androidx.compose.material.icons.filled.*
//import androidx.compose.material.icons.outlined.*
//import androidx.compose.material3.*
//import androidx.compose.runtime.*
//import androidx.compose.ui.Alignment
//import androidx.compose.ui.Modifier
//import androidx.compose.ui.draw.clip
//import androidx.compose.ui.graphics.Color
//import androidx.compose.ui.platform.LocalContext
//import androidx.compose.ui.text.font.FontWeight
//import androidx.compose.ui.tooling.preview.Preview
//import androidx.compose.ui.tooling.preview.PreviewParameter
//import androidx.compose.ui.unit.dp
//import androidx.compose.ui.unit.sp
//import com.google.zxing.integration.android.IntentIntegrator
//import com.journeyapps.barcodescanner.ScanContract
//import com.journeyapps.barcodescanner.ScanOptions
//import com.nyayasahayi.ui.AddDataActivity
//import com.nyayasahayi.ui.ViewDataActivity
//import androidx.compose.foundation.lazy.LazyColumn
//import androidx.compose.foundation.lazy.items
//import androidx.compose.foundation.text.KeyboardActions
//import androidx.compose.foundation.text.KeyboardOptions
//import androidx.compose.ui.text.input.ImeAction
//import androidx.compose.material.icons.automirrored.filled.Send // Note: auto-mirrored for RTL support
//// Add this if CalendarScreen is in the 'ui' package
//import com.nyayasahayi.ui.CalendarScreen
//import android.os.Build // Needed for the version check
//
//@OptIn(ExperimentalMaterial3Api::class)
//@Composable
//fun NyayaGPTHomeScreen() {
//    var currentScreen by remember { mutableStateOf("Chat") }
//    val context = LocalContext.current
//
//    val backgroundColor = Color(0xFF0D0D0D)
//    val primaryBlue = Color(0xFF3B82F6)
//    val surfaceColor = Color(0xFF1A1C1E)
//
//    Scaffold(
//        topBar = {
//            CenterAlignedTopAppBar(
//                title = {
//                    Text(
//                        "NyayaSahayi",
//                        color = Color.White,
//                        fontWeight = FontWeight.Bold,
//                        fontSize = 20.sp
//                    )
//                },
//                navigationIcon = {
//                    IconButton(onClick = { currentScreen = "FCM_Demo" }) { // <--- Added state change here
//                        Icon(Icons.Default.Menu, contentDescription = "Menu", tint = Color.White)
//                    }
//                },
////                navigationIcon = {
////                    IconButton(onClick = { /* Handle Menu */ }) {
////                        Icon(Icons.Default.Menu, contentDescription = "Menu", tint = Color.White)
////                    }
////                },
//                actions = {
//                    Box(
//                        modifier = Modifier
//                            .padding(end = 16.dp)
//                            .size(34.dp)
//                            .clip(CircleShape)
//                            .background(primaryBlue),
//                        contentAlignment = Alignment.Center
//                    ) {
//                        Text(
//                            "A",
//                            color = Color.White,
//                            fontWeight = FontWeight.Bold,
//                            fontSize = 14.sp
//                        )
//                    }
//                },
//                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
//                    containerColor = backgroundColor
//                )
//            )
//        },
//        bottomBar = {
//            Column(modifier = Modifier.background(backgroundColor)) {
//                Row(
//                    modifier = Modifier
//                        .fillMaxWidth()
//                        .padding(vertical = 8.dp),
//                    horizontalArrangement = Arrangement.SpaceAround,
//                    verticalAlignment = Alignment.CenterVertically
//                ) {
//                    BottomNavItem(
//                        label = "Chat",
//                        icon = if (currentScreen == "Chat") Icons.Filled.ChatBubble else Icons.Outlined.ChatBubbleOutline,
//                        isSelected = currentScreen == "Chat",
//                        activeColor = primaryBlue,
//                        onClick = { currentScreen = "Chat" }
//                    )
//                    BottomNavItem(
//                        label = "Client",
//                        icon = Icons.Outlined.Person2,
//                        isSelected = currentScreen == "Client",
//                        activeColor = primaryBlue,
//                        onClick = { currentScreen = "Client" }
//                    )
//                    BottomNavItem(
//                        label = "Calendar",
//                        icon = Icons.Outlined.CalendarToday,
//                        isSelected = currentScreen == "Calendar",
//                        activeColor = primaryBlue,
//                        onClick = { currentScreen = "Calendar" }
//                    )
//                    BottomNavItem(
//                        label = "Document",
//                        icon = Icons.Outlined.Description,
//                        isSelected = currentScreen == "Document",
//                        activeColor = primaryBlue,
//                        onClick = { currentScreen = "Document" }
//                    )
//                }
//            }
//        }
//    ) { innerPadding ->
//        Box(
//            modifier = Modifier
//                .fillMaxSize()
//                .background(backgroundColor)
//                .padding(innerPadding)
//        ) {
//            when (currentScreen) {
//                "Chat" -> ChatScreenContent(primaryBlue, surfaceColor)
//                "Calendar" -> {
//                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
//                        CalendarScreen() // <--- Calls the screen from your separate file
//                    } else {
//                        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
//                            Text("Calendar requires Android 8.0+", color = Color.White)
//                        }
//                    }
//                }
//                "Document" -> Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
//                    Text("Document Coming Soon", color = Color.White)
//                }
//                "FCM_Demo" -> {
//                    val auth = com.google.firebase.auth.FirebaseAuth.getInstance()
//                    val userEmail = auth.currentUser?.email ?: "Lawyer"
//
//                    com.nyayasahayi.ui.TopicSubscriptionDashboard(
//                        userEmail = userEmail,
//                        onLogout = {
//                            auth.signOut()
//                            // Restart the activity to instantly send the user back to the login screen
//                            (context as? android.app.Activity)?.recreate()
//                        }
//                    )
//                }
//                "Client" -> ClientScreenContent(context)
//                else -> Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
//                    Text("Coming Soon", color = Color.White)
//                }
//
//            }
//        }
//    }
//}
//
//@Composable
//fun BottomNavItem(
//    label: String,
//    icon: androidx.compose.ui.graphics.vector.ImageVector,
//    isSelected: Boolean,
//    activeColor: Color,
//    onClick: () -> Unit
//) {
//    Column(
//        horizontalAlignment = Alignment.CenterHorizontally,
//        modifier = Modifier.width(80.dp)
//    ) {
//        IconButton(onClick = onClick) {
//            Icon(
//                imageVector = icon,
//                contentDescription = label,
//                tint = if (isSelected) activeColor else Color.Gray,
//                modifier = Modifier.size(24.dp)
//            )
//        }
//        Text(
//            text = label,
//            color = if (isSelected) activeColor else Color.Gray,
//            fontSize = 11.sp,
//            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal
//        )
//        Spacer(modifier = Modifier.height(6.dp))
//        if (isSelected) {
//            Box(
//                modifier = Modifier
//                    .width(18.dp)
//                    .height(2.dp)
//                    .clip(RoundedCornerShape(1.dp))
//                    .background(activeColor)
//            )
//        } else {
//            Spacer(modifier = Modifier.height(2.dp))
//        }
//    }
//}
//
//
//@Composable
//fun ChatScreenContent(primaryBlue: Color, surfaceColor: Color) {
//    // 1. STATE: Manage the text input and the list of messages
//    var userQuery by remember { mutableStateOf("") }
//    var chatMessages by remember { mutableStateOf(listOf<ChatMessage>()) }
//
//    Column(
//        modifier = Modifier
//            .fillMaxSize()
//            .padding(horizontal = 24.dp, vertical = 15.dp)
//    ) {
//        // 2. CHAT HISTORY (Takes up all available space)
//        LazyColumn(
//            modifier = Modifier.weight(1f),
//            verticalArrangement = Arrangement.spacedBy(8.dp),
//            contentPadding = PaddingValues(bottom = 16.dp) // Add padding so last item isn't hidden
//        ) {
//            // Initial Welcome Text (Only show if chat is empty)
//            if (chatMessages.isEmpty()) {
//                item {
//                    Column(
//                        modifier = Modifier.fillParentMaxSize(),
//                        verticalArrangement = Arrangement.Center,
//                        horizontalAlignment = Alignment.CenterHorizontally
//                    ) {
//                        Text(
//                            text = "Hello,",
//                            color = primaryBlue,
//                            fontSize = 30.sp,
//                            fontWeight = FontWeight.Medium
//                        )
//                        Text(
//                            text = "How can i help you?",
//                            color = primaryBlue,
//                            fontSize = 30.sp,
//                            fontWeight = FontWeight.Medium,
//                            lineHeight = 40.sp,
//                            textAlign = androidx.compose.ui.text.style.TextAlign.Center
//                        )
//                    }
//                }
//            }
//
//            // The Messages
//            items(chatMessages) { message ->
//                MessageBubble(message, primaryBlue, surfaceColor)
//            }
//        }
//
//        // 3. INPUT AREA (Modified as requested)
//        Row(
//            modifier = Modifier
//                .fillMaxWidth()
//                .height(64.dp)
//                .clip(RoundedCornerShape(32.dp))
//                .background(surfaceColor)
//                .padding(horizontal = 16.dp), // Added padding inside the capsule
//            verticalAlignment = Alignment.CenterVertically
//        ) {
//            // INPUT FIELD
//            TextField(
//                value = userQuery,
//                onValueChange = { userQuery = it },
//                placeholder = { Text("Ask NyayaSahayi", color = Color.Gray.copy(alpha = 0.6f)) },
//                colors = TextFieldDefaults.colors(
//                    focusedContainerColor = Color.Transparent,
//                    unfocusedContainerColor = Color.Transparent,
//                    focusedIndicatorColor = Color.Transparent,
//                    unfocusedIndicatorColor = Color.Transparent,
//                    cursorColor = primaryBlue,
//                    focusedTextColor = Color.White,
//                    unfocusedTextColor = Color.White
//                ),
//                modifier = Modifier.weight(1f),
//                singleLine = true,
//                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
//                keyboardActions = KeyboardActions(onSend = {
//                    if (userQuery.isNotBlank()) {
//                        val query = userQuery
//                        // Add User Message
//                        chatMessages = chatMessages + ChatMessage(query, true)
//                        userQuery = "" // Clear input
//
//                        // TODO: Call your Server API here
//                        // For now, we simulate a bot response after 1 second
//                        chatMessages = chatMessages + ChatMessage("Searching for: $query...", false)
//                    }
//                })
//            )
//
//            IconButton(
//                onClick = {
//                    if (userQuery.isNotBlank()) {
//                        val query = userQuery
//                        chatMessages = chatMessages + ChatMessage(query, true)
//                        userQuery = ""
//
//                        // Mock Bot Response
//                        chatMessages = chatMessages + ChatMessage("Here is the answer for: $query", false)
//                    }
//                }
//            ) {
//                Icon(
//                    imageVector = Icons.AutoMirrored.Filled.Send,
//                    contentDescription = "Send",
//                    tint = primaryBlue
//                )
//            }
//        }
//    }
//}
//
//// 4. HELPER: How a single message bubble looks
//@Composable
//fun MessageBubble(message: ChatMessage, primaryBlue: Color, surfaceColor: Color) {
//    Row(
//        modifier = Modifier.fillMaxWidth(),
//        horizontalArrangement = if (message.isUser) Arrangement.End else Arrangement.Start
//    ) {
//        Surface(
//            color = if (message.isUser) primaryBlue else surfaceColor,
//            shape = RoundedCornerShape(
//                topStart = 16.dp,
//                topEnd = 16.dp,
//                bottomStart = if (message.isUser) 16.dp else 0.dp,
//                bottomEnd = if (message.isUser) 0.dp else 16.dp
//            ),
//            modifier = Modifier.widthIn(max = 280.dp) // Max width of bubble
//        ) {
//            Text(
//                text = message.text,
//                color = Color.White,
//                modifier = Modifier.padding(16.dp),
//                fontSize = 16.sp
//            )
//        }
//    }
//}
////fun ChatScreenContent(primaryBlue: Color, surfaceColor: Color) {
////    Column(
////        modifier = Modifier
////            .fillMaxSize()
////            .padding(horizontal = 24.dp, vertical = 15.dp),
////        horizontalAlignment = Alignment.CenterHorizontally
////    ) {
////        Spacer(modifier = Modifier.weight(1f))
////
////        Column(horizontalAlignment = Alignment.CenterHorizontally) {
////            Text(
////                text = "Hello,",
////                color = primaryBlue,
////                fontSize = 36.sp,
////                fontWeight = FontWeight.Medium
////            )
////            Text(
////                text = "How can i help you?",
////                color = primaryBlue,
////                fontSize = 32.sp,
////                fontWeight = FontWeight.Medium
////            )
////        }
////
////        Spacer(modifier = Modifier.weight(1.5f))
////
////        // Search Bar matching the image
////        Row(
////            modifier = Modifier
////                .fillMaxWidth()
////                .height(64.dp)
////                .clip(RoundedCornerShape(32.dp))
////                .background(surfaceColor)
////                .padding(horizontal = 1.dp),
////            verticalAlignment = Alignment.CenterVertically
////        ) {
////            Icon(
////                imageVector = Icons.Default.Add,
////                contentDescription = "Add",
////                tint = Color.Gray,
////                modifier = Modifier.size(24.dp)
////            )
////            Spacer(modifier = Modifier.width(12.dp))
////            Text(
////                text = "Ask NyayaSahayi",
////                color = Color.Gray.copy(alpha = 0.6f),
////                modifier = Modifier.weight(1f),
////                fontSize = 16.sp
////            )
////            Icon(
////                imageVector = Icons.Default.Mic,
////                contentDescription = "Voice",
////                tint = Color.Gray,
////                modifier = Modifier.size(24.dp)
////            )
////        }
////        Spacer(modifier = Modifier.height(16.dp))
////    }
////}
//
//
//@Composable
//fun ClientScreenContent(context: android.content.Context) {
//
//    // 1. Define the Scan Logic Here (Modern "launcher" approach)
//    val qrLauncher = rememberLauncherForActivityResult(ScanContract()) { result ->
//        if (result.contents == null) {
//            Toast.makeText(context, "Cancelled", Toast.LENGTH_LONG).show()
//        } else {
//            val scanContent = result.contents
//            // 2. YOUR PARSING LOGIC MOVED HERE
//            val cnr = if (scanContent.contains("cnr=")) {
//                scanContent.substringAfter("cnr=")
//            } else {
//                scanContent
//            }
//
//            Toast.makeText(context, "Scanned: $cnr", Toast.LENGTH_LONG).show()
//
//            // 3. Launch CaseDetailActivity
//            // Note: Ensure CaseDetailActivity is imported or use full package path
//            val intent = Intent(context, com.nyayasahayi.ui.CaseDetailActivity::class.java).apply {
//                putExtra("CNR_NUMBER", cnr)
//                putExtra("RAW_SCAN_CONTENT", scanContent)
//            }
//            context.startActivity(intent)
//        }
//    }
//
//    Column(
//        modifier = Modifier.fillMaxSize(),
//        verticalArrangement = Arrangement.Center,
//        horizontalAlignment = Alignment.CenterHorizontally
//    ) {
//        // SCAN BUTTON
//        Button(
//            onClick = {
//                val options = ScanOptions()
//                options.setDesiredBarcodeFormats(ScanOptions.QR_CODE)
//                options.setPrompt("Scan Case QR Code")
//                options.setCameraId(0)
//                options.setBeepEnabled(false)
//                options.setBarcodeImageEnabled(false)
//                qrLauncher.launch(options)
//            },
//            modifier = Modifier.fillMaxWidth(0.8f).padding(8.dp),
//            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF3B82F6))
//        ) {
//            Text("Scan QR Code")
//        }
//
//        // ADD DATA BUTTON
//        Button(
//            onClick = {
//                context.startActivity(Intent(context, AddDataActivity::class.java))
//            },
//            modifier = Modifier.fillMaxWidth(0.8f).padding(8.dp),
//            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF3B82F6))
//        ) {
//            Text("Add Data")
//        }
//
//        // VIEW DATA BUTTON
//        Button(
//            onClick = {
//                context.startActivity(Intent(context, ViewDataActivity::class.java))
//            },
//            modifier = Modifier.fillMaxWidth(0.8f).padding(8.dp),
//            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF3B82F6))
//        ) {
//            Text("View Data")
//        }
//    }
//}
//data class ChatMessage(
//    val text: String,
//    val isUser: Boolean // true = User, false = Bot
//)
////@Preview
////@Composable
////fun PreviewClientScreen() {
////    // We provide the missing parameter here manually
////    ClientScreenContent(context = LocalContext.current)
////}
//
////@Preview
////@Composable
////fun PreviewChatScreen() {
////    // Define dummy colors for the preview
////    val primaryBlue = Color(0xFF3B82F6)
////    val surfaceColor = Color(0xFF1A1C1E)
////
////    // Call your function with the dummy data
////    ChatScreenContent(primaryBlue = primaryBlue, surfaceColor = surfaceColor)
////}



package com.nyayasahayi

import android.app.Activity
import android.content.Intent
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.journeyapps.barcodescanner.ScanContract
import com.journeyapps.barcodescanner.ScanOptions
import com.nyayasahayi.ui.AddDataActivity
import com.nyayasahayi.ui.ViewDataActivity
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.material.icons.automirrored.filled.Send
import com.nyayasahayi.ui.CalendarScreen
import com.nyayasahayi.ui.DocumentEditorScreen  // <-- Import the new screen
import android.os.Build
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

data class CaseResult(
    val caseNumber: String,
    val clientName: String,
    val status: String
)
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NyayaGPTHomeScreen() {
    var currentScreen by remember { mutableStateOf("Chat") }
    val context = LocalContext.current

    val backgroundColor = Color(0xFF0D0D0D)
    val primaryBlue = Color(0xFF3B82F6)
    val surfaceColor = Color(0xFF1A1C1E)

    // If Document editor is open, show it full-screen (no top/bottom bars)
    if (currentScreen == "Document") {
        DocumentEditorScreen(
            documentTitle = "Untitled Legal Document",
            onBack = { currentScreen = "Chat" } // back arrow returns to Chat
        )
        return
    }

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = {
                    Text(
                        "NyayaSahayi",
                        color = Color.White,
                        fontWeight = FontWeight.Bold,
                        fontSize = 20.sp
                    )
                },
                navigationIcon = {
                    IconButton(onClick = { currentScreen = "FCM_Demo" }) {
                        Icon(Icons.Default.Menu, contentDescription = "Menu", tint = Color.White)
                    }
                },
                actions = {
                    Box(
                        modifier = Modifier
                            .padding(end = 16.dp)
                            .size(34.dp)
                            .clip(CircleShape)
                            .background(primaryBlue),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            "A",
                            color = Color.White,
                            fontWeight = FontWeight.Bold,
                            fontSize = 14.sp
                        )
                    }
                },
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                    containerColor = backgroundColor
                )
            )
        },
        bottomBar = {
            Column(modifier = Modifier.background(backgroundColor)) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 8.dp),
                    horizontalArrangement = Arrangement.SpaceAround,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    BottomNavItem(
                        label = "Chat",
                        icon = if (currentScreen == "Chat") Icons.Filled.ChatBubble else Icons.Outlined.ChatBubbleOutline,
                        isSelected = currentScreen == "Chat",
                        activeColor = primaryBlue,
                        onClick = { currentScreen = "Chat" }
                    )
                    BottomNavItem(
                        label = "Client",
                        icon = Icons.Outlined.Person2,
                        isSelected = currentScreen == "Client",
                        activeColor = primaryBlue,
                        onClick = { currentScreen = "Client" }
                    )
                    BottomNavItem(
                        label = "Calendar",
                        icon = Icons.Outlined.CalendarToday,
                        isSelected = currentScreen == "Calendar",
                        activeColor = primaryBlue,
                        onClick = { currentScreen = "Calendar" }
                    )
                    BottomNavItem(
                        label = "Document",
                        icon = Icons.Outlined.Description,
                        isSelected = currentScreen == "Document",
                        activeColor = primaryBlue,
                        onClick = { currentScreen = "Document" }
                    )
                }
            }
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(backgroundColor)
                .padding(innerPadding)
        ) {
            when (currentScreen) {
                "Chat" -> ChatScreenContent(primaryBlue, surfaceColor)
                "Calendar" -> {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        CalendarScreen()
                    } else {
                        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                            Text("Calendar requires Android 8.0+", color = Color.White)
                        }
                    }
                }
                "FCM_Demo" -> {
                    val auth = com.google.firebase.auth.FirebaseAuth.getInstance()
                    val userEmail = auth.currentUser?.email ?: "Lawyer"
                    com.nyayasahayi.ui.TopicSubscriptionDashboard(
                        userEmail = userEmail,
                        onLogout = {
                            auth.signOut()
                            (context as? android.app.Activity)?.recreate()
                        }
                    )
                }
                "Client" -> ClientScreenContent(context)
                else -> Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("Coming Soon", color = Color.White)
                }
            }
        }
    }
}

@Composable
fun BottomNavItem(
    label: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    isSelected: Boolean,
    activeColor: Color,
    onClick: () -> Unit
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier.width(80.dp)
    ) {
        IconButton(onClick = onClick) {
            Icon(
                imageVector = icon,
                contentDescription = label,
                tint = if (isSelected) activeColor else Color.Gray,
                modifier = Modifier.size(24.dp)
            )
        }
        Text(
            text = label,
            color = if (isSelected) activeColor else Color.Gray,
            fontSize = 11.sp,
            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal
        )
        Spacer(modifier = Modifier.height(6.dp))
        if (isSelected) {
            Box(
                modifier = Modifier
                    .width(18.dp)
                    .height(2.dp)
                    .clip(RoundedCornerShape(1.dp))
                    .background(activeColor)
            )
        } else {
            Spacer(modifier = Modifier.height(2.dp))
        }
    }
}

@Composable
fun ChatScreenContent(primaryBlue: Color, surfaceColor: Color) {
    var userQuery by remember { mutableStateOf("") }
    var chatMessages by remember { mutableStateOf(listOf<ChatMessage>()) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 24.dp, vertical = 15.dp)
    ) {
        LazyColumn(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(8.dp),
            contentPadding = PaddingValues(bottom = 16.dp)
        ) {
            if (chatMessages.isEmpty()) {
                item {
                    Column(
                        modifier = Modifier.fillParentMaxSize(),
                        verticalArrangement = Arrangement.Center,
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text("Hello,", color = primaryBlue, fontSize = 30.sp, fontWeight = FontWeight.Medium)
                        Text(
                            "How can i help you?",
                            color = primaryBlue, fontSize = 30.sp, fontWeight = FontWeight.Medium,
                            lineHeight = 40.sp,
                            textAlign = androidx.compose.ui.text.style.TextAlign.Center
                        )
                    }
                }
            }
            items(chatMessages) { message ->
                MessageBubble(message, primaryBlue, surfaceColor)
            }
        }

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .height(64.dp)
                .clip(RoundedCornerShape(32.dp))
                .background(surfaceColor)
                .padding(horizontal = 16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            TextField(
                value = userQuery,
                onValueChange = { userQuery = it },
                placeholder = { Text("Ask NyayaSahayi", color = Color.Gray.copy(alpha = 0.6f)) },
                colors = TextFieldDefaults.colors(
                    focusedContainerColor = Color.Transparent,
                    unfocusedContainerColor = Color.Transparent,
                    focusedIndicatorColor = Color.Transparent,
                    unfocusedIndicatorColor = Color.Transparent,
                    cursorColor = primaryBlue,
                    focusedTextColor = Color.White,
                    unfocusedTextColor = Color.White
                ),
                modifier = Modifier.weight(1f),
                singleLine = true,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                keyboardActions = KeyboardActions(onSend = {
                    if (userQuery.isNotBlank()) {
                        val query = userQuery
                        chatMessages = chatMessages + ChatMessage(query, true)
                        userQuery = ""
                        chatMessages = chatMessages + ChatMessage("Searching for: $query...", false)
                    }
                })
            )
            IconButton(
                onClick = {
                    if (userQuery.isNotBlank()) {
                        val query = userQuery
                        chatMessages = chatMessages + ChatMessage(query, true)
                        userQuery = ""
                        chatMessages = chatMessages + ChatMessage("Here is the answer for: $query", false)
                    }
                }
            ) {
                Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Send", tint = primaryBlue)
            }
        }
    }
}

@Composable
fun MessageBubble(message: ChatMessage, primaryBlue: Color, surfaceColor: Color) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = if (message.isUser) Arrangement.End else Arrangement.Start
    ) {
        Surface(
            color = if (message.isUser) primaryBlue else surfaceColor,
            shape = RoundedCornerShape(
                topStart = 16.dp, topEnd = 16.dp,
                bottomStart = if (message.isUser) 16.dp else 0.dp,
                bottomEnd = if (message.isUser) 0.dp else 16.dp
            ),
            modifier = Modifier.widthIn(max = 280.dp)
        ) {
            Text(text = message.text, color = Color.White, modifier = Modifier.padding(16.dp), fontSize = 16.sp)
        }
    }
}

@Composable
fun ClientScreenContent(context: android.content.Context) {
    // State variables for search and results
    var searchQuery by remember { mutableStateOf("") }
    var searchResults by remember { mutableStateOf(emptyList<CaseResult>()) }
    var isLoading by remember { mutableStateOf(false) }

    // Coroutine scope for simulating network delay
    val coroutineScope = rememberCoroutineScope()

    // Existing QR Scanner Logic
    val qrLauncher = rememberLauncherForActivityResult(ScanContract()) { result ->
        if (result.contents == null) {
            Toast.makeText(context, "Cancelled", Toast.LENGTH_LONG).show()
        } else {
            val scanContent = result.contents
            val cnr = if (scanContent.contains("cnr=")) {
                scanContent.substringAfter("cnr=")
            } else {
                scanContent
            }
            Toast.makeText(context, "Scanned: $cnr", Toast.LENGTH_LONG).show()
            val intent = Intent(context, com.nyayasahayi.ui.CaseDetailActivity::class.java).apply {
                putExtra("CNR_NUMBER", cnr)
                putExtra("RAW_SCAN_CONTENT", scanContent)
            }
            context.startActivity(intent)
        }
    }

    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // --- TOP SECTION: Search Bar and Buttons ---
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 32.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Combined Search Bar with QR Scanner Icon
            OutlinedTextField(
                value = searchQuery,
                onValueChange = { searchQuery = it },
                label = { Text("Enter Case No. or Client Name", color = Color.Gray) },
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = Color(0xFF3B82F6),
                    unfocusedBorderColor = Color.Gray,
                    focusedTextColor = Color.White,
                    unfocusedTextColor = Color.White
                ),
                modifier = Modifier
                    .fillMaxWidth(0.85f)
                    .padding(bottom = 12.dp),
                singleLine = true,
                trailingIcon = {
                    IconButton(onClick = {
                        val options = ScanOptions()
                        options.setDesiredBarcodeFormats(ScanOptions.QR_CODE)
                        options.setPrompt("Scan Case QR Code")
                        options.setCameraId(0)
                        options.setBeepEnabled(false)
                        options.setBarcodeImageEnabled(false)
                        qrLauncher.launch(options)
                    }) {
                        Icon(
                            imageVector = Icons.Default.QrCodeScanner,
                            contentDescription = "Scan QR Code",
                            tint = Color(0xFF3B82F6)
                        )
                    }
                }
            )

            // Search Case Button
            Button(
                onClick = {
                    if (searchQuery.isNotBlank()) {
                        coroutineScope.launch {
                            isLoading = true
                            searchResults = emptyList() // Clear previous results

                            // Simulate a 1-second network delay to your FastAPI backend
                            delay(1000)

                            // Load dummy data
                            searchResults = listOf(
                                CaseResult("CNR-2023-001", "Ramesh Kumar", "Pending Hearing"),
                                CaseResult("CNR-2023-089", "Priya Sharma", "Closed"),
                                CaseResult("CNR-2024-012", "TechCorp India Ltd.", "Awaiting Documents")
                            ).filter {
                                // Simple local filter to mimic a real search
                                it.caseNumber.contains(searchQuery, ignoreCase = true) ||
                                        it.clientName.contains(searchQuery, ignoreCase = true)
                            }

                            isLoading = false

                            if (searchResults.isEmpty()) {
                                Toast.makeText(context, "No cases found", Toast.LENGTH_SHORT).show()
                            }
                        }
                    } else {
                        Toast.makeText(context, "Please enter a search term", Toast.LENGTH_SHORT).show()
                    }
                },
                modifier = Modifier.fillMaxWidth(0.85f).padding(vertical = 4.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF3B82F6))
            ) {
                Text("Search Case")
            }

            // Existing Add Data Button
            Button(
                onClick = { context.startActivity(Intent(context, AddDataActivity::class.java)) },
                modifier = Modifier.fillMaxWidth(0.85f).padding(vertical = 4.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF3B82F6))
            ) {
                Text("Add Data")
            }

            // Existing View Data Button
            Button(
                onClick = { context.startActivity(Intent(context, ViewDataActivity::class.java)) },
                modifier = Modifier.fillMaxWidth(0.85f).padding(vertical = 4.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF3B82F6))
            ) {
                Text("View Data")
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // --- BOTTOM SECTION: Search Results ---
        if (isLoading) {
            Box(modifier = Modifier.weight(1f), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = Color(0xFF3B82F6))
            }
        } else if (searchResults.isNotEmpty()) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "Search Results",
                    color = Color.White,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier
                        .align(Alignment.Start)
                        .padding(horizontal = 32.dp, vertical = 8.dp)
                )

                LazyColumn(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 24.dp),
                    contentPadding = PaddingValues(bottom = 16.dp)
                ) {
                    items(searchResults) { case ->
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 6.dp),
                            colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1C1E))
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Text(
                                    text = "Case: ${case.caseNumber}",
                                    color = Color.White,
                                    fontWeight = FontWeight.Bold
                                )
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(text = "Client: ${case.clientName}", color = Color.LightGray)
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(text = "Status: ${case.status}", color = Color(0xFF3B82F6))
                            }
                        }
                    }
                }
            }
        }
    }
}

//search + qr - no seach results
//fun ClientScreenContent(context: android.content.Context) {
//    // NEW: State to hold the user's typed search query
//    var searchQuery by remember { mutableStateOf("") }
//
//    val qrLauncher = rememberLauncherForActivityResult(ScanContract()) { result ->
//        if (result.contents == null) {
//            Toast.makeText(context, "Cancelled", Toast.LENGTH_LONG).show()
//        } else {
//            val scanContent = result.contents
//            val cnr = if (scanContent.contains("cnr=")) {
//                scanContent.substringAfter("cnr=")
//            } else {
//                scanContent
//            }
//            Toast.makeText(context, "Scanned: $cnr", Toast.LENGTH_LONG).show()
//            val intent = Intent(context, com.nyayasahayi.ui.CaseDetailActivity::class.java).apply {
//                putExtra("CNR_NUMBER", cnr)
//                putExtra("RAW_SCAN_CONTENT", scanContent)
//            }
//            context.startActivity(intent)
//        }
//    }
//
//    Column(
//        modifier = Modifier.fillMaxSize(),
//        verticalArrangement = Arrangement.Center,
//        horizontalAlignment = Alignment.CenterHorizontally
//    ) {
//        // NEW: Combined Search Bar with QR Scanner Icon
//        OutlinedTextField(
//            value = searchQuery,
//            onValueChange = { searchQuery = it },
//            label = { Text("Enter Case No. or Client Name") },
//            modifier = Modifier
//                .fillMaxWidth(0.8f)
//                .padding(8.dp),
//            singleLine = true,
//            trailingIcon = {
//                // The QR scanner logic stays exactly the same, just moved to this icon
//                IconButton(onClick = {
//                    val options = ScanOptions()
//                    options.setDesiredBarcodeFormats(ScanOptions.QR_CODE)
//                    options.setPrompt("Scan Case QR Code")
//                    options.setCameraId(0)
//                    options.setBeepEnabled(false)
//                    options.setBarcodeImageEnabled(false)
//                    qrLauncher.launch(options)
//                }) {
//                    Icon(
//                        imageVector = Icons.Default.QrCodeScanner, // Make sure to import this icon
//                        contentDescription = "Scan QR Code",
//                        tint = Color(0xFF3B82F6)
//                    )
//                }
//            }
//        )
//
//        // UPDATED: Search Button for manual text entry
//        Button(
//            onClick = {
//                if (searchQuery.isNotBlank()) {
//                    // TODO: Trigger MongoDB search here
//                    Toast.makeText(context, "Searching for: $searchQuery", Toast.LENGTH_SHORT).show()
//                } else {
//                    Toast.makeText(context, "Please enter a search term", Toast.LENGTH_SHORT).show()
//                }
//            },
//            modifier = Modifier
//                .fillMaxWidth(0.8f)
//                .padding(8.dp),
//            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF3B82F6))
//        ) {
//            Text("Search Case")
//        }
//
//        // Existing Add Data Button
//        Button(
//            onClick = { context.startActivity(Intent(context, AddDataActivity::class.java)) },
//            modifier = Modifier
//                .fillMaxWidth(0.8f)
//                .padding(8.dp),
//            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF3B82F6))
//        ) { Text("Add Data") }
//
//        // Existing View Data Button
//        Button(
//            onClick = { context.startActivity(Intent(context, ViewDataActivity::class.java)) },
//            modifier = Modifier
//                .fillMaxWidth(0.8f)
//                .padding(8.dp),
//            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF3B82F6))
//        ) { Text("View Data") }
//    }
//}

//prev - no search
//fun ClientScreenContent(context: android.content.Context) {
//    val qrLauncher = rememberLauncherForActivityResult(ScanContract()) { result ->
//        if (result.contents == null) {
//            Toast.makeText(context, "Cancelled", Toast.LENGTH_LONG).show()
//        } else {
//            val scanContent = result.contents
//            val cnr = if (scanContent.contains("cnr=")) {
//                scanContent.substringAfter("cnr=")
//            } else {
//                scanContent
//            }
//            Toast.makeText(context, "Scanned: $cnr", Toast.LENGTH_LONG).show()
//            val intent = Intent(context, com.nyayasahayi.ui.CaseDetailActivity::class.java).apply {
//                putExtra("CNR_NUMBER", cnr)
//                putExtra("RAW_SCAN_CONTENT", scanContent)
//            }
//            context.startActivity(intent)
//        }
//    }
//
//    Column(
//        modifier = Modifier.fillMaxSize(),
//        verticalArrangement = Arrangement.Center,
//        horizontalAlignment = Alignment.CenterHorizontally
//    ) {
//        Button(
//            onClick = {
//                val options = ScanOptions()
//                options.setDesiredBarcodeFormats(ScanOptions.QR_CODE)
//                options.setPrompt("Scan Case QR Code")
//                options.setCameraId(0)
//                options.setBeepEnabled(false)
//                options.setBarcodeImageEnabled(false)
//                qrLauncher.launch(options)
//            },
//            modifier = Modifier.fillMaxWidth(0.8f).padding(8.dp),
//            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF3B82F6))
//        ) { Text("Search Case") }
//
//        Button(
//            onClick = { context.startActivity(Intent(context, AddDataActivity::class.java)) },
//            modifier = Modifier.fillMaxWidth(0.8f).padding(8.dp),
//            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF3B82F6))
//        ) { Text("Add Data") }
//
//        Button(
//            onClick = { context.startActivity(Intent(context, ViewDataActivity::class.java)) },
//            modifier = Modifier.fillMaxWidth(0.8f).padding(8.dp),
//            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF3B82F6))
//        ) { Text("View Data") }
//    }
//}

data class ChatMessage(
    val text: String,
    val isUser: Boolean
)