package com.nyayasahayi.ui

import android.os.Build
import androidx.annotation.RequiresApi
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccessTime
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.ArrowForward
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.time.LocalDate
import java.time.LocalTime
import java.time.format.DateTimeFormatter
import java.time.format.TextStyle
import java.util.Locale


// Data class for a schedule item
data class CaseScheduleItem(
    val id: String,
    val caseNumber: String,
    val clientName: String,
    val courtName: String,
    val purpose: String, // e.g., "Hearing", "Filing", "Evidence"
    val time: LocalTime,
    val date: LocalDate,
    val status: String // "Pending", "Done"
)
// --- Colors (Reusing your theme) ---
private val DarkBg = Color(0xFF0D0D0D)
private val CardSurface = Color(0xFF1E1E1E)
//private val PrimaryBlue = Color(0xFF3B82F6)
private val TextGray = Color(0xFF9CA3AF)

@RequiresApi(Build.VERSION_CODES.O)
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CalendarScreen() {
    // 1. STATE
    var selectedDate by remember { mutableStateOf(LocalDate.now()) }

    // Mock Data Generator (In real app, fetch from Room DB or API)
    val schedule = remember { generateMockSchedule() }

    // Filter cases for the selected date
    val todaysCases = schedule.filter { it.date == selectedDate }.sortedBy { it.time }

    Scaffold(
        containerColor = DarkBg,
        topBar = {
            Column(modifier = Modifier.background(DarkBg)) {
                CenterAlignedTopAppBar(
                    title = {
                        Text(
                            "Schedule",
                            color = Color.White,
                            fontWeight = FontWeight.Bold
                        )
                    },
                    colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                        containerColor = DarkBg
                    ),
                    actions = {
                        // jump to today button
                        IconButton(onClick = { selectedDate = LocalDate.now() }) {
                            Icon(Icons.Default.DateRange, "Today", tint = PrimaryBlue)
                        }
                    }
                )
                // 2. DATE STRIP COMPONENT
                DateSelectorStrip(
                    selectedDate = selectedDate,
                    onDateSelected = { newDate -> selectedDate = newDate }
                )
                Spacer(modifier = Modifier.height(16.dp))
            }
        }
    ) { innerPadding ->
        // 3. CASE LIST
        Box(
            modifier = Modifier
                .padding(innerPadding)
                .fillMaxSize()
                .background(DarkBg)
        ) {
            if (todaysCases.isEmpty()) {
                EmptyStateMessage(selectedDate)
            } else {
                LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    // Header for the list
                    item {
                        Text(
                            text = "Tasks & Hearings (${todaysCases.size})",
                            color = TextGray,
                            fontSize = 14.sp,
                            modifier = Modifier.padding(bottom = 8.dp)
                        )
                    }

                    items(todaysCases) { item ->
                        CaseScheduleCard(item)
                    }
                }
            }
        }
    }
}

// --- COMPONENT: Horizontal Date Strip ---
@RequiresApi(Build.VERSION_CODES.O)
@Composable
fun DateSelectorStrip(
    selectedDate: LocalDate,
    onDateSelected: (LocalDate) -> Unit
) {
    // Generate 2 weeks of dates around today
    // We start 3 days back and go 14 days forward
    val dates = remember {
        val today = LocalDate.now()
        (-3..14).map { today.plusDays(it.toLong()) }
    }

    val listState = rememberLazyListState(initialFirstVisibleItemIndex = 1) // Start near today

    LazyRow(
        state = listState,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        contentPadding = PaddingValues(horizontal = 16.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        items(dates) { date ->
            val isSelected = date == selectedDate
            val isToday = date == LocalDate.now()

            DateChip(
                date = date,
                isSelected = isSelected,
                isToday = isToday,
                onClick = { onDateSelected(date) }
            )
        }
    }
}

@RequiresApi(Build.VERSION_CODES.O)
@Composable
fun DateChip(
    date: LocalDate,
    isSelected: Boolean,
    isToday: Boolean,
    onClick: () -> Unit
) {
    // Colors based on state
    val containerColor = if (isSelected) PrimaryBlue else CardSurface
    val contentColor = if (isSelected) Color.White else TextGray

    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier
            .width(60.dp)
            .clip(RoundedCornerShape(12.dp))
            .background(containerColor)
            .clickable { onClick() }
            .padding(vertical = 12.dp)
    ) {
        // Day of Week (e.g., "Mon")
        Text(
            text = date.dayOfWeek.getDisplayName(TextStyle.SHORT, Locale.getDefault()).uppercase(),
            color = contentColor.copy(alpha = 0.7f),
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold
        )
        Spacer(modifier = Modifier.height(4.dp))
        // Day of Month (e.g., "12")
        Text(
            text = date.dayOfMonth.toString(),
            color = if (isSelected) Color.White else Color.White,
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold
        )

        // Dot indicator for "Today"
        if (isToday && !isSelected) {
            Spacer(modifier = Modifier.height(4.dp))
            Box(
                modifier = Modifier
                    .size(4.dp)
                    .clip(CircleShape)
                    .background(PrimaryBlue)
            )
        }
    }
}

