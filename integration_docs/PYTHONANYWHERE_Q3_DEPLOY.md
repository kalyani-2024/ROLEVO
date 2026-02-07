# PythonAnywhere: Q3 Integration Deployment

Use this checklist when uploading Rolevo to **PythonAnywhere** (or similar hosting) so the Q3 integration works on the **hosted** site.

---

## 1. Files to upload (required for integration)

Upload these **modified** files. Keep your existing project structure.

| File | Purpose |
|------|---------|
| `app/api_integration.py` | Assessment launch, assessment-start, cluster metadata sync, results payload (Q3 format) |
| `app/queries.py` | `get_cluster_by_id_or_external` helper |
| `app/routes.py` | `sync_cluster_metadata_to_q3` on cluster create/update, `return_url` for completion overlay |
| `.env.example` | Reference for Q3-related env vars (optional; see below) |

**Do not upload** (used only for local testing):

- `scripts/mock_q3_receiver.py` – run locally to receive metadata/results
- `scripts/test_q3_integration.py` – run locally, pointing at the hosted URL

**Optional** (documentation only; app does not load them):

- `integration_docs/` (README, API_OVERVIEW, Q3_IMPLEMENTATION_GUIDE, TESTING, `schemas/`) – useful to have in repo or on server for reference, but not required for the API to work.

---

## 2. Environment variables on PythonAnywhere

In the **Web** app → **WSGI configuration** / **Environment variables** (or a `.env` file if you load it), set:

| Variable | Required | Description |
|----------|----------|-------------|
| `Q3_INTEGRATION_SECRET` | Yes* | Shared secret for JWT validation. Must match what Q3 uses. |
| `AIO_CLIENT_SECRET` or `AIO_API_TOKEN` | Yes* | Same as above if you use these instead of `Q3_INTEGRATION_SECRET`. |
| `Q3_BASE_URL` | For metadata sync | Q3 base URL (e.g. `https://q3.example.com`). Rolevo POSTs cluster metadata here when you create/update clusters. |
| `AIO_CALLBACK_URL` | Fallback for results | Default URL for results callback if `results_url` is not sent in assessment-launch. |

\* At least one of `Q3_INTEGRATION_SECRET`, `AIO_CLIENT_SECRET`, or `AIO_API_TOKEN` must be set.

---

## 3. Reload the web app

After uploading the files and setting env vars:

1. Open the **Web** tab for your app.
2. Click **Reload**.
3. Check the **Error log** for startup issues.

---

## 4. Test against the hosted site

Run tests **on your local machine**, with Rolevo running on PythonAnywhere.

### 4.1 Point tests at the hosted URL

```bash
# .env or export (for test script)
ROLEVO_BASE_URL=https://youruser.pythonanywhere.com
# or
ROLEVO_BASE_URL=https://roleplays.trajectorie.com

Q3_INTEGRATION_SECRET=your_secret
# or AIO_CLIENT_SECRET / AIO_API_TOKEN
```

### 4.2 Run verification script

```bash
python scripts/test_q3_integration.py
```

This calls the **hosted** Rolevo API (token, clusters, assessment-launch, assessment-start).

### 4.3 Optional: mock Q3 receiver for metadata + results

1. Run locally: `python scripts/mock_q3_receiver.py` (listens on `http://127.0.0.1:5999`).
2. Use a **public URL** for the mock (e.g. [ngrok](https://ngrok.com) pointing at 5999), so the **hosted** Rolevo can reach it:
   - `Q3_BASE_URL` = `https://your-ngrok-url.ngrok.io`
   - `AIO_CALLBACK_URL` = `https://your-ngrok-url.ngrok.io/api/receive-assessment-results`
   - Or pass `results_url` in assessment-launch to that URL.
3. Create/update a cluster on the **hosted** app → metadata should hit the mock.
4. Complete a roleplay via assessment launch → results should hit the mock.

If you use **webhook.site** instead of the mock, set `AIO_CALLBACK_URL` or `results_url` to your webhook URL. The hosted app will POST results there.

---

## 5. Quick checklist

- [ ] `app/api_integration.py`, `app/queries.py`, `app/routes.py` uploaded.
- [ ] `Q3_INTEGRATION_SECRET` (or `AIO_CLIENT_SECRET` / `AIO_API_TOKEN`) set on PythonAnywhere.
- [ ] `Q3_BASE_URL` set if you use metadata sync.
- [ ] `AIO_CALLBACK_URL` set if you use a default results URL.
- [ ] Web app reloaded; error log clean.
- [ ] `ROLEVO_BASE_URL` set to hosted URL when running `scripts/test_q3_integration.py` locally.
