package com.nyayasahayi.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.CalendarToday
import androidx.compose.material.icons.filled.Gavel
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

// --- Colors (Matching your App Theme) ---
val DarkBackground = Color(0xFF0D0D0D)
val SurfaceColor = Color(0xFF1E1E1E)
val PrimaryBlue = Color(0xFF3B82F6)
val TextSecondary = Color(0xFF9CA3AF)
val StatusPending = Color(0xFFF59E0B) // Amber for Pending

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CaseDetailScreen(
    caseData: CaseRoot,
    onBackClick: () -> Unit = {}
) {
    Scaffold(
        containerColor = DarkBackground,
        topBar = {
            TopAppBar(
                title = { Text("Case Details", color = Color.White, fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back", tint = Color.White)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = DarkBackground)
            )
        }
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .padding(innerPadding)
                .fillMaxSize()
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // 1. CLIENT & STATUS CARD
            item {
                ClientHeaderCard(caseData)
            }

            // 2. KEY DETAILS GRID
            item {
                Text(
                    "Case Information",
                    color = Color.White,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 18.sp,
                    modifier = Modifier.padding(vertical = 8.dp)
                )
                InfoGrid(caseData.caseDetails)
            }

            // 3. CASE HISTORY TIMELINE
            item {
                Text(
                    "Case History",
                    color = Color.White,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 18.sp,
                    modifier = Modifier.padding(top = 16.dp, bottom = 8.dp)
                )
            }

            itemsIndexed(caseData.caseHistory) { index, historyItem ->
                TimelineItem(
                    item = historyItem,
                    isLast = index == caseData.caseHistory.lastIndex
                )
            }

            // Bottom padding spacer
            item { Spacer(modifier = Modifier.height(32.dp)) }
        }
    }
}

// --- SUB-COMPONENTS ---

@Composable
fun ClientHeaderCard(data: CaseRoot) {
    Card(
        colors = CardDefaults.cardColors(containerColor = SurfaceColor),
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Row(
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth()
            ) {
                // Client Badge
                Surface(
                    color = PrimaryBlue.copy(alpha = 0.2f),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.Person, null, tint = PrimaryBlue, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = data.clientName,
                            color = PrimaryBlue,
                            fontWeight = FontWeight.Bold,
                            style = MaterialTheme.typography.labelLarge
                        )
                    }
                }

                // Status Badge
                Surface(
                    color = StatusPending.copy(alpha = 0.2f),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text(
                        text = data.caseDetails.caseStatus,
                        color = StatusPending,
                        fontWeight = FontWeight.Bold,
                        style = MaterialTheme.typography.labelSmall,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            Text("Case Number", color = TextSecondary, fontSize = 12.sp)
            Text(
                text = data.caseDetails.caseNo,
                color = Color.White,
                fontSize = 22.sp,
                fontWeight = FontWeight.Bold
            )

            Spacer(modifier = Modifier.height(8.dp))
            HorizontalDivider(color = Color.Gray.copy(alpha = 0.2f))
            Spacer(modifier = Modifier.height(8.dp))

            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.Gavel, null, tint = TextSecondary, modifier = Modifier.size(16.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = data.caseDetails.actsAndSection,
                    color = Color.White.copy(alpha = 0.9f),
                    style = MaterialTheme.typography.bodyMedium
                )
            }
        }
    }
}

@Composable
fun InfoGrid(details: CaseDetails) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            InfoCard(
                label = "Next Hearing",
                value = details.nextListDate,
                icon = Icons.Default.CalendarToday,
                highlight = true,
                modifier = Modifier.weight(1f)
            )
            InfoCard(
                label = "CNR Number",
                value = details.cnrNumber,
                icon = Icons.Default.History, // Using generic icon
                modifier = Modifier.weight(1f)
            )
        }

        InfoCard(
            label = "Court Establishment",
            value = details.establishment,
            icon = Icons.Default.LocationOn,
            modifier = Modifier.fillMaxWidth()
        )
    }
}

@Composable
fun InfoCard(
    label: String,
    value: String,
    icon: ImageVector,
    modifier: Modifier = Modifier,
    highlight: Boolean = false
) {
    Surface(
        color = SurfaceColor,
        shape = RoundedCornerShape(12.dp),
        modifier = modifier
    ) {
        Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .clip(CircleShape)
                    .background(if (highlight) PrimaryBlue.copy(alpha = 0.2f) else Color(0xFF2A2A2A)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = icon,
                    contentDescription = null,
                    tint = if (highlight) PrimaryBlue else Color.Gray
                )
            }
            Spacer(modifier = Modifier.width(12.dp))
            Column {
                Text(label, color = TextSecondary, fontSize = 11.sp)
                Text(
                    value,
                    color = Color.White,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 14.sp
                )
            }
        }
    }
}

