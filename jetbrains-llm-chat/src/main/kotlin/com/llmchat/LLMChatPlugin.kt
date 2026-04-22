package com.llmchat

import com.intellij.openapi.components.ServiceManager
import com.intellij.openapi.project.Project
import com.intellij.openapi.startup.ProjectActivity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class LLMChatPlugin : ProjectActivity {
    
    override suspend fun execute(project: Project) {
        CoroutineScope(Dispatchers.IO).launch {
            // Initialize plugin on project startup
            val service = project.getService(LLMChatService::class.java)
            println("LLM Chat Plugin initialized for project: ${project.name}")
            
            // Optional: Check API server health on startup
            try {
                val health = service.checkHealth()
                if (health) {
                    println("LLM Chat API server is running")
                } else {
                    println("LLM Chat API server not running. Start the API server from Tools menu.")
                }
            } catch (e: Exception) {
                println("Failed to connect to LLM Chat API server")
            }
        }
    }
}