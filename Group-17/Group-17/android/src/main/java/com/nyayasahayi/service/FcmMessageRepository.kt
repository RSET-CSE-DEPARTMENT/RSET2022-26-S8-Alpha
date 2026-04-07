package com.nyayasahayi.service

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

// A singleton to hold our real-time incoming messages
object FcmMessageRepository {
    private val _messages = MutableStateFlow<List<String>>(emptyList())
    val messages: StateFlow<List<String>> = _messages.asStateFlow()

    fun addMessage(message: String) {
        // Add new message to the top of the list
        _messages.value = listOf(message) + _messages.value
    }
}