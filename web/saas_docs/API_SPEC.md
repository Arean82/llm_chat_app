# SaaS API Specification

This document outlines the exposed API surfaces for the Synora Studio SaaS module.

## 1. OpenAI-Compatible Gateway (`/v1`)
The platform supports native OpenAI compatibility to allow easy drop-in replacement for downstream applications.

- **`GET /v1/models`**
  - **Description**: Returns the model catalog.
  - **Auth**: Bearer Token (Passport Key).
  - **Response**: Standard JSON list of model objects (filters out models where tenant lacks a BYOK credential).

- **`POST /v1/chat/completions`**
  - **Description**: Submits a chat completion job.
  - **Auth**: Bearer Token (Passport Key).
  - **Body**: standard `messages`, `model`, `temperature`, etc.
  - **Response**: Streamed chunking or standard sync response.

## 2. Authentication & Web Endpoints

- **`POST /login`**
  - **Body Form**: `username`, `password`
  - **Response**: Cookie session instantiation.

- **`POST /api/credentials`**
  - **Description**: Updates BYOK keys in the secure vault.
  - **Auth**: Web Session.

## 3. Administrator Endpoints
*These endpoints require an API Passport mapped to a user with `key_type = 'admin_funded'`.*

- **`GET /api/admin/users`**
  - **Description**: Lists all active tenants and total token spend.

- **`GET /api/admin/stats`**
  - **Description**: Retrieves aggregate burndown token graphs and historical trends.

- **`GET /api/admin/telemetry`**
  - **Description**: Exposes dynamic system health, background queue length, and circuit breaker statuses.
