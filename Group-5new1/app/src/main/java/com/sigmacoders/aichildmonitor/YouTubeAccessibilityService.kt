package com.sigmacoders.aichildmonitor

import android.accessibilityservice.AccessibilityService
import android.content.Context
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import com.sigmacoders.aichildmonitor.YouTubeClassifierTrigger

class YouTubeAccessibilityService : AccessibilityService() {

    private val TAG = "YT_MONITOR"
    private var lastDetectedTitle: CharSequence? = null

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event?.eventType != AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED) return
        if (event.packageName != "com.google.android.youtube") return

        val rootNode = rootInActiveWindow ?: return
        val watchPanelNodes = rootNode.findAccessibilityNodeInfosByViewId("com.google.android.youtube:id/watch_panel")

        var title: CharSequence? = null
        var videoId: String? = null

        if (watchPanelNodes.isNotEmpty()) {
            title = findFirstTextInNode(watchPanelNodes[0])
            videoId = extractVideoId(rootNode.text?.toString() ?: "")
        }

        watchPanelNodes.forEach { it.recycle() }
        rootNode.recycle()

        if (!title.isNullOrBlank() && title != lastDetectedTitle && !isTimestamp(title.toString()) && isValidVideoTitle(title.toString())) {
            lastDetectedTitle = title
            Log.d(TAG, "VIDEO TITLE DETECTED: $title")

            // Load real pairing data from storage
            val prefs = getSharedPreferences("AI_CHILD_MONITOR_PREFS", Context.MODE_PRIVATE)
            val parentId = prefs.getString("PARENT_ID", null)
            val childId = prefs.getString("CHILD_ID", null)
            if (parentId != null && childId != null) {
                YouTubeClassifierTrigger.classifyIfNeeded(
                    context = this,
                    title = title.toString(),
                    videoId = videoId,
                    parentId = parentId,
                    childId = childId
                )
            } else {
                Log.e(TAG, "Cannot classify: IDs not found. Ensure device is paired.")
            }
        }
    }

    private fun findFirstTextInNode(nodeInfo: AccessibilityNodeInfo): CharSequence? {
        if (!nodeInfo.text.isNullOrBlank()) return nodeInfo.text
        for (i in 0 until nodeInfo.childCount) {
            val child = nodeInfo.getChild(i)
            if (child != null) {
                val textFromChild = findFirstTextInNode(child)
                if (textFromChild != null) return textFromChild
            }
        }
        return null
    }

    private fun isTimestamp(text: String): Boolean {
        return text.matches(Regex("^\\d{1,2}:\\d{2}.*"))
    }

    private fun extractVideoId(text: String): String? {
        val regex = Regex("v=([a-zA-Z0-9_-]{11})")
        return regex.find(text)?.groupValues?.get(1)
    }

    override fun onInterrupt() {
        Log.w(TAG, "Service interrupted")
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        Log.i(TAG, "YouTube Accessibility Service Connected")
    }

    private fun isValidVideoTitle(text: String): Boolean {
        val trimmed = text.trim().lowercase()
        if (trimmed.length < 8) return false
        val blockedWords = listOf("live", "comments", "shorts", "home", "library", "subscriptions", "trending", "search", "share", "like", "dislike")
        if (blockedWords.contains(trimmed)) return false
        if (!trimmed.contains(" ")) return false
        return true
    }
}
