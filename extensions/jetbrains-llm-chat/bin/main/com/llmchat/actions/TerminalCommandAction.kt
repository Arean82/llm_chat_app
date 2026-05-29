package com.llmchat.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.Messages
import com.llmchat.LLMChatService

class TerminalCommandAction : AnAction() {
    override fun actionPerformed(e: AnActionEvent) {
        val project: Project = e.project ?: return

        val userPrompt = Messages.showInputDialog(
            project,
            "Describe what you want to do:",
            "LLM Chat - Terminal Command",
            Messages.getQuestionIcon()
        ) ?: return

        val service = project.getService(LLMChatService::class.java)
        val response = service.sendMessage(
            userPrompt,
            "Terminal Command",
            "Generate only the terminal command, no explanation:"
        )

        response?.let {
            service.showResponse(project, it, "Terminal Command")
        }
    }
}