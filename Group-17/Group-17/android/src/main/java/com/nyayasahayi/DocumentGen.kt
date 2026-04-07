package com.nyayasahayi.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.FormatAlignLeft
import androidx.compose.material.icons.automirrored.filled.Redo
import androidx.compose.material.icons.automirrored.filled.Undo
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.TextFieldValue
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private val DocBg       = Color(0xFFF8F9FA)
private val DocSurface  = Color(0xFFFFFFFF)
private val TopBarBg    = Color(0xFF1E1E2E)
private val ToolbarBg   = Color(0xFF2A2A3E)
private val ActiveTool  = Color(0xFF3B82F6)
private val IconTint    = Color(0xFFCDD6F4)
private val SubtleGray  = Color(0xFFB0B8D1)
private val PageShadow  = Color(0x26000000)
private val StatusGreen = Color(0xFF4ADE80)

@Composable
fun DocumentEditorScreen(
    documentTitle: String = "Untitled Legal Document",
    onBack: () -> Unit = {}
) {
    var title         by remember { mutableStateOf(documentTitle) }
    var bodyText      by remember { mutableStateOf(TextFieldValue(SAMPLE_LEGAL_TEXT)) }
    var isBold        by remember { mutableStateOf(false) }
    var isItalic      by remember { mutableStateOf(false) }
    var isUnderline   by remember { mutableStateOf(false) }
    var fontSize      by remember { mutableStateOf(14) }
    var isSaved       by remember { mutableStateOf(true) }
    var showSaveSnack by remember { mutableStateOf(false) }
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(showSaveSnack) {
        if (showSaveSnack) {
            snackbarHostState.showSnackbar("Document saved successfully")
            showSaveSnack = false
        }
    }

    Scaffold(
        snackbarHost   = { SnackbarHost(snackbarHostState) },
        containerColor = DocBg,
        topBar         = {
            DocTopBar(
                title         = title,
                onTitleChange = { title = it; isSaved = false },
                isSaved       = isSaved,
                onBack        = onBack,
                onSave        = { isSaved = true; showSaveSnack = true }
            )
        }
    ) { paddingValues ->
        Column(modifier = Modifier.fillMaxSize().padding(paddingValues)) {
            FormattingToolbar(
                isBold      = isBold,
                isItalic    = isItalic,
                isUnderline = isUnderline,
                fontSize    = fontSize,
                onBold      = { isBold = !isBold },
                onItalic    = { isItalic = !isItalic },
                onUnderline = { isUnderline = !isUnderline },
                onFontInc   = { if (fontSize < 32) fontSize++ },
                onFontDec   = { if (fontSize > 8) fontSize-- }
            )
            Box(
                modifier         = Modifier.fillMaxSize().background(DocBg).verticalScroll(rememberScrollState()),
                contentAlignment = Alignment.TopCenter
            ) {
                Box(
                    modifier = Modifier
                        .padding(vertical = 24.dp, horizontal = 12.dp)
                        .fillMaxWidth()
                        .shadow(6.dp, RoundedCornerShape(4.dp), ambientColor = PageShadow)
                        .background(DocSurface, RoundedCornerShape(4.dp))
                        .padding(horizontal = 32.dp, vertical = 40.dp)
                ) {
                    val bodyStyle = TextStyle(
                        fontSize       = fontSize.sp,
                        fontWeight     = if (isBold) FontWeight.Bold else FontWeight.Normal,
                        fontStyle      = if (isItalic) FontStyle.Italic else FontStyle.Normal,
                        textDecoration = if (isUnderline) TextDecoration.Underline else TextDecoration.None,
                        color          = Color(0xFF1A1A2E),
                        lineHeight     = (fontSize * 1.75).sp
                    )
                    BasicTextField(
                        value         = bodyText,
                        onValueChange = { bodyText = it; isSaved = false },
                        textStyle     = bodyStyle,
                        cursorBrush   = SolidColor(ActiveTool),
                        modifier      = Modifier.fillMaxWidth(),
                        decorationBox = { innerTextField ->
                            if (bodyText.text.isEmpty()) {
                                Text("Start typing your legal document...",
                                    style = bodyStyle.copy(color = Color(0xFFAAAAAA)))
                            }
                            innerTextField()
                        }
                    )
                }
            }
        }
    }
}

@Composable
private fun DocTopBar(
    title: String, onTitleChange: (String) -> Unit,
    isSaved: Boolean, onBack: () -> Unit, onSave: () -> Unit
) {
    Surface(color = TopBarBg, shadowElevation = 4.dp) {
        Row(
            modifier = Modifier.fillMaxWidth().statusBarsPadding().height(56.dp).padding(horizontal = 8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onBack) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back", tint = IconTint)
            }
            Box(
                modifier = Modifier.size(32.dp).clip(RoundedCornerShape(6.dp)).background(ActiveTool),
                contentAlignment = Alignment.Center
            ) {
                Icon(Icons.Default.Description, null, tint = Color.White, modifier = Modifier.size(18.dp))
            }
            Spacer(Modifier.width(10.dp))
            Column(modifier = Modifier.weight(1f)) {
                BasicTextField(
                    value = title, onValueChange = onTitleChange,
                    textStyle = TextStyle(color = Color.White, fontSize = 15.sp, fontWeight = FontWeight.SemiBold),
                    cursorBrush = SolidColor(ActiveTool), singleLine = true
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(modifier = Modifier.size(6.dp).clip(CircleShape)
                        .background(if (isSaved) StatusGreen else Color(0xFFFBBF24)))
                    Spacer(Modifier.width(4.dp))
                    Text(if (isSaved) "Saved" else "Unsaved changes", color = SubtleGray, fontSize = 10.sp)
                }
            }
            IconButton(onClick = {}) {
                Icon(Icons.Default.Share, "Share", tint = IconTint)
            }
            Button(
                onClick = onSave,
                colors = ButtonDefaults.buttonColors(containerColor = ActiveTool),
                contentPadding = PaddingValues(horizontal = 14.dp, vertical = 0.dp),
                modifier = Modifier.height(34.dp)
            ) {
                Icon(Icons.Default.Save, null, modifier = Modifier.size(16.dp))
                Spacer(Modifier.width(4.dp))
                Text("Save", fontSize = 12.sp)
            }
            Spacer(Modifier.width(4.dp))
            IconButton(onClick = {}) {
                Icon(Icons.Default.MoreVert, "More", tint = IconTint)
            }
        }
    }
}

