package com.sigmacoders.aichildmonitor.ai

import okhttp3.*
import org.json.JSONObject
import java.io.IOException

class YouTubeSearchFetcher {

    private val client = OkHttpClient()

    fun searchVideoIdByTitle(
        title: String,
        apiKey: String,
        onSuccess: (String?) -> Unit,
        onFailure: () -> Unit
    ) {

        val encodedTitle = java.net.URLEncoder.encode(title, "UTF-8")

        val url =
            "https://www.googleapis.com/youtube/v3/search" +
                    "?part=snippet" +
                    "&q=$encodedTitle" +
                    "&type=video" +
                    "&maxResults=1" +
                    "&key=$apiKey"

        val request = Request.Builder()
            .url(url)
            .get()
            .build()

        client.newCall(request).enqueue(object : Callback {

            override fun onFailure(call: Call, e: IOException) {
                onFailure()
            }

            override fun onResponse(call: Call, response: Response) {
                try {
                    val body = response.body?.string() ?: ""
                    val json = JSONObject(body)

                    val items = json.getJSONArray("items")

                    if (items.length() == 0) {
                        onSuccess(null)
                        return
                    }

                    val videoId = items
                        .getJSONObject(0)
                        .getJSONObject("id")
                        .getString("videoId")

                    onSuccess(videoId)

                } catch (e: Exception) {
                    onFailure()
                }
            }
        })
    }
}
