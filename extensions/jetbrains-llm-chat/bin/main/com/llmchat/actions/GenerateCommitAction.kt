package com.llmchat.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.project.Project
import com.intellij.openapi.vcs.ProjectLevelVcsManager
import com.intellij.openapi.vcs.changes.ChangeListManager
import com.llmchat.LLMChatService

class GenerateCommitAction : AnAction() {
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        
        val vcsManager = ProjectLevelVcsManager.getInstance(project)
        val changeListManager = ChangeListManager.getInstance(project)
        val changes = changeListManager.defaultChangeList.changes
        
        if (changes.isEmpty()) {
            com.intellij.openapi.ui.Messages.showWarningDialog(
                project,
                "No changes to commit",
                "LLM Chat"
            )
            return
        }
        
        val changesText = changes.joinToString("\n") { 
            "- ${it.virtualFile?.path ?: "unknown"}" 
        }
        
        val service = project.getService(LLMChatService::class.java)
        val response = service.sendMessage(
            changesText,
            "Generate Commit",
            "Generate a concise git commit message for these changes:"
        )
        
        response?.let {
            service.showResponse(project, it, "Commit Message")
        }
    }
}