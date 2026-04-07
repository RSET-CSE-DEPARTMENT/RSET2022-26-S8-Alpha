package com.sigmacoders.aichildmonitor.model

import com.google.firebase.firestore.Exclude

data class Child(
    @get:Exclude var id: String = "", 
    var name: String = "",
    var gender: String = "", // Added field
    var age: Int = 0,        // Added field
    var isPaired: Boolean = false,
    var parentId: String = "",
    var riskLevel: String = "Low", // Added for consistency
    var journalText: String = "No entry yet." // Added for consistency
)
