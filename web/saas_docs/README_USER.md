# User Guide

Welcome to the **SaaS Platform User Guide**. This document explains how you can manage your account and connect third-party applications.

## 1. Registration and Passport Keys

To access the Synora Studio network, you must create an account. Once registered, your account is secured by a unique **API Passport Key**. This key is an encrypted token mapped strictly to your tenant identity.

- To retrieve your Passport Key, log into the Web Dashboard. Your key will be displayed on the main welcome screen.
- **Never share this key** publicly. It provides direct access to your billing and token quotas.

## 2. Managing BYOK (Bring Your Own Key)

The platform supports a BYOK architecture. This means you can plug your own direct API keys (like OpenAI or DeepSeek keys) securely into the platform.
1. Click the **Credential Manager** icon on your web dashboard.
2. Select your desired ecosystem.
3. Paste your key and click Save.

Your key is immediately encrypted using secure zero-trust symmetric PBKDF2 ciphers derived dynamically from your master login password. Raw keys are never written to disk in plaintext, and the system decrypts your credentials in transient memory exclusively for the duration of that isolated web request.

## 3. Connecting Client Applications

You can use your API Passport Key to connect external tools (like Continue.dev or Cline) to this host.
**Example Connection Schema:**
- **Base URL**: `http://<your-host-ip>:5000/v1`
- **API Key**: `<Your Passport Key>`

## 4. Public Orbit Sharing

Our platform allows you to safely export chat logs as "Orbits". 
When you click the export button, a secure static snapshot of your conversation is created and mapped to an unguessable `share_hash`. You can share this hash link with colleagues to let them read your conversation logs without granting them access to your account.
