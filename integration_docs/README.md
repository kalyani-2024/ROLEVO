# Rolevo–Q3 Integration Documentation

**Version:** 1.0  
**Last Updated:** January 29, 2026

---

## Documentation structure

```
integration_docs/
├── README.md                      ← You are here
├── API_OVERVIEW.md                ← Complete API reference
├── Q3_IMPLEMENTATION_GUIDE.md     ← What Q3 team must build
├── TESTING.md                     ← How to test & verify before sending to Q3
├── PYTHONANYWHERE_Q3_DEPLOY.md    ← Files to upload & env vars for PythonAnywhere
└── schemas/                       ← JSON examples
    ├── cluster_metadata_sync.json
    ├── assessment_launch_request.json
    ├── assessment_launch_success.json
    ├── assessment_launch_errors.json
    ├── results_submission.json
    └── error_responses.json
```

---

### Testing before sending to Q3

See **[TESTING.md](TESTING.md)** for how to run the verification script, mock Q3 receiver, and end-to-end checks.

### Deploying to PythonAnywhere (hosted Rolevo)

See **[PYTHONANYWHERE_Q3_DEPLOY.md](PYTHONANYWHERE_Q3_DEPLOY.md)** for which files to upload and which env vars to set so you can test against the hosted site.

---

### For Q3 team

1. **Read:** `Q3_IMPLEMENTATION_GUIDE.md`
2. **Review:** `schemas/` folder for exact JSON formats
3. **Build:** 2 endpoints (receive cluster metadata & results)
4. **Implement:** User launch flow with JWT + POST redirect

**What to build:**

- Endpoint to receive cluster metadata from Rolevo (when cluster is created/updated)
- Endpoint to receive assessment results from Rolevo (when user completes roleplays)
- User launch flow (generate JWT → POST to Rolevo → redirect user)

---

### For Rolevo team

1. **Implement:** `POST /api/integration/assessment-launch` endpoint
2. **Implement:** Cluster metadata sync to Q3 on cluster create/update
3. **Implement:** Results sending to Q3 after user completes assessment
4. **Configure:** `Q3_INTEGRATION_SECRET` and `Q3_BASE_URL` environment variables
5. **Test:** Integration with Q3 team

---

## Integration flow

### 3 handshakes

**1. Cluster metadata sync** (Rolevo → Q3)

- **When:** Admin creates or updates a cluster in Rolevo
- **Endpoint:** `POST {Q3_BASE_URL}/api/receive-cluster-metadata`
- **JSON:** `cluster_metadata_sync.json`

**2. Assessment launch** (Q3 → Rolevo → User)

- **When:** User clicks “Attempt assessment” in Q3
- **Flow:**
  1. Q3 generates JWT token
  2. Q3 POSTs to `{ROLEVO}/api/integration/assessment-launch`
  3. Rolevo validates, returns `redirect_url`
  4. Q3 redirects user via POST form
  5. User completes roleplay(s) in Rolevo
- **JSONs:** `assessment_launch_request.json`, `assessment_launch_success.json`

**3. Results submission** (Rolevo → Q3)

- **When:** User completes roleplay(s) and submits assessment
- **Endpoint:** `POST {Q3_BASE_URL}/api/receive-assessment-results`
- **JSON:** `results_submission.json`

---

## Authentication

**Method:** JWT with shared secret

Both systems must set:

```bash
Q3_INTEGRATION_SECRET=your-matching-secret-key
```

**Usage:** Q3 generates JWT when launching users. Rolevo validates it.

---

## Base URLs

**Rolevo base URL:**

```
https://roleplays.trajectorie.com
```

*Q3 needs this to send assessment launch requests.*

**Q3 base URL:**  
Q3 team must provide their base URL (e.g. `https://q3.example.com`).  
*Rolevo needs this to send cluster metadata and results.*

---

## JSON schemas

All JSONs in `schemas/` are **direct examples** (not schema markup).

| File | Purpose |
|------|---------|
| `cluster_metadata_sync.json` | Cluster config sent to Q3 when cluster created/updated |
| `assessment_launch_request.json` | Launch request from Q3 |
| `assessment_launch_success.json` | Launch success response |
| `assessment_launch_errors.json` | Launch error responses |
| `results_submission.json` | Results sent to Q3 |
| `error_responses.json` | Other errors |

---

## Error format

All errors follow:

```json
{
  "success": false,
  "detail": "Error message here"
}
```

---

## What Q3 must build

1. **2 endpoints**
   - `POST /api/receive-cluster-metadata`
   - `POST /api/receive-assessment-results`
2. **User launch flow**
   - Generate JWT and POST to Rolevo
   - Redirect user to Rolevo assessment
3. **Data storage**
   - Cluster metadata (roleplays, competencies, max scores, times)
   - Assessment results (scores, time taken, competencies)

---

## What Rolevo must build

1. **1 endpoint**
   - `POST /api/integration/assessment-launch`
2. **Cluster metadata sync**
   - After cluster create/update, POST to Q3 metadata endpoint
3. **Results sending**
   - After user completes assessment, POST to Q3 results endpoint
4. **Session management**
   - Create session from Q3 user data
   - Store `return_url` for post-assessment redirect
   - After sending results to Q3, redirect user to `return_url`

---

## Testing

1. Q3 generates token and sends launch request
2. Rolevo validates and returns redirect URL
3. User is redirected to Rolevo via POST form
4. User completes roleplay(s)
5. Results are sent to Q3
6. User is redirected back to Q3 dashboard
