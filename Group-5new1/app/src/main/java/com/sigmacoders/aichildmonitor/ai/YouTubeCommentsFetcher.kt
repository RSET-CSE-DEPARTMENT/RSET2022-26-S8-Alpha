package com.sigmacoders.aichildmonitor.ai

import okhttp3.*
import org.json.JSONObject
import java.io.IOException

class YouTubeCommentsFetcher {

    private val client = OkHttpClient()

    fun fetchTopComments(
        videoId: String,
        apiKey: String,
        onSuccess: (List<String>) -> Unit,
        onFailure: () -> Unit
    ) {
        val url =
            "https://www.googleapis.com/youtube/v3/commentThreads" +
                    "?part=snippet" +
                    "&videoId=$videoId" +
                    "&maxResults=10" +
                    "&order=relevance" +
                    "&textFormat=plainText" +
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

                    val comments = mutableListOf<String>()

                    for (i in 0 until items.length()) {
                        val comment = items
                            .getJSONObject(i)
                            .getJSONObject("snippet")
                            .getJSONObject("topLevelComment")
                            .getJSONObject("snippet")
                            .getString("textDisplay")

                        if (comment.length > 15) {
                            comments.add(comment)
                        }
                    }

                    onSuccess(comments)

                } catch (e: Exception) {
                    onFailure()
                }
            }
        })
    }
}
