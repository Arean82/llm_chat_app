package com.llmchat

import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.PersistentStateComponent
import com.intellij.openapi.components.State
import com.intellij.openapi.components.Storage
import com.intellij.credentialStore.CredentialAttributes
import com.intellij.credentialStore.generateServiceName
import com.intellij.ide.passwordSafe.PasswordSafe

@State(
    name = "com.llmchat.LLMChatSettingsState",
    storages = [Storage("LLMChatSettings.xml")]
)
class LLMChatSettingsState : PersistentStateComponent<LLMChatSettingsState> {
    var apiUrl: String = "http://localhost:5000"
    var apiTokenPlaceholder: String = "llm-local-auth-82c4f3eb0d"

    override fun getState(): LLMChatSettingsState {
        return this
    }

    override fun loadState(state: LLMChatSettingsState) {
        com.intellij.util.xmlb.XmlSerializerUtil.copyBean(state, this)
    }

    companion object {
        val instance: LLMChatSettingsState
            get() = ApplicationManager.getApplication().getService(LLMChatSettingsState::class.java)

        private val credentialAttributes = CredentialAttributes(
            generateServiceName("LLMChat", "apiToken")
        )

        fun getApiToken(): String {
            val token = PasswordSafe.instance.getPassword(credentialAttributes)
            return if (!token.isNullOrEmpty()) token else instance.apiTokenPlaceholder
        }

        fun setApiToken(token: String?) {
            PasswordSafe.instance.setPassword(credentialAttributes, token)
            if (!token.isNullOrEmpty()) {
                instance.apiTokenPlaceholder = token
            }
        }
    }
}
