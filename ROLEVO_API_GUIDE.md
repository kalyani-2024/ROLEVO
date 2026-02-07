# Rolevo API Integration Guide

**Base URL:** `https://roleplays.trajectorie.com`

**Version:** 1.0  
**Last Updated:** January 2026

---

## Authentication

All API endpoints require JWT authentication.

### 1. Get Access Token

```http
POST /api/auth/token
Content-Type: application/json
```

**Request Body:**
```json
{
  "client_id": "q3_platform",
  "client_secret": "your_client_secret"
}
```

**Response:**
```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 86400
}
```

**Note:** Token is valid for 24 hours. Use in subsequent requests as:
```
Authorization: Bearer <access_token>
```

---

## Endpoints

### 2. Get All Clusters

Retrieve all available assessment clusters with their roleplays and competencies.

```http
GET /api/rolevo/clusters
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "success": true,
  "clusters": [
    {
      "cluster_id": "ddad93e3-324",
      "cluster_name": "Sales Training",
      "total_roleplays": 3,
      "total_time_minutes": 45,
      "roleplays": [
        {
          "roleplay_id": "RP_22P91IFO",
          "roleplay_name": "Customer Negotiation",
          "max_time_minutes": 15,
          "competencies": [
            {
              "competency_code": "EMP LEVEL 2",
              "competency_name": "Empathy Level 2"
            },
            {
              "competency_code": "PERSUADE LEVEL 2",
              "competency_name": "Persuasion- Win/Win mindset Level 2"
            }
          ]
        }
      ]
    }
  ]
}
```

---

### 3. Initialize SSO Session

Start a user assessment session via SSO.

```http
POST /api/auth/init
Content-Type: application/json
```

**Request Body:**
```json
{
  "api_token": "your_client_secret",
  "user_id": "EMP-12345",
  "user_name": "John Doe",
  "cluster_id": "ddad93e3-324",
  "callback_url": "https://your-system.com/webhook/rolevo"
}
```

**Response:**
```json
{
  "success": true,
  "redirect_url": "https://roleplays.trajectorie.com/api/auth/start?token=xxx&cluster_id=ddad93e3-324",
  "session_token": "xxx",
  "expires_in": 900
}
```

**Usage:** Redirect user's browser to `redirect_url` to start the assessment.

---

### 4. Get Scores by Cluster

Retrieve scores for all users in a cluster.

```http
GET /api/rolevo/scores/cluster/{cluster_id}
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "success": true,
  "cluster_id": "ddad93e3-324",
  "cluster_name": "Sales Training",
  "total_users": 2,
  "users": [
    {
      "user_id": "john@example.com",
      "roleplays": [
        {
          "roleplay_id": "RP_22P91IFO",
          "roleplay_name": "Customer Negotiation",
          "total_interactions": 8,
          "overall_score": 3,
          "time_taken_seconds": 1010,
          "completed_at": "2026-01-17T19:56:50",
          "competencies": [
            {
              "competency_code": "Motivating",
              "competency_name": "Motivating Level 2",
              "max_score": 24,
              "score_obtained": 22
            },
            {
              "competency_code": "Empathy",
              "competency_name": "Empathy Level 2",
              "max_score": 21,
              "score_obtained": 15
            }
          ]
        }
      ]
    }
  ]
}
```

---

### 5. Get Scores by User

Retrieve all scores for a specific user.

```http
GET /api/rolevo/scores/user/{user_id}
Authorization: Bearer <access_token>
```

**Parameters:**
- `user_id` - User's email or Q3 user ID

**Response:**
```json
{
  "success": true,
  "user_id": "EMP-12345",
  "total_roleplays": 2,
  "roleplays": [
    {
      "roleplay_id": "RP_22P91IFO",
      "roleplay_name": "Customer Negotiation",
      "cluster_id": "ddad93e3-324",
      "cluster_name": "Sales Training",
      "play_id": 456,
      "status": "completed",
      "start_time": "2026-01-17T19:40:00",
      "end_time": "2026-01-17T19:56:50",
      "time_taken_seconds": 1010,
      "total_interactions": 8,
      "overall_score": 3,
      "competencies": [
        {
          "competency_code": "Motivating",
          "competency_name": "Motivating Level 2",
          "max_score": 24,
          "score_obtained": 22,
          "interactions": 8
        }
      ]
    }
  ]
}
```

---

### 6. Get Scores by Play ID

Retrieve detailed scores for a specific play session.

```http
GET /api/rolevo/scores/play/{play_id}
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "success": true,
  "play": {
    "play_id": 456,
    "user_id": 123,
    "user_email": "john@example.com",
    "roleplay_id": "RP_22P91IFO",
    "roleplay_name": "Customer Negotiation",
    "cluster_id": "ddad93e3-324",
    "status": "completed",
    "start_time": "2026-01-17T19:40:00",
    "end_time": "2026-01-17T19:56:50"
  },
  "scores": [
    {
      "interaction_id": 789,
      "overall_score": 3,
      "competencies": [
        {
          "competency_name": "Motivating Level 2",
          "score": 3
        }
      ]
    }
  ]
}
```

---

## Webhook Callback (Optional)

When a user completes an assessment, Rolevo can send results to your callback URL.

**POST** to your `callback_url`

```json
{
  "event": "assessment_completed",
  "timestamp": "2026-01-17T19:56:50Z",
  "user_id": "EMP-12345",
  "cluster_id": "ddad93e3-324",
  "roleplay_id": "RP_22P91IFO",
  "play_id": 456,
  "overall_score": 3,
  "competencies": [
    {
      "competency_name": "Motivating Level 2",
      "score_obtained": 22,
      "max_score": 24
    }
  ]
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "success": false,
  "error": "Error message description"
}
```

**Common HTTP Status Codes:**
- `200` - Success
- `400` - Bad Request (missing parameters)
- `401` - Unauthorized (invalid/expired token)
- `404` - Resource not found
- `500` - Internal Server Error

---

## Integration Flow

1. **Get JWT Token** → `/api/auth/token`
2. **Fetch Clusters** → `/api/rolevo/clusters` (to show available assessments)
3. **Start SSO Session** → `/api/auth/init` (when user starts assessment)
4. **Redirect User** → to `redirect_url` returned
5. **User Completes Assessment** → Rolevo sends callback (if configured)
6. **Fetch Scores** → `/api/rolevo/scores/user/{user_id}` or `/api/rolevo/scores/cluster/{cluster_id}`

---

## Credentials

Contact Rolevo admin to obtain:
- `client_id`
- `client_secret`
