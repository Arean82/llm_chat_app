package com.llmchat

import com.intellij.openapi.options.Configurable
import com.intellij.openapi.ui.Messages
import java.awt.GridBagConstraints
import java.awt.GridBagLayout
import java.awt.Insets
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import javax.swing.*

class LLMChatConfigurable : Configurable {
    private var mySettingsComponent: JPanel? = null
    private val apiUrlField = JTextField()
    private val apiTokenField = JPasswordField()

    override fun getDisplayName(): String {
        return "Synora Studio"
    }

    override fun createComponent(): JComponent? {
        val panel = JPanel(GridBagLayout())
        val c = GridBagConstraints()
        c.fill = GridBagConstraints.HORIZONTAL
        c.insets = Insets(5, 5, 5, 5)

        // Title Label
        val titleLabel = JLabel("Synora Studio Settings Configuration")
        titleLabel.font = titleLabel.font.deriveFont(java.awt.Font.BOLD, 14f)
        c.gridx = 0
        c.gridy = 0
        c.gridwidth = 2
        panel.add(titleLabel, c)

        // Description Label
        val descLabel = JLabel("<html>Set up your LLM Chat server connectivity. Supports both local desktop and dynamic cloud SaaS tenants.</html>")
        c.gridy = 1
        c.gridwidth = 2
        panel.add(descLabel, c)

        // API URL Label
        c.gridwidth = 1
        c.gridy = 2
        c.gridx = 0
        panel.add(JLabel("API Server URL:"), c)

        // API URL Field
        c.gridx = 1
        c.weightx = 1.0
        panel.add(apiUrlField, c)

        // API Token Label
        c.gridx = 0
        c.gridy = 3
        c.weightx = 0.0
        panel.add(JLabel("API Token / Passport Key:"), c)

        // API Token Field
        c.gridx = 1
        c.weightx = 1.0
        panel.add(apiTokenField, c)

        // Test Connection Button
        val testButton = JButton("Test Connection")
        testButton.addActionListener {
            val url = apiUrlField.text.trim()
            if (url.isEmpty()) {
                Messages.showErrorDialog("Please enter an API URL first.", "Connection Test Failed")
                return@addActionListener
            }

            val testClient = HttpClient.newHttpClient()
            try {
                // Ping health endpoint
                val pingUrl = if (url.endsWith("/")) "${url}health" else "$url/health"
                val request = HttpRequest.newBuilder()
                    .uri(URI.create(pingUrl))
                    .GET()
                    .build()

                val response = testClient.send(request, HttpResponse.BodyHandlers.ofString())
                if (response.statusCode() == 200) {
                    Messages.showInfoMessage("Successfully connected to LLM Chat server health endpoint!", "Connection Successful")
                } else {
                    Messages.showWarningDialog("Connected to server but received status code: ${response.statusCode()}", "Connection Warning")
                }
            } catch (e: Exception) {
                Messages.showErrorDialog("Failed to connect to $url: ${e.message}", "Connection Failed")
            }
        }

        c.gridy = 4
        c.gridx = 1
        c.weightx = 0.0
        c.fill = GridBagConstraints.NONE
        c.anchor = GridBagConstraints.EAST
        panel.add(testButton, c)

        // Spacer to push everything up
        val spacer = JPanel()
        c.gridy = 5
        c.gridx = 0
        c.gridwidth = 2
        c.weighty = 1.0
        c.fill = GridBagConstraints.BOTH
        panel.add(spacer, c)

        mySettingsComponent = panel
        return panel
    }

    override fun isModified(): Boolean {
        val settings = LLMChatSettingsState.instance
        val currentUrl = settings.apiUrl
        val currentToken = LLMChatSettingsState.getApiToken()

        return apiUrlField.text != currentUrl || String(apiTokenField.password) != currentToken
    }

    override fun apply() {
        val settings = LLMChatSettingsState.instance
        settings.apiUrl = apiUrlField.text.trim()
        LLMChatSettingsState.setApiToken(String(apiTokenField.password).trim())
    }

    override fun reset() {
        val settings = LLMChatSettingsState.instance
        apiUrlField.text = settings.apiUrl
        apiTokenField.text = LLMChatSettingsState.getApiToken()
    }

    override fun disposeUIResources() {
        mySettingsComponent = null
    }
}
