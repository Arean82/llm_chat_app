package com.llmchat.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.llmchat.LLMChatService

class ExplainCodeAction : AnAction() {
    override fun actionPerformed(e: AnActionEvent) {
        val editor = e.getData(CommonDataKeys.EDITOR) ?: return
        val project = e.project ?: return
        val selection = editor.selectionModel.selectedText ?: return
        
        val service = project.getService(LLMChatService::class.java)
        val response = service.sendMessage(
            selection, 
            "Explain Code",
            "Explain this code in simple terms:"
        )
        
        response?.let {
            service.showResponse(project, it, "Code Explanation")
        }
    }
    
    override fun update(e: AnActionEvent) {
        val editor = e.getData(CommonDataKeys.EDITOR)
        e.presentation.isEnabled = editor != null && editor.selectionModel.hasSelection()
    }
}