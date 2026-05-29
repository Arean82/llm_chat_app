package com.llmchat.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.llmchat.LLMChatService

class GenerateDocstringAction : AnAction() {
    override fun actionPerformed(e: AnActionEvent) {
        val editor = e.getData(CommonDataKeys.EDITOR) ?: return
        val project = e.project ?: return
        val selection = editor.selectionModel.selectedText ?: return
        
        // Check if it's a function
        if (!selection.contains("def ") && !selection.contains("fun ")) {
            com.intellij.openapi.ui.Messages.showWarningDialog(
                project,
                "Select a function to generate docstring",
                "LLM Chat"
            )
            return
        }
        
        val service = project.getService(LLMChatService::class.java)
        val response = service.sendMessage(
            selection,
            "Generate Docstring",
            "Generate a docstring for this function:"
        )
        
        response?.let {
            service.showResponse(project, it, "Generated Docstring")
        }
    }
    
    override fun update(e: AnActionEvent) {
        val editor = e.getData(CommonDataKeys.EDITOR)
        e.presentation.isEnabled = editor != null && editor.selectionModel.hasSelection()
    }
}