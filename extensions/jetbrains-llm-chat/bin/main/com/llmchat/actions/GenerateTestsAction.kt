package com.llmchat.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.llmchat.LLMChatService

class GenerateTestsAction : AnAction() {
    override fun actionPerformed(e: AnActionEvent) {
        val editor = e.getData(CommonDataKeys.EDITOR) ?: return
        val project = e.project ?: return
        val selection = editor.selectionModel.selectedText ?: return
        
        val service = project.getService(LLMChatService::class.java)
        val response = service.sendMessage(
            selection,
            "Generate Tests",
            "Generate unit tests for this code:"
        )
        
        response?.let {
            service.showResponse(project, it, "Generated Tests")
        }
    }
    
    override fun update(e: AnActionEvent) {
        val editor = e.getData(CommonDataKeys.EDITOR)
        e.presentation.isEnabled = editor != null && editor.selectionModel.hasSelection()
    }
}