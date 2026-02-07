# Rolevo–Q3 Integration: Testing & Verification

Use this guide to verify the integration **before** sending specs to the Q3/trajectorie team.

**Testing against the hosted site (e.g. PythonAnywhere)?**  
See **[PYTHONANYWHERE_Q3_DEPLOY.md](PYTHONANYWHERE_Q3_DEPLOY.md)** for what to upload and which env vars to set. Then run the verification script locally with `ROLEVO_BASE_URL` pointing at your hosted URL.

---

## Prerequisites

- Python 3.8+
- Rolevo app running locally (`flask run` or `python roleplay.py`) or pointed at `https://roleplays.trajectorie.com`
- `.env` with `Q3_INTEGRATION_SECRET` or `AIO_CLIENT_SECRET` / `AIO_API_TOKEN` (same value Q3 will use)
- At least one **cluster** with roleplays in Rolevo

---

## 1. Quick API Checks (no mock server)

### 1.1 Get JWT and list clusters

```bash
# Get API token (use your CLIENT_SECRET from .env)
curl -X POST http://127.0.0.1:5000/api/auth/token \
  -H "Content-Type: application/json" \
  -d '{"client_id":"q3_platform","client_secret":"YOUR_CLIENT_SECRET"}'

# List clusters (use the access_token from above)
curl -X GET "http://127.0.0.1:5000/api/rolevo/clusters" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Note a `cluster_id` (e.g. `b4bf406c-4f9`) for the next steps.

### 1.2 Run the integration test script

```bash
# From project root
python scripts/test_q3_integration.py
```

This script will:

- Generate a Q3-style JWT and call `POST /api/integration/assessment-launch`
- Verify success and `redirect_url`
- Call `GET /api/integration/assessment-start` with the token (dry-run; no browser)
- Optionally validate a results payload against `schemas/results_submission.json`

Set env vars (or use `.env`):

- `ROLEVO_BASE_URL` — default `http://127.0.0.1:5000` (or `https://roleplays.trajectorie.com`)
- `Q3_INTEGRATION_SECRET` or `AIO_CLIENT_SECRET` — same as Rolevo
- `TEST_CLUSTER_ID` — optional; otherwise first cluster from `/api/rolevo/clusters` is used

---

## 2. End-to-end with mock Q3 receiver

Use a **mock Q3** server to receive cluster metadata and results.

### 2.1 Start the mock Q3 receiver

```bash
python scripts/mock_q3_receiver.py
```

Runs a small Flask app on **http://127.0.0.1:5999** with:

- `POST /api/receive-cluster-metadata` — cluster metadata (when you create/update a cluster)
- `POST /api/receive-assessment-results` — results when a user completes a roleplay

All received JSON is printed to the console.

### 2.2 Point Rolevo at the mock

**Option A: Environment variables**

```bash
# .env or export
Q3_BASE_URL=http://127.0.0.1:5999
AIO_CALLBACK_URL=http://127.0.0.1:5999/api/receive-assessment-results
```

**Option B: Use `results_url` in assessment-launch**

When calling assessment-launch, send:

```json
"results_url": "http://127.0.0.1:5999/api/receive-assessment-results"
```

(Use `http://localhost:5999` only if both Rolevo and mock run on same machine.)

### 2.3 Trigger cluster metadata sync

1. Start Rolevo (`flask run`).
2. Ensure `Q3_BASE_URL=http://127.0.0.1:5999` (or your mock URL).
3. In admin, **create** or **edit** a cluster and save.
4. Check mock receiver console: you should see a `POST /api/receive-cluster-metadata` with body matching `schemas/cluster_metadata_sync.json` (cluster_id, cluster_name, cluster_type, roleplays, etc.).

### 2.4 Test assessment launch → start → complete → results

1. Run `python scripts/test_q3_integration.py` (assessment-launch + assessment-start).
2. **Browser flow:**
   - Use the `redirect_url` from the launch response.
   - Open it (GET); you’ll land on assessment-start, then redirect to the cluster dashboard.
   - Complete a roleplay.
3. Check mock receiver console: you should see `POST /api/receive-assessment-results` with body matching `schemas/results_submission.json` (cluster_id, cluster_name, cluster_type, user_id, user_name, roleplays with stakeholders, max_time, time_taken, competencies, etc.).

---

## 3. Verify payload shapes

### 3.1 Cluster metadata (`cluster_metadata_sync.json`)

- `cluster_id`, `cluster_name`, `cluster_type`
- `number_of_roleplays`
- `roleplays[]`: each with `roleplay_id`, `roleplay_name`, `total_time_minutes`, `competencies[]` (`competency_id`, `competency_name`, `max_score`)

### 3.2 Results (`results_submission.json`)

- `cluster_id`, `cluster_name`, `cluster_type`
- `user_id`, `user_name`
- `roleplays[]`: each with `roleplay_id`, `roleplay_name`, `stakeholders` (2-char numeric), `max_time`, `time_taken`, `competencies[]` (`competency_code`, `competency_name`, `max_marks`, `marks_obtained`)

### 3.3 Assessment launch

- Request: `user_id`, `user_name`, `assessment_cluster_id`, `auth_token`, `return_url`, optional `results_url`.
- Response: `success`, `redirect_url`, `message`.

---

## 4. Optional: Use webhook.site for results only

If you prefer not to run the mock receiver:

1. Go to [webhook.site](https://webhook.site), copy your unique URL.
2. Use that URL as `results_url` when calling assessment-launch (or set `AIO_CALLBACK_URL` to it).
3. Complete a roleplay in Rolevo and confirm the results POST on webhook.site.
4. Manually compare the JSON to `schemas/results_submission.json`.

---

## 5. Checklist before sending to Q3

- [ ] `POST /api/integration/assessment-launch` returns 200 and `redirect_url` for valid JWT + cluster.
- [ ] `GET /api/integration/assessment-start?token=...&cluster_id=...` redirects to cluster dashboard.
- [ ] Cluster create/update triggers metadata sync to mock Q3 (or webhook) and payload matches `cluster_metadata_sync.json`.
- [ ] Completing a roleplay sends results to `results_url` / `AIO_CALLBACK_URL`; payload matches `results_submission.json`.
- [ ] `cluster_type` and `stakeholders` are present in results.
- [ ] JWT validation rejects invalid/expired tokens (401).
- [ ] Missing required fields in launch request return 400.

---

## 6. Troubleshooting

| Issue | What to check |
|-------|----------------|
| 401 on assessment-launch | JWT secret: Rolevo and test script must use the same `Q3_INTEGRATION_SECRET` / `AIO_CLIENT_SECRET`. |
| 404 cluster not found | Use `cluster_id` from `GET /api/rolevo/clusters` (external ID string). |
| No metadata sync | `Q3_BASE_URL` set? Cluster create/update in admin? |
| No results callback | `results_url` in launch or `AIO_CALLBACK_URL` set? User completed roleplay in an integration session? |
| Mock unreachable | Same machine: `127.0.0.1:5999`. Different machine: use host IP and ensure firewall allows it. |
