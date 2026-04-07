package com.nyayasahayi.ui

import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CalendarToday
import androidx.compose.material.icons.filled.Gavel
import androidx.compose.material.icons.filled.Info
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp

@Composable
fun CallOverlay(
    clientName: String,
    caseStatus: String,
    nextHearingDate: String,
    onClose: () -> Unit,
    onWindowDrag: (Offset) -> Unit
) {
    var isBannerVisible by remember { mutableStateOf(true) }

    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.wrapContentSize()
    ) {
        // Banner
        CaseInfoBanner(
            isVisible = isBannerVisible,
            clientName = clientName,
            caseStatus = caseStatus,
            nextHearingDate = nextHearingDate
        )

        Spacer(modifier = Modifier.width(8.dp))

        // Bubble
        Box(
            modifier = Modifier
                .size(64.dp)
                .clip(CircleShape)
                .background(MaterialTheme.colorScheme.primary)
                .pointerInput(Unit) {
                    detectDragGestures(
                        onDrag = { change, dragAmount ->
                            change.consume()
                            onWindowDrag(dragAmount)
                        },
                        onDragEnd = { /* Optional: Add snapping logic here */ }
                    )
                }
                .pointerInput(Unit) {
                    detectTapGestures(onTap = { isBannerVisible = !isBannerVisible })
                },
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = Icons.Default.Gavel,
                contentDescription = "Case Info",
                tint = MaterialTheme.colorScheme.onPrimary
            )
        }
    }
}

@Composable
fun CaseInfoBanner(
    isVisible: Boolean,
    clientName: String,
    caseStatus: String,
    nextHearingDate: String
) {
    AnimatedVisibility(
        visible = isVisible,
        enter = expandHorizontally(expandFrom = Alignment.CenterHorizontally) + fadeIn(),
        exit = shrinkHorizontally(shrinkTowards = Alignment.CenterHorizontally) + fadeOut()
    ) {
        Card(
            shape = RoundedCornerShape(16.dp),
            elevation = CardDefaults.cardElevation(defaultElevation = 8.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
        ) {
            Column(
                modifier = Modifier
                    .padding(16.dp)
                    .width(IntrinsicSize.Max)
            ) {
                InfoRow(icon = Icons.Default.Gavel, label = "CLIENT", value = clientName)
                Spacer(modifier = Modifier.height(8.dp))
                InfoRow(icon = Icons.Default.Info, label = "STATUS", value = caseStatus)
                Spacer(modifier = Modifier.height(8.dp))
                InfoRow(icon = Icons.Default.CalendarToday, label = "NEXT DATE", value = nextHearingDate)
            }
        }
    }
}

@Composable
fun InfoRow(icon: ImageVector, label: String, value: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Icon(
            imageVector = icon,
            contentDescription = label,
            tint = MaterialTheme.colorScheme.primary,
            modifier = Modifier.size(20.dp)
        )
        Spacer(modifier = Modifier.width(8.dp))
        Column {
            Text(text = label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(text = value, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurface)
        }
    }
}
