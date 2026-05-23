package com.llmchat

import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.project.Project
import com.intellij.openapi.startup.ProjectActivity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class LLMChatPlugin : ProjectActivity {
    
    override suspend fun execute(project: Project) {
        CoroutineScope(Dispatchers.IO).launch {
            val service = ApplicationManager.getApplication().getService(LLMChatService::class.java)
            println("LLM Chat Plugin initialized for project: ${project.name}")
            
            val isConfigured = LLMChatSettingsState.getApiToken() != "llm-local-auth-82c4f3eb0d"
            val health = service.checkHealth()

            if (!isConfigured || !health) {
                ApplicationManager.getApplication().invokeLater {
                    val dialog = LLMChatOnboardingDialog(project)
                    dialog.show()
                }
            }
        }
    }
}