// --- COMPONENT: Case Schedule Card ---
@RequiresApi(Build.VERSION_CODES.O)
@Composable
fun CaseScheduleCard(item: CaseScheduleItem) {
    Row(modifier = Modifier.fillMaxWidth()) {
        // Time Column
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier
                .padding(end = 12.dp)
                .padding(top = 12.dp)
                .width(50.dp)
        ) {
            Text(
                text = item.time.format(DateTimeFormatter.ofPattern("HH:mm")),
                color = Color.White,
                fontWeight = FontWeight.Bold,
                fontSize = 14.sp
            )
            // Vertical timeline line
            Box(
                modifier = Modifier
                    .padding(top = 8.dp)
                    .width(1.dp)
                    .height(40.dp)
                    .background(TextGray.copy(alpha = 0.3f))
            )
        }

        // Details Card
        Card(
            colors = CardDefaults.cardColors(containerColor = CardSurface),
            shape = RoundedCornerShape(16.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                // Header: Purpose & Status
                Row(
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Surface(
                        color = PrimaryBlue.copy(alpha = 0.1f),
                        shape = RoundedCornerShape(6.dp)
                    ) {
                        Text(
                            text = item.purpose.uppercase(),
                            color = PrimaryBlue,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                        )
                    }

                    // Simple dot for status
                    Icon(
                        imageVector = Icons.Default.AccessTime,
                        contentDescription = null,
                        tint = TextGray,
                        modifier = Modifier.size(14.dp)
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                // Client & Case Info
                Text(
                    text = item.clientName,
                    color = Color.White,
                    fontWeight = FontWeight.Bold,
                    fontSize = 16.sp
                )
                Text(
                    text = "Case No: ${item.caseNumber}",
                    color = TextGray,
                    fontSize = 12.sp
                )

                Spacer(modifier = Modifier.height(12.dp))

                // Location
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.LocationOn,
                        contentDescription = null,
                        tint = TextGray,
                        modifier = Modifier.size(14.dp)
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = item.courtName,
                        color = TextGray,
                        fontSize = 12.sp,
                        maxLines = 1
                    )
                }
            }
        }
    }
}

// --- COMPONENT: Empty State ---
@RequiresApi(Build.VERSION_CODES.O)
@Composable
fun EmptyStateMessage(date: LocalDate) {
    Column(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(
            imageVector = Icons.Default.DateRange,
            contentDescription = null,
            tint = TextGray.copy(alpha = 0.3f),
            modifier = Modifier.size(64.dp)
        )
        Spacer(modifier = Modifier.height(16.dp))
        Text(
            text = "No cases scheduled",
            color = Color.White,
            fontWeight = FontWeight.Bold,
            fontSize = 18.sp
        )
        Text(
            text = "for ${date.format(DateTimeFormatter.ofPattern("MMMM dd, yyyy"))}",
            color = TextGray,
            fontSize = 14.sp
        )
    }
}

// --- MOCK DATA ---
@RequiresApi(Build.VERSION_CODES.O)
fun generateMockSchedule(): List<CaseScheduleItem> {
    val today = LocalDate.now()

    return listOf(
        // Today's Cases
        CaseScheduleItem("1", "KL/2023/889", "Alan Arackal", "High Court of Kerala", "Hearing", LocalTime.of(10, 30), today, "Pending"),
        CaseScheduleItem("2", "DL/2024/112", "Sarah John", "Magistrate Court I", "Cross Exam", LocalTime.of(14, 0), today, "Pending"),
        CaseScheduleItem("3", "KL/2023/554", "Mohammed R.", "Family Court Ernakulam", "Filing", LocalTime.of(16, 15), today, "Pending"),

        // Tomorrow's Cases
        CaseScheduleItem("4", "TX/2022/001", "Tech Corp Ltd", "Civil Court", "Judgment", LocalTime.of(11, 0), today.plusDays(1), "Pending"),

        // Yesterday
        CaseScheduleItem("5", "CR/2025/110", "State vs. Doe", "District Court", "Bail Hearing", LocalTime.of(10, 0), today.minusDays(1), "Done"),
    )
}

@RequiresApi(Build.VERSION_CODES.O)
@Preview
@Composable
fun PreviewCalendar() {
    CalendarScreen()
}