@Composable
private fun FormattingToolbar(
    isBold: Boolean, isItalic: Boolean, isUnderline: Boolean, fontSize: Int,
    onBold: () -> Unit, onItalic: () -> Unit, onUnderline: () -> Unit,
    onFontInc: () -> Unit, onFontDec: () -> Unit
) {
    Surface(color = ToolbarBg, shadowElevation = 2.dp) {
        Row(
            modifier = Modifier.fillMaxWidth().height(48.dp)
                .horizontalScroll(rememberScrollState()).padding(horizontal = 8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            ToolbarIconBtn(Icons.AutoMirrored.Filled.Undo, "Undo",  false, {})
            ToolbarIconBtn(Icons.AutoMirrored.Filled.Redo, "Redo",  false, {})
            ToolbarDivider()
            IconButton(onClick = onFontDec, modifier = Modifier.size(32.dp)) {
                Icon(Icons.Default.Remove, "Dec font", tint = IconTint, modifier = Modifier.size(14.dp))
            }
            Text("$fontSize", color = Color.White, fontSize = 13.sp,
                fontWeight = FontWeight.Medium, modifier = Modifier.widthIn(min = 22.dp),
                textAlign = TextAlign.Center)
            IconButton(onClick = onFontInc, modifier = Modifier.size(32.dp)) {
                Icon(Icons.Default.Add, "Inc font", tint = IconTint, modifier = Modifier.size(14.dp))
            }
            ToolbarDivider()
            ToolbarIconBtn(Icons.Default.FormatBold,       "Bold",      isBold,      onBold)
            ToolbarIconBtn(Icons.Default.FormatItalic,     "Italic",    isItalic,    onItalic)
            ToolbarIconBtn(Icons.Default.FormatUnderlined, "Underline", isUnderline, onUnderline)
            ToolbarDivider()
            ToolbarIconBtn(Icons.AutoMirrored.Filled.FormatAlignLeft, "Left",    true,  {})
            ToolbarIconBtn(Icons.Default.FormatAlignCenter,            "Center",  false, {})
            ToolbarIconBtn(Icons.Default.FormatAlignRight,             "Right",   false, {})
            ToolbarIconBtn(Icons.Default.FormatAlignJustify,           "Justify", false, {})
            ToolbarDivider()
            ToolbarIconBtn(Icons.Default.FormatListBulleted, "Bullets",  false, {})
            ToolbarIconBtn(Icons.Default.FormatListNumbered, "Numbered", false, {})
            ToolbarDivider()
            ToolbarIconBtn(Icons.Default.Image, "Image", false, {})
            ToolbarIconBtn(Icons.Default.Link,  "Link",  false, {})
        }
    }
}

@Composable
private fun ToolbarIconBtn(icon: ImageVector, label: String, active: Boolean, onClick: () -> Unit) {
    Box(
        modifier = Modifier.size(36.dp).clip(RoundedCornerShape(6.dp))
            .background(if (active) ActiveTool.copy(alpha = 0.25f) else Color.Transparent)
            .border(if (active) 1.dp else 0.dp, if (active) ActiveTool else Color.Transparent, RoundedCornerShape(6.dp))
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center
    ) {
        Icon(icon, label, tint = if (active) ActiveTool else IconTint, modifier = Modifier.size(18.dp))
    }
    Spacer(Modifier.width(2.dp))
}

@Composable
private fun ToolbarDivider() {
    Box(modifier = Modifier.padding(horizontal = 6.dp).width(1.dp).height(24.dp).background(Color(0xFF3A3A5A)))
}

private val SAMPLE_LEGAL_TEXT = """LEGAL NOTICE

To: [Recipient Name]
Date: [Insert Date]

Subject: Notice Regarding [Legal Matter]

Dear Sir/Madam,

This notice is issued under the provisions of [Applicable Law / Section], informing you that [Party Name] has initiated proceedings with respect to the matter described herein.

1. Background
   The facts giving rise to this notice are as follows: [Describe facts clearly and concisely.]

2. Legal Basis
   The above facts constitute a violation of [Statute / Agreement / Order], thereby entitling our client to seek appropriate legal relief.

3. Relief Sought
   We hereby demand that you [Specific demand] within [X] days from the date of receipt of this notice.

Failure to comply may result in legal proceedings being initiated before the competent court/authority, at your sole risk and expense.

Yours faithfully,

[Advocate Name]
Bar Council No.: [XXXX]
[Law Firm / Chamber Name]
[Address | Phone | Email]"""