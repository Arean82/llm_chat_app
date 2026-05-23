package com.llmchat

import com.intellij.openapi.components.Service
import com.intellij.openapi.diagnostic.Logger
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.Messages
import com.intellij.openapi.application.ApplicationManager
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
    
    fun sendMessage(content: String, title: String, systemPrompt: String? = null): String? {
        val settings = LLMChatSettingsState.instance
        val apiToken = LLMChatSettingsState.getApiToken()
        val isConfigured = apiToken != "llm-local-auth-82c4f3eb0d"

        if (!isConfigured) {
            var dialogResult = false
            ApplicationManager.getApplication().invokeAndWait {
                val dialog = LLMChatOnboardingDialog(null)
                dialogResult = dialog.showAndGet()
            }
            if (!dialogResult) {
                return null
            }
        }

        val baseUrl = settings.apiUrl.trimEnd('/')
        val completionsUrl = "$baseUrl/v1/chat/completions"
        val activeToken = LLMChatSettingsState.getApiToken()

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
                .uri(URI.create(completionsUrl))
                .header("Content-Type", "application/json")
                .header("Authorization", "Bearer $activeToken")
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
        val settings = LLMChatSettingsState.instance
        val baseUrl = settings.apiUrl.trimEnd('/')
        return try {
            val request = HttpRequest.newBuilder()
                .uri(URI.create("$baseUrl/health"))
                .GET()
                .build()
            
            val response = client.send(request, HttpResponse.BodyHandlers.ofString())
            response.statusCode() == 200
        } catch (e: Exception) {
            false
        }
    }
}