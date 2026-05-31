package com.llmchat

import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.DialogWrapper
import com.intellij.openapi.ui.Messages
import com.google.gson.Gson
import com.google.gson.JsonObject
import java.awt.BorderLayout
import java.awt.GridBagConstraints
import java.awt.GridBagLayout
import java.awt.Insets
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import javax.swing.*

class LLMChatOnboardingDialog(project: Project?) : DialogWrapper(project, true) {
    private val tabbedPane = JTabbedPane()
    private val gson = Gson()
    private val client = HttpClient.newHttpClient()

    // Login Fields
    private val loginUrlField = JTextField("http://localhost:5000")
    private val loginUserField = JTextField()
    private val loginPassField = JPasswordField()
    private val loginStatusLabel = JLabel("")

    // Register Fields
    private val regUrlField = JTextField("http://localhost:5000")
    private val regUserField = JTextField()
    private val regEmailField = JTextField()
    private val regPassField = JPasswordField()
    private val regApiKeyField = JPasswordField()
    private val regKeyTypeCombo = JComboBox(arrayOf("Bring Your Own Key (BYOK)", "Admin Funded Tier"))
    private val regStatusLabel = JLabel("")

    init {
        title = "Synora Studio Onboarding Gateway"
        init()
    }

    override fun createCenterPanel(): JComponent {
        val dialogPanel = JPanel(BorderLayout())
        
        // Add Header
        val headerPanel = JPanel(BorderLayout())
        val titleLabel = JLabel("Connect IDE to Synora Studio", SwingConstants.CENTER)
        titleLabel.font = titleLabel.font.deriveFont(java.awt.Font.BOLD, 16f)
        val subtitleLabel = JLabel("Configure dynamic server credentials to activate completions", SwingConstants.CENTER)
        headerPanel.add(titleLabel, BorderLayout.NORTH)
        headerPanel.add(subtitleLabel, BorderLayout.SOUTH)
        headerPanel.border = BorderFactory.createEmptyBorder(10, 10, 15, 10)
        dialogPanel.add(headerPanel, BorderLayout.NORTH)

        // Setup Login Panel
        val loginPanel = JPanel(GridBagLayout())
        val lc = GridBagConstraints()
        lc.fill = GridBagConstraints.HORIZONTAL
        lc.insets = Insets(5, 5, 5, 5)

        lc.gridx = 0; lc.gridy = 0; lc.weightx = 0.0
        loginPanel.add(JLabel("Server URL:"), lc)
        lc.gridx = 1; lc.weightx = 1.0
        loginPanel.add(loginUrlField, lc)

        lc.gridx = 0; lc.gridy = 1; lc.weightx = 0.0
        loginPanel.add(JLabel("Email or Username:"), lc)
        lc.gridx = 1; lc.weightx = 1.0
        loginPanel.add(loginUserField, lc)

        lc.gridx = 0; lc.gridy = 2; lc.weightx = 0.0
        loginPanel.add(JLabel("Password:"), lc)
        lc.gridx = 1; lc.weightx = 1.0
        loginPanel.add(loginPassField, lc)

        // Login Button
        val loginBtn = JButton("Log In & Authenticate")
        loginBtn.addActionListener { performLogin() }
        lc.gridx = 1; lc.gridy = 3; lc.weightx = 0.0; lc.fill = GridBagConstraints.NONE
        lc.anchor = GridBagConstraints.EAST
        loginPanel.add(loginBtn, lc)

        // Login Status
        lc.gridx = 0; lc.gridy = 4; lc.gridwidth = 2; lc.weightx = 1.0; lc.fill = GridBagConstraints.HORIZONTAL
        loginStatusLabel.foreground = java.awt.Color.RED
        loginPanel.add(loginStatusLabel, lc)

        tabbedPane.addTab("Login", loginPanel)

        // Setup Register Panel
        val regPanel = JPanel(GridBagLayout())
        val rc = GridBagConstraints()
        rc.fill = GridBagConstraints.HORIZONTAL
        rc.insets = Insets(4, 4, 4, 4)

        rc.gridx = 0; rc.gridy = 0; rc.weightx = 0.0
        regPanel.add(JLabel("Server URL:"), rc)
        rc.gridx = 1; rc.weightx = 1.0
        regPanel.add(regUrlField, rc)

        rc.gridx = 0; rc.gridy = 1; rc.weightx = 0.0
        regPanel.add(JLabel("Username:"), rc)
        rc.gridx = 1; rc.weightx = 1.0
        regPanel.add(regUserField, rc)

        rc.gridx = 0; rc.gridy = 2; rc.weightx = 0.0
        regPanel.add(JLabel("Email Address:"), rc)
        rc.gridx = 1; rc.weightx = 1.0
        regPanel.add(regEmailField, rc)

        rc.gridx = 0; rc.gridy = 3; rc.weightx = 0.0
        regPanel.add(JLabel("Password:"), rc)
        rc.gridx = 1; rc.weightx = 1.0
        regPanel.add(regPassField, rc)

        rc.gridx = 0; rc.gridy = 4; rc.weightx = 0.0
        regPanel.add(JLabel("LLM API Key (Passport):"), rc)
        rc.gridx = 1; rc.weightx = 1.0
        regPanel.add(regApiKeyField, rc)

        rc.gridx = 0; rc.gridy = 5; rc.weightx = 0.0
        regPanel.add(JLabel("User Tier Key Type:"), rc)
        rc.gridx = 1; rc.weightx = 1.0
        regPanel.add(regKeyTypeCombo, rc)

        // Register Button
        val regBtn = JButton("Register & Create Workspace")
        regBtn.addActionListener { performRegister() }
        rc.gridx = 1; rc.gridy = 6; rc.weightx = 0.0; rc.fill = GridBagConstraints.NONE
        rc.anchor = GridBagConstraints.EAST
        regPanel.add(regBtn, rc)

        // Register Status
        rc.gridx = 0; rc.gridy = 7; rc.gridwidth = 2; rc.weightx = 1.0; rc.fill = GridBagConstraints.HORIZONTAL
        regStatusLabel.foreground = java.awt.Color.RED
        regPanel.add(regStatusLabel, rc)

        tabbedPane.addTab("Register Workspace", regPanel)

        dialogPanel.add(tabbedPane, BorderLayout.CENTER)
        dialogPanel.preferredSize = java.awt.Dimension(480, 360)
        return dialogPanel
    }

