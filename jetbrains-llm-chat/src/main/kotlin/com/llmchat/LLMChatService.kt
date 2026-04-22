package com.llmchat

import com.intellij.openapi.components.Service
import com.intellij.openapi.diagnostic.Logger
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.Messages
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import com.google.gson.Gson
import com.google.gson.JsonObject

@Service
class LLMChatService {
    private val logger = Logger.getInstance(LLMChatService::class.java)
    private val client = HttpClient.newHttpClient()
    private val gson = Gson()
    private val apiUrl = "http://localhost:5000/v1/chat/completions"
    
    fun sendMessage(content: String, title: String, systemPrompt: String? = null): String? {
        return try {
            val messages = mutableListOf<Map<String, String>>()
            systemPrompt?.let {
                messages.add(mapOf("role" to "system", "content" to it))
            }
            messages.add(mapOf("role" to "user", "content" to "$title:\n\n$content"))
            
            val requestBody = mapOf(
                "messages" to messages,
                "temperature" to 0.5,
                "max_tokens" to 2000
            )
            
            val request = HttpRequest.newBuilder()
                .uri(URI.create(apiUrl))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(gson.toJson(requestBody)))
                .build()
            
            val response = client.send(request, HttpResponse.BodyHandlers.ofString())
            
            if (response.statusCode() == 200) {
                val json = gson.fromJson(response.body(), JsonObject::class.java)
                json.getAsJsonArray("choices")
                    .get(0)
                    .asJsonObject
                    .getAsJsonObject("message")
                    .get("content")
                    .asString
            } else {
                logger.warn("API error: ${response.statusCode()}")
                null
            }
        } catch (e: Exception) {
            logger.error("API call failed", e)
            null
        }
    }
    
    fun showResponse(project: Project, response: String, title: String) {
        Messages.showMessageDialog(
            project,
            response,
            "LLM Chat: $title",
            Messages.getInformationIcon()
        )
    }
    fun checkHealth(): Boolean {
        return try {
            val request = HttpRequest.newBuilder()
                .uri(URI.create("http://localhost:5000/health"))
                .GET()
                .build()
            
            val response = client.send(request, HttpResponse.BodyHandlers.ofString())
            response.statusCode() == 200
        } catch (e: Exception) {
            false
        }
    }
}