@Composable
fun TimelineItem(item: CaseHistoryItem, isLast: Boolean) {
    IntrinsicHeightRow(modifier = Modifier.fillMaxWidth()) {
        // Left Side: Date & Line
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.width(60.dp)
        ) {
            Text(
                text = item.hearingDate.substringBefore("-"), // Just the Day
                color = Color.White,
                fontWeight = FontWeight.Bold,
                fontSize = 18.sp
            )
            Text(
                text = item.hearingDate.substringAfter("-").substringBefore("-"), // Month (approx logic)
                color = TextSecondary,
                fontSize = 12.sp
            )

            Spacer(modifier = Modifier.height(8.dp))

            // The vertical line
            if (!isLast) {
                Box(
                    modifier = Modifier
                        .width(2.dp)
                        .weight(1f)
                        .background(Color.Gray.copy(alpha = 0.3f))
                )
            }
        }

        // Right Side: Content
        Card(
            colors = CardDefaults.cardColors(containerColor = SurfaceColor),
            shape = RoundedCornerShape(topStart = 0.dp, bottomStart = 12.dp, topEnd = 12.dp, bottomEnd = 12.dp),
            modifier = Modifier
                .weight(1f)
                .padding(bottom = 24.dp)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = item.purpose,
                        color = PrimaryBlue,
                        fontWeight = FontWeight.Bold,
                        style = MaterialTheme.typography.labelMedium
                    )
                    Spacer(modifier = Modifier.weight(1f))
                    Text(
                        text = "Judge: ${item.judicialOfficer.take(10)}...", // Truncate if long
                        color = TextSecondary,
                        fontSize = 10.sp
                    )
                }

                Spacer(modifier = Modifier.height(8.dp))

                Text(
                    text = item.proceedings,
                    color = Color.White.copy(alpha = 0.8f),
                    style = MaterialTheme.typography.bodyMedium,
                    lineHeight = 20.sp
                )

                Spacer(modifier = Modifier.height(12.dp))

                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.CalendarToday, null, tint = TextSecondary, modifier = Modifier.size(12.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = "Next: ${item.nextDate}",
                        color = TextSecondary,
                        fontSize = 12.sp
                    )
                }
            }
        }
    }
}

// Wrapper to help draw the timeline line correctly
@Composable
fun IntrinsicHeightRow(modifier: Modifier = Modifier, content: @Composable RowScope.() -> Unit) {
    Row(modifier = modifier.height(IntrinsicSize.Min), content = content)
}

// --- PREVIEW ---

@Preview
@Composable
fun PreviewCaseDetail() {
    val mockData = CaseRoot(
        clientName = "Alan J Arackal",
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
                proceedings = "Complainant present accused absent represented considering the request...",
                judicialOfficer = "Smt.Samyuktha M K",
                purpose = "For cross examination.",
                nextDate = "17-01-2026"
            ),
            CaseHistoryItem(
                hearingDate = "22-10-2025",
                proceedings = "Complainant present represented Pw1 present Accused absent represented...",
                judicialOfficer = "Smt.Samyuktha M K",
                purpose = "Bound over",
                nextDate = "06-12-2025"
            ),
                    CaseHistoryItem(
                    hearingDate = "06-12-2025",
            proceedings = "Complainant present accused absent represented considering the request...",
            judicialOfficer = "Smt.Samyuktha M K",
            purpose = "For cross examination.",
            nextDate = "17-01-2026"
        ),
        CaseHistoryItem(
            hearingDate = "22-10-2025",
            proceedings = "Complainant present represented Pw1 present Accused absent represented...",
            judicialOfficer = "Smt.Samyuktha M K",
            purpose = "Bound over",
            nextDate = "06-12-2025"
        )
        )
    )

    CaseDetailScreen(caseData = mockData)
}

data class CaseRoot(
    val clientName: String, // You requested this explicitly
    val caseDetails: CaseDetails,
    val caseHistory: List<CaseHistoryItem>
)

data class CaseDetails(
    val caseType: String,
    val caseStatus: String,
    val caseNo: String,
    val cnrNumber: String,
    val nextListDate: String,
    val actsAndSection: String,
    val establishment: String,
    val filingDate: String,
    val registrationDate: String
)

data class CaseHistoryItem(
    val hearingDate: String,
    val proceedings: String,
    val judicialOfficer: String,
    val purpose: String,
    val nextDate: String
)