    override fun createActions(): Array<Action> {
        // Only return a Cancel button, because action buttons are handled interactively inside tabs
        return arrayOf(cancelAction)
    }

    private fun performLogin() {
        val serverUrl = loginUrlField.text.trim()
        val userInput = loginUserField.text.trim()
        val password = String(loginPassField.password).trim()

        if (serverUrl.isEmpty() || userInput.isEmpty() || password.isEmpty()) {
            loginStatusLabel.text = "Please fill in all standard credentials."
            return
        }

        loginStatusLabel.text = "Authenticating..."
        loginStatusLabel.foreground = java.awt.Color.BLUE

        SwingWorker.create {
            try {
                val loginUrl = "${serverUrl.trimEnd('/')}/api/login"
                val body = mapOf(
                    "username_or_email" to userInput,
                    "password" to password
                )

                val request = HttpRequest.newBuilder()
                    .uri(URI.create(loginUrl))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(gson.toJson(body)))
                    .build()

                val response = client.send(request, HttpResponse.BodyHandlers.ofString())
                if (response.statusCode() == 200) {
                    val json = gson.fromJson(response.body(), JsonObject::class.java)
                    if (json.get("success").asBoolean) {
                        val userObj = json.getAsJsonObject("user")
                        val passportToken = userObj.get("passport_token").asString

                        // Persist config dynamically
                        val settings = LLMChatSettingsState.instance
                        settings.apiUrl = serverUrl
                        LLMChatSettingsState.setApiToken(passportToken)

                        SwingUtilities.invokeLater {
                            Messages.showInfoMessage("Successfully authenticated! IDE is now fully connected.", "Login Successful")
                            close(OK_EXIT_CODE)
                        }
                    } else {
                        val err = json.get("error")?.asString ?: "Unknown login error"
                        showLoginError(err)
                    }
                } else {
                    val err = "Server responded with error code ${response.statusCode()}"
                    showLoginError(err)
                }
            } catch (e: Exception) {
                showLoginError("Connection failed: ${e.message}")
            }
        }.execute()
    }

    private fun showLoginError(msg: String) {
        SwingUtilities.invokeLater {
            loginStatusLabel.text = msg
            loginStatusLabel.foreground = java.awt.Color.RED
        }
    }

    private fun performRegister() {
        val serverUrl = regUrlField.text.trim()
        val username = regUserField.text.trim()
        val email = regEmailField.text.trim()
        val password = String(regPassField.password).trim()
        val apiKey = String(regApiKeyField.password).trim()
        val tierSelection = regKeyTypeCombo.selectedItem as String
        val keyType = if (tierSelection.contains("BYOK")) "byok" else "admin_funded"

        if (serverUrl.isEmpty() || username.isEmpty() || email.isEmpty() || password.isEmpty() || apiKey.isEmpty()) {
            regStatusLabel.text = "All registration parameters are mandatory."
            return
        }

        regStatusLabel.text = "Provisioning workspace..."
        regStatusLabel.foreground = java.awt.Color.BLUE

        SwingWorker.create {
            try {
                val regUrl = "${serverUrl.trimEnd('/')}/api/register"
                val body = mapOf(
                    "api_key" to apiKey,
                    "username" to username,
                    "email" to email,
                    "password" to password,
                    "key_type" to keyType
                )

                val request = HttpRequest.newBuilder()
                    .uri(URI.create(regUrl))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(gson.toJson(body)))
                    .build()

                val response = client.send(request, HttpResponse.BodyHandlers.ofString())
                if (response.statusCode() == 201 || response.statusCode() == 200) {
                    val json = gson.fromJson(response.body(), JsonObject::class.java)
                    if (json.get("success").asBoolean) {
                        SwingUtilities.invokeLater {
                            Messages.showInfoMessage("Account provisioned! Please sign in to activate this workspace.", "Registration Successful")
                            // Sync login tab details and switch
                            loginUrlField.text = serverUrl
                            loginUserField.text = username
                            loginPassField.text = password
                            tabbedPane.selectedIndex = 0
                            regStatusLabel.text = ""
                        }
                    } else {
                        val err = json.get("error")?.asString ?: "Registration failed."
                        showRegError(err)
                    }
                } else {
                    val err = "Server error code ${response.statusCode()}"
                    showRegError(err)
                }
            } catch (e: Exception) {
                showRegError("Connection failed: ${e.message}")
            }
        }.execute()
    }

    private fun showRegError(msg: String) {
        SwingUtilities.invokeLater {
            regStatusLabel.text = msg
            regStatusLabel.foreground = java.awt.Color.RED
        }
    }
}

// Utility extension for SwingWorker initialization inside Kotlin dialogs
private class SwingWorker<T>(private val executeBlock: () -> T) : javax.swing.SwingWorker<T, Void>() {
    override fun doInBackground(): T = executeBlock()
    
    companion object {
        fun <T> create(executeBlock: () -> T) = SwingWorker(executeBlock)
    }
}
