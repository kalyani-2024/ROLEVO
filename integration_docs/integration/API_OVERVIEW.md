# Rolevo–Q3 API Integration Documentation

**Version:** 1.0  
**Last Updated:** January 29, 2026

---

## Table of contents

1. [Introduction](#introduction)
2. [Base URL configuration](#base-url-configuration)
3. [Authentication](#authentication)
4. [Integration flow](#integration-flow)
5. [Handshake 1: Cluster metadata sync](#handshake-1-cluster-metadata-sync)
6. [Handshake 2: Assessment launch](#handshake-2-assessment-launch)
7. [Handshake 3: Results submission](#handshake-3-results-submission)
8. [Error handling](#error-handling)

---

## Introduction

The Rolevo API enables integration with Q3 (Assessment / LMS). It supports:

- **Cluster metadata sync:** Push cluster configuration from Rolevo to Q3 when a cluster is created or updated
- **Assessment launch:** Users from Q3 can launch roleplay assessments in Rolevo
- **Results submission:** Send assessment results (scores, competencies, times) back to Q3

---

## Base URL configuration

**Rolevo (current):**

```
https://roleplays.trajectorie.com
```

**Q3:**  
Provide your base URL to the Rolevo team (e.g. `https://q3.example.com`).

---

## Authentication

### JWT token authentication

Both systems use **JWT** with a shared secret.

**Environment variable (both systems):**

```bash
Q3_INTEGRATION_SECRET=your-shared-secret-key
```

**JWT payload format (Q3 must include):**

```json
{
  "user_id": "EMP_789",
  "assessment_cluster_id": "b4bf406c-4f9",
  "iat": 1737964638,
  "exp": 1737965538
}
```

**Required claims:**

- `user_id`: User identifier from Q3
- `assessment_cluster_id`: Rolevo cluster ID (external `cluster_id` string)
- `iat`: Issued at (current time)
- `exp`: Expiration (e.g. `iat` + 15 minutes)

**Token expiry:** 15 minutes  
**Algorithm:** HS256

---

## Integration flow

```
STEP 1: CLUSTER METADATA SYNC
 Admin creates/updates cluster in Rolevo
   ↓
 Rolevo → POST /api/receive-cluster-metadata → Q3
   ↓
 Q3 stores cluster config (roleplays, competencies, max scores, times)

STEP 2: ASSESSMENT LAUNCH
 User clicks "Attempt assessment" in Q3
   ↓
 Q3 generates JWT
   ↓
 Q3 → POST /api/integration/assessment-launch → Rolevo
   ↓
 Rolevo validates token, creates session
   ↓
 Returns redirect_url to Q3
   ↓
 Q3 redirects user to Rolevo (POST form)
   ↓
 User completes roleplay(s)

STEP 3: RESULTS SUBMISSION
 User completes assessment in Rolevo
   ↓
 Rolevo → POST /api/receive-assessment-results → Q3
   ↓
 User redirects back to Q3 (return_url)
```

---

## Handshake 1: Cluster metadata sync

**Direction:** Rolevo → Q3  
**Trigger:** Admin creates or updates a cluster in Rolevo.

### Endpoint (Q3 must implement)

```
POST {Q3_BASE_URL}/api/receive-cluster-metadata
```

### Request headers

```
Content-Type: application/json
```

### Request body

See `schemas/cluster_metadata_sync.json`.

Includes:

- `cluster_id`, `cluster_name`, `cluster_type`
- `number_of_roleplays`, `roleplays[]` (ids, names, competencies, max scores, total time)
- Competency IDs and names per roleplay; max score per competency (including 16PF where used)

### Success response (HTTP 200)

```json
{
  "success": true,
  "cluster_id": "b4bf406c-4f9",
  "message": "Cluster metadata received successfully"
}
```

### Error responses

- **400 Bad Request:** Invalid or missing required fields  
See `schemas/error_responses.json` → `metadata_sync_errors`.

---

## Handshake 2: Assessment launch

**Direction:** Q3 → Rolevo → User  
**Trigger:** User clicks “Attempt assessment” in Q3.

### Step 1: Q3 sends launch request

**Endpoint (Rolevo implements):**

```
POST {ROLEVO_BASE_URL}/api/integration/assessment-launch
```

**Request headers:**

```
Content-Type: application/json
```

**Request body:**

See `schemas/assessment_launch_request.json`.

```json
{
  "user_id": "EMP_789",
  "user_name": "johndoe",
  "assessment_cluster_id": "b4bf406c-4f9",
  "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "return_url": "https://q3.example.com/dashboard",
  "results_url": "https://q3.example.com/api/receive-assessment-results"
}
```

- `results_url` (optional): Endpoint where Rolevo POSTs results. If present, Rolevo always uses this URL; otherwise it uses the configured default. Results are never sent to `Q3_BASE_URL` directly.

**Success response from Rolevo (HTTP 200):**

```json
{
  "success": true,
  "user_id": "EMP_789",
  "assessment_cluster_id": "b4bf406c-4f9",
  "redirect_url": "https://roleplays.trajectorie.com/api/integration/assessment-start",
  "message": "User authenticated successfully"
}
```

**Error responses:**  
See `schemas/assessment_launch_errors.json` (e.g. 401 invalid token, 404 cluster not found, 400 missing fields).

### Step 2: Q3 redirects user

After success, Q3 redirects the user to `redirect_url`:

- **Method:** POST  
- **Content-Type:** `application/x-www-form-urlencoded`  
- **Parameter:** `assessment_cluster_id` = Rolevo cluster ID

### Step 3: User experience

1. User lands on Rolevo assessment (cluster dashboard)
2. User completes one or more roleplays
3. After completion, Rolevo sends results to Q3 and redirects user to `return_url`

---

## Handshake 3: Results submission

**Direction:** Rolevo → Q3  
**Trigger:** User completes assessment (roleplay(s)) in Rolevo.

### Endpoint (Q3 must implement)

```
POST {Q3_BASE_URL}/api/receive-assessment-results
```

### Request headers

```
Content-Type: application/json
```

### Request body

See `schemas/results_submission.json`.

Includes:

- `cluster_id`, `cluster_name`, `cluster_type`
- `user_id`, `user_name`
- Per roleplay: `roleplay_id`, `roleplay_name`, `stakeholders` (2-digit numeric string), `max_time`, `time_taken`, `competency_code`, `competency_name`, `max_marks`, `marks_obtained` (repeat for each competency)
- One block per roleplay in the cluster that was attempted

### Success response from Q3 (HTTP 200)

```json
{
  "success": true,
  "user_id": "EMP_789",
  "cluster_id": "b4bf406c-4f9",
  "message": "Results received successfully"
}
```

### Error responses

- **400 Bad Request:** Invalid or missing required fields  
See `schemas/error_responses.json` → `results_submission_errors`.

### Post‑submission: user redirect

After successfully sending results to Q3, Rolevo redirects the user to the `return_url` from the assessment launch request.

---

## Error handling

All errors use:

```json
{
  "success": false,
  "detail": "Human-readable error message"
}
```

**Examples:**

- **Cluster not found (404):** `"detail": "Cluster not found: b4bf406c-4f9"`
- **Invalid token (401):** `"detail": "Authentication token is invalid or expired"`
- **Missing fields (400):** `"detail": "Missing required fields: user_id, assessment_cluster_id, auth_token, return_url"`

See `schemas/error_responses.json` for a full set.
