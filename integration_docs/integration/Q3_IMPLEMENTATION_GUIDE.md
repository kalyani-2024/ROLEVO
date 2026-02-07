# Q3 Integration Guide

**For:** Q3 development team  
**Purpose:** What Rolevo sends to Q3 and what Q3 must provide

---

## Configuration required

**Environment variable:**

```bash
Q3_INTEGRATION_SECRET=your-shared-secret-key
```

Must match Rolevo’s secret for JWT validation in Handshake 2.

**Base URL:**  
Provide your Q3 base URL to the Rolevo team (e.g. `https://q3.example.com`).

**JWT token format:**  
When generating `auth_token` for user launch, include:

```json
{
  "user_id": "EMP_789",
  "assessment_cluster_id": "b4bf406c-4f9",
  "iat": 1737964638,
  "exp": 1737965538
}
```

- **Expiry:** 15 minutes from issuance  
- **Algorithm:** HS256

---

## What Rolevo sends to Q3

### 1. Cluster metadata (when cluster created or updated)

**Rolevo calls:**

```
POST {Q3_BASE_URL}/api/receive-cluster-metadata
Content-Type: application/json
```

**You receive:**  
See `schemas/cluster_metadata_sync.json`.

Summary:

- `cluster_id`, `cluster_name`, `cluster_type`
- `number_of_roleplays`
- `roleplays[]`: each with `roleplay_id`, `roleplay_name`, `total_time_minutes`, `competencies[]` (id, name, max_score per competency, including 16PF where applicable)

**You must return:**

```json
{
  "success": true,
  "cluster_id": "b4bf406c-4f9",
  "message": "Cluster metadata received successfully"
}
```

**Error (if data invalid):**

```json
{
  "success": false,
  "detail": "Invalid cluster metadata format or missing required fields"
}
```

---

### 2. Assessment results (when user completes assessment)

**Rolevo calls:**

```
POST {Q3_BASE_URL}/api/receive-assessment-results
Content-Type: application/json
```

**You receive:**  
See `schemas/results_submission.json`.

Summary:

- `cluster_id`, `cluster_name`, `cluster_type`
- `user_id`, `user_name`
- `roleplays[]`: per roleplay, `roleplay_id`, `roleplay_name`, `stakeholders` (2‑digit string), `max_time`, `time_taken`, `competencies[]` with `competency_code`, `competency_name`, `max_marks`, `marks_obtained`

**You must return:**

```json
{
  "success": true,
  "user_id": "EMP_789",
  "cluster_id": "b4bf406c-4f9",
  "message": "Results received successfully"
}
```

**Error (if data invalid):**

```json
{
  "success": false,
  "detail": "Invalid results format or missing required fields"
}
```

---

## What Q3 sends to Rolevo

### User launch (when user clicks “Attempt assessment”)

**You call:**

```
POST https://roleplays.trajectorie.com/api/integration/assessment-launch
Content-Type: application/json
```

**You send:**  
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

- `auth_token`: JWT with `user_id` and `assessment_cluster_id` (15 min expiry).
- `return_url`: Where the user is sent after completing the assessment.
- `results_url` (optional): Where Rolevo POSTs assessment results. If omitted, Rolevo uses `Q3_BASE_URL` + `/api/receive-assessment-results` or `AIO_CALLBACK_URL`. **Results are always sent to this callback URL from the launch; Rolevo never posts results to `Q3_BASE_URL` directly.**

**Rolevo returns (success):**

```json
{
  "success": true,
  "user_id": "EMP_789",
  "assessment_cluster_id": "b4bf406c-4f9",
  "redirect_url": "https://roleplays.trajectorie.com/api/integration/assessment-start",
  "message": "User authenticated successfully"
}
```

**After success:**  
Redirect the user to `redirect_url` via **POST** (`application/x-www-form-urlencoded`) with form field `assessment_cluster_id` = Rolevo cluster ID.

**Possible errors:**  
See `schemas/assessment_launch_errors.json`.

---

## Summary

### Endpoints Q3 must implement

1. `POST /api/receive-cluster-metadata` – receive cluster configuration  
2. `POST /api/receive-assessment-results` – receive assessment results

### Endpoint Q3 calls

1. `POST /api/integration/assessment-launch` – launch user into Rolevo assessment

### Data schemas

Use the JSON examples in the `schemas/` folder as the reference format.
