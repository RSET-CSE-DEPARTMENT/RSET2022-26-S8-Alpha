package com.nyayasahayi.data

import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Body
import retrofit2.http.Query

interface ApiService {
    @GET("cases/details")
    suspend fun getCaseDetails(@Query("cnr") cnr: String): LocalCase
    
    // Stub for sync
    @GET("sync")
    suspend fun syncData(@Query("since") timestamp: String): List<LocalCase>

    @POST("case/create")
    suspend fun createCase(@Body request: CreateCaseRequest): retrofit2.Response<Unit>
}

data class CreateCaseRequest(
    val cnrNumber: String,
    val status: String?,
    val nextDate: String?,
    val historyJson: String,
    val fcmToken: String
)
