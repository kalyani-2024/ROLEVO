# Rolevo Roleplay System - Third-Party Integration Guide

## System Overview

**Rolevo** is a Flask-based AI-powered roleplay training and assessment platform that enables users to practice conversations with virtual characters using text or voice inputs. The system evaluates user responses against predefined competencies and generates detailed performance reports.

### Key Features
- 🎭 Interactive roleplay scenarios with AI-powered responses (OpenAI GPT)
- 🎙️ Voice and text input support with multi-language capabilities
- 📊 Real-time competency scoring and feedback
- 📈 PDF report generation with score breakdowns
- 🏆 Cluster-based training and assessment modes
- 👥 User and admin role management
- 🔄 Multi-attempt roleplay support with optimal video demonstrations

---

## Architecture Overview

```
┌─────────────────┐
│  Third-Party    │
│     System      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│         Rolevo Flask Application         │
│  ┌─────────────┐  ┌─────────────────┐  │
│  │   Routes    │  │  Database Layer │  │
│  │  (routes.py)│←→│   (queries.py)  │  │
│  └─────────────┘  └─────────────────┘  │
│         ↓                  ↓            │
│  ┌─────────────┐  ┌─────────────────┐  │
│  │  Interface  │  │  Reader/Excel   │  │
│  │(OpenAI/TTS) │  │   Processing    │  │
│  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────┘
         ↓                  ↓
┌─────────────────┐  ┌─────────────────┐
│  MySQL Database │  │  External APIs  │
│  (roleplay DB)  │  │ - OpenAI GPT    │
│                 │  │ - Google TTS    │
└─────────────────┘  └─────────────────┘
```

---

## 1. Database Schema & Data Models

### Core Tables

#### **users** - User Authentication & Profiles
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,  -- bcrypt hashed
    is_admin TINYINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**JSON Structure:**
```json
{
  "id": 5,
  "email": "user@example.com",
  "is_admin": 0,
  "created_at": "2025-01-15T10:30:00Z"
}
```

---

#### **roleplay** - Roleplay Scenarios
```sql
CREATE TABLE roleplay (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500),              -- Excel file with conversation flow
    image_file_path VARCHAR(500),        -- Excel file with character images
    competency_file_path VARCHAR(500),   -- Master competency definitions
    scenario TEXT,                        -- Scenario description
    person_name VARCHAR(255),            -- Character name
    scenario_file_path VARCHAR(500),     -- Downloadable scenario document
    logo_path VARCHAR(500),              -- Character avatar/logo
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

**JSON Structure:**
```json
{
  "id": "RP_TVC2MN3M",
  "name": "Difficult Team Member Conversation",
  "scenario": "You are meeting with Alex, a team member who has been missing deadlines...",
  "person_name": "Alex Johnson",
  "file_path": "uploads/roleplay/conversation_flow.xlsx",
  "image_file_path": "uploads/images/character_images.xlsx",
  "competency_file_path": "uploads/competency/master_competencies.xlsx",
  "scenario_file_path": "uploads/scenarios/alex_context.pdf",
  "logo_path": "uploads/logos/alex_avatar.png",
  "created_at": "2025-01-10T09:00:00Z",
  "updated_at": "2025-01-15T14:30:00Z"
}
```

---

#### **roleplay_config** - Roleplay Configuration
```sql
CREATE TABLE roleplay_config (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    roleplay_id VARCHAR(100) NOT NULL,
    competencies_included TEXT,          -- JSON array of competency names
    input_type ENUM('audio', 'text') DEFAULT 'audio',
    player_vs_computer VARCHAR(50) DEFAULT 'computer',
    available_languages TEXT,            -- JSON array: ["English", "Hindi", "Tamil"]
    max_interaction_time INTEGER DEFAULT 300,      -- seconds per response
    max_total_time INTEGER DEFAULT 1800,           -- total roleplay time
    repeat_attempts_allowed INTEGER DEFAULT 1,
    character_name VARCHAR(255),
    show_ideal_video BOOLEAN DEFAULT FALSE,
    ideal_video_path VARCHAR(500),       -- Google Drive link or local path
    video_auto_play BOOLEAN DEFAULT TRUE,
    difficulty_level ENUM('easy', 'medium', 'hard') DEFAULT 'easy',
    FOREIGN KEY (roleplay_id) REFERENCES roleplay(id) ON DELETE CASCADE
);
```

**JSON Structure:**
```json
{
  "id": 45,
  "roleplay_id": "RP_TVC2MN3M",
  "competencies_included": "[\"Empathy\", \"Active Listening\", \"Problem Solving\"]",
  "input_type": "audio",
  "player_vs_computer": "computer",
  "available_languages": "[\"English\", \"Hindi\", \"Tamil\"]",
  "max_interaction_time": 300,
  "max_total_time": 1800,
  "repeat_attempts_allowed": 3,
  "character_name": "Alex Johnson",
  "show_ideal_video": true,
  "ideal_video_path": "https://drive.google.com/file/d/1ABC.../view",
  "video_auto_play": false,
  "difficulty_level": "medium"
}
```

---

#### **roleplay_cluster** - Training/Assessment Clusters
```sql
CREATE TABLE roleplay_cluster (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(1000) NOT NULL,
    cluster_id VARCHAR(100) NOT NULL UNIQUE,
    type ENUM('assessment', 'training') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

**JSON Structure:**
```json
{
  "id": 12,
  "name": "Leadership Assessment Q1 2025",
  "cluster_id": "CLUSTER_LEAD_Q1",
  "type": "assessment",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-15T10:00:00Z"
}
```

**Key Differences:**
- **Training Mode**: Shows scores, allows retries, displays tips and optimal videos
- **Assessment Mode**: Hides all scores, no retries, no feedback, evaluation-focused

---

#### **cluster_roleplay** - Cluster-Roleplay Mapping
```sql
CREATE TABLE cluster_roleplay (
    cluster_id INTEGER NOT NULL,
    roleplay_id VARCHAR(100) NOT NULL,
    order_sequence INTEGER DEFAULT 1,
    PRIMARY KEY (cluster_id, roleplay_id),
    FOREIGN KEY (cluster_id) REFERENCES roleplay_cluster(id) ON DELETE CASCADE,
    FOREIGN KEY (roleplay_id) REFERENCES roleplay(id) ON DELETE CASCADE
);
```

---

#### **user_cluster** - User Cluster Access
```sql
CREATE TABLE user_cluster (
    user_id INTEGER NOT NULL,
    cluster_id INTEGER NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, cluster_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (cluster_id) REFERENCES roleplay_cluster(id) ON DELETE CASCADE
);
```

---

#### **play** - User Roleplay Sessions
```sql
CREATE TABLE play (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    user_id INTEGER NOT NULL,
    roleplay_id VARCHAR(100) NOT NULL,
    cluster_id INTEGER,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP NULL,
    status ENUM('in_progress', 'completed', 'optimal_viewed') DEFAULT 'in_progress',
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (roleplay_id) REFERENCES roleplay(id),
    FOREIGN KEY (cluster_id) REFERENCES roleplay_cluster(id)
);
```

**JSON Structure:**
```json
{
  "id": 1523,
  "user_id": 5,
  "roleplay_id": "RP_TVC2MN3M",
  "cluster_id": 12,
  "start_time": "2025-01-15T14:30:00Z",
  "end_time": "2025-01-15T14:55:00Z",
  "status": "completed"
}
```

---

#### **scorebreakdown** - Competency Scores
```sql
CREATE TABLE scorebreakdown (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    play_id INTEGER NOT NULL,
    competency VARCHAR(255) NOT NULL,
    score FLOAT NOT NULL,
    max_score FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (play_id) REFERENCES play(id) ON DELETE CASCADE
);
```

**JSON Structure:**
```json
{
  "id": 8901,
  "play_id": 1523,
  "competency": "Empathy Level 2",
  "score": 8.5,
  "max_score": 12.0,
  "created_at": "2025-01-15T14:55:00Z"
}
```

---

#### **character_gender** - Voice Configuration
```sql
CREATE TABLE character_gender (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    roleplay_id VARCHAR(100) NOT NULL,
    character_name VARCHAR(255) NOT NULL,
    gender ENUM('male', 'female') NOT NULL,
    UNIQUE KEY unique_roleplay_character (roleplay_id, character_name),
    FOREIGN KEY (roleplay_id) REFERENCES roleplay(id) ON DELETE CASCADE
);
```

**JSON Structure:**
```json
{
  "id": 23,
  "roleplay_id": "RP_TVC2MN3M",
  "character_name": "Alex Johnson",
  "gender": "male"
}
```

---

## 2. Excel File Formats

### A. Conversation Flow Excel (file_path)
**Sheet: "Main"**
| Interaction | Competency | Tips | Next | Computer Says | Player Says | Image |
|-------------|------------|------|------|---------------|-------------|-------|
| 1 | Empathy Level 2 | Show understanding | 2,3 | Hello, thanks for meeting me | Hi Alex, how are you? | image1.jpg |
| 2 | Problem Solving | Ask open questions | 4 | I've been struggling with the workload | Tell me more about it | image2.jpg |

**Key Columns:**
- `Interaction`: Numeric ID (1, 2, 3...)
- `Competency`: Competency name(s) being tested (comma-separated)
- `Tips`: Guidance for training mode
- `Next`: Next interaction ID(s) - comma-separated for multiple paths
- `Computer Says`: Character's dialogue
- `Player Says`: Example user response (optional)
- `Image`: Character image filename

### B. Tags Sheet (in same Excel or separate)
**Sheet: "Tags"**
| Competencies | Max Score | Enabled | Description |
|--------------|-----------|---------|-------------|
| Empathy Level 2 | 12 | TRUE | Shows understanding of emotions |
| Active Listening | 18 | TRUE | Pays attention and clarifies |
| Problem Solving | 15 | FALSE | Identifies root causes |

**Purpose**: Defines which competencies are scored and their maximum values

### C. Master Competency File (competency_file_path)
**Sheet: "Sheet1"**
| Abbr | CompetencyType | Description | Score 0 | Score 1 | Score 2 | Score 3 |
|------|----------------|-------------|---------|---------|---------|---------|
| EMP | Empathy Level 2 | Understanding emotions | No empathy | Acknowledges | Shows concern | Deep empathy |
| ACTLSTN | Active Listening | Attentive listening | Interrupts | Listens | Clarifies | Summarizes |

### D. Image Excel (image_file_path)
**Sheet: "Main"**
| Interaction | Image | Character |
|-------------|-------|-----------|
| 1 | image1.jpg | Alex Johnson |
| 2 | image2.jpg | Alex Johnson |

---

## 3. Integration Points & APIs

### Authentication & Session Management

#### User Login
```http
POST /login
Content-Type: application/x-www-form-urlencoded

email=user@example.com&password=secret123
```

**Response (Redirect):**
```
HTTP 302 Redirect to /user_dashboard/<user_id>
Set-Cookie: session=<encrypted_session_token>; Path=/; HttpOnly
```

**Session Structure:**
```python
{
    'user_id': 5,
    'is_admin': 0,
    'user_email': 'user@example.com',
    'cluster_id': 12,
    'roleplay_id': 'RP_TVC2MN3M',
    'selected_language': 'English',
    'interaction_number': 3,
    'play_id': 1523
}
```

---

#### Admin Login
```http
POST /admin/login
Content-Type: application/x-www-form-urlencoded

email=admin@example.com&password=adminpass
```

**Response:**
```
HTTP 302 Redirect to /admin
Set-Cookie: session=<encrypted_admin_session>; Path=/; HttpOnly; Max-Age=604800
```

**Admin Session:**
```python
{
    'user_id': 1,
    'is_admin': 1,
    'user_email': 'admin@example.com'
}
```

---

### Roleplay Lifecycle

#### 1. Launch Roleplay
```http
GET /launch/<user_id>/<roleplay_id>?language=English&cluster_id=12
```

**What Happens:**
1. Creates `play` record with status `in_progress`
2. Loads Excel files (conversation flow, images, competencies)
3. Initializes session with roleplay context
4. Redirects to `/chatbot/<roleplay_id>/<interaction_num>`

**Session Data Set:**
```python
{
    'user_id': 5,
    'roleplay_id': 'RP_TVC2MN3M',
    'cluster_id': 12,
    'play_id': 1523,
    'interaction_number': 1,
    'selected_language': 'English',
    'input_type': 'audio',
    'max_interaction_time': 300,
    'max_total_time': 1800,
    'roleplay_start_time': 1705329000.123
}
```

---

#### 2. Chatbot Interaction
```http
GET /chatbot/<roleplay_id>/<interaction_num>
```

**Response:** HTML page with:
- Character dialogue (text + audio)
- Character image
- User input form (text or voice recording)
- Score display (training mode only)
- Timer display

**Context Data Sent to Template:**
```json
{
  "roleplay_id": "RP_TVC2MN3M",
  "interaction_number": 3,
  "scenario": "You are meeting with Alex...",
  "comp_dialogue": "I've been struggling with the workload lately.",
  "image": "/static/images/alex_image3.jpg",
  "tip": "Ask open-ended questions to understand the root cause",
  "competencies": ["Empathy Level 2", "Active Listening"],
  "score": 2,
  "last_round_result": {
    "Empathy Level 2": 2,
    "Active Listening": 1
  },
  "cumul_score": {
    "Empathy Level 2": {"score": 6.5, "total": 12},
    "Active Listening": {"score": 4.0, "total": 18}
  },
  "cluster_type": "training",
  "input_type": "audio",
  "available_languages": ["English", "Hindi", "Tamil"],
  "selected_language": "English",
  "is_final": false,
  "is_final_interaction": false
}
```

---

#### 3. Submit User Response
```http
POST /chatbot/<roleplay_id>/<interaction_num>
Content-Type: application/x-www-form-urlencoded

post=I%20understand%20this%20must%20be%20challenging&submit=Submit
```

**What Happens:**
1. Sends user response to OpenAI GPT for scoring
2. Calculates competency scores (0-3 scale)
3. Saves scores to `scorebreakdown` table
4. Determines next interaction based on Excel flow
5. Redirects to next interaction or completion page

**Scoring JSON (Internal):**
```json
{
  "sentiment_analysis": {
    "sentiment": "empathetic",
    "score": 2,
    "explanation": "Shows understanding of the challenge"
  },
  "tips_following_analysis": {
    "followed": true,
    "score": 2,
    "explanation": "Used open-ended questioning"
  },
  "competency_scores": {
    "Empathy Level 2": 2,
    "Active Listening": 2,
    "Problem Solving": 1
  }
}
```

---

#### 4. Roleplay Completion
```http
GET /chatbot/<roleplay_id>/<final_interaction>
```

**Final Page Context:**
```json
{
  "is_final": true,
  "is_final_interaction": true,
  "cluster_type": "training",
  "completion_message": "Great work! You completed this training roleplay.",
  "can_retry": true,
  "retry_disabled": false,
  "max_attempts": 3,
  "completed_attempts": 1,
  "attempts_remaining": 2,
  "has_viewed_optimal": false,
  "show_ideal_video": true,
  "ideal_video_path": "https://drive.google.com/file/d/1ABC.../view",
  "show_optimal_warning": true,
  "home_url": "/user/5/cluster/12"
}
```

**Assessment Mode Completion:**
```json
{
  "is_final": true,
  "is_final_interaction": true,
  "cluster_type": "assessment",
  "completion_message": "Great work! You completed this assessment.",
  "can_retry": false,
  "show_ideal_video": false,
  "home_url": "/user/5/cluster/12"
}
```

---

### Report Generation

#### Get PDF Report
```http
GET /showreport/<play_id>
```

**Response:**
```
HTTP 200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename="roleplay_report_1523.pdf"

[PDF Binary Data]
```

**Report Contents:**
- User name and email
- Roleplay name and completion date
- Overall score percentage
- Competency-wise breakdown with descriptions
- Score bar charts
- Performance analysis

**Data Flow for Report:**
1. Fetch `play` record by `play_id`
2. Fetch all `scorebreakdown` records for that play
3. Read Tags sheet from Excel (max scores)
4. Read Master file (descriptions)
5. Calculate percentages: `(score / max_score) * 100`
6. Generate PDF using ReportLab

---

## 4. External API Integrations

### OpenAI GPT-4 (AI Scoring)

**Endpoint Used:** `https://api.openai.com/v1/chat/completions`

**Request Structure:**
```json
{
  "model": "gpt-4",
  "messages": [
    {
      "role": "system",
      "content": "You are evaluating a roleplay conversation. Score the user's empathy on a 0-3 scale..."
    },
    {
      "role": "user",
      "content": "User said: 'I understand this must be challenging for you.'"
    }
  ],
  "temperature": 0.7,
  "max_tokens": 500
}
```

**Response:**
```json
{
  "choices": [
    {
      "message": {
        "content": "Score: 2\nExplanation: The user shows understanding and empathy..."
      }
    }
  ]
}
```

**Environment Variable Required:**
```bash
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
```

---

### Google Text-to-Speech (Audio Generation)

**Python Library:** `gTTS` (Google Text-to-Speech)

**Usage:**
```python
from gtts import gTTS

text = "Hello, thanks for meeting with me today."
tts = gTTS(text=text, lang='en', slow=False)
tts.save('static/audio/interaction_1.mp3')
```

**Audio Cache:**
- Location: `app/static/audio_cache/`
- Naming: `<text_hash>_<gender>.mp3`
- Auto-generated on first request, cached for reuse

**API Endpoint:**
```http
GET /make_audio?text=Hello%20world&gender=male&character=Alex
```

**Response:**
```
HTTP 200 OK
Content-Type: audio/mpeg

[MP3 Binary Data]
```

---

## 5. Integration Scenarios

### Scenario A: Single Sign-On (SSO) Integration

**Third-Party System → Rolevo**

1. **User Authentication at Third-Party**
   ```json
   POST https://your-system.com/api/authenticate
   Response: {
     "user_id": "EXT_12345",
     "email": "john@company.com",
     "name": "John Doe",
     "token": "jwt_token_here"
   }
   ```

2. **Create/Sync User in Rolevo**
   ```python
   # Pseudo-code for integration endpoint (needs to be created)
   POST /api/v1/users/sync
   Authorization: Bearer <api_key>
   Content-Type: application/json
   
   {
     "external_id": "EXT_12345",
     "email": "john@company.com",
     "password_hash": "<bcrypt_hash>",  # Or skip password for SSO
     "is_admin": false
   }
   ```

3. **Assign User to Cluster**
   ```python
   POST /api/v1/user_cluster/assign
   Authorization: Bearer <api_key>
   Content-Type: application/json
   
   {
     "user_id": 5,
     "cluster_id": 12
   }
   ```

4. **Launch Roleplay with Auto-Login**
   ```http
   GET /launch/5/RP_TVC2MN3M?language=English&cluster_id=12&auto_login_token=<token>
   ```

---

### Scenario B: Webhook for Completion Notifications

**Rolevo → Third-Party System**

When a user completes a roleplay, send completion data:

```http
POST https://your-system.com/api/webhooks/roleplay_completed
Content-Type: application/json
Authorization: Bearer <webhook_secret>

{
  "event": "roleplay.completed",
  "timestamp": "2025-01-15T14:55:00Z",
  "data": {
    "play_id": 1523,
    "user_id": 5,
    "user_email": "john@company.com",
    "roleplay_id": "RP_TVC2MN3M",
    "roleplay_name": "Difficult Team Member Conversation",
    "cluster_id": 12,
    "cluster_name": "Leadership Assessment Q1 2025",
    "cluster_type": "assessment",
    "start_time": "2025-01-15T14:30:00Z",
    "end_time": "2025-01-15T14:55:00Z",
    "duration_seconds": 1500,
    "status": "completed",
    "scores": [
      {
        "competency": "Empathy Level 2",
        "score": 8.5,
        "max_score": 12.0,
        "percentage": 70.83
      },
      {
        "competency": "Active Listening",
        "score": 12.0,
        "max_score": 18.0,
        "percentage": 66.67
      }
    ],
    "overall_percentage": 68.75,
    "report_url": "https://rolevo-app.com/showreport/1523"
  }
}
```

---

### Scenario C: LMS Integration (SCORM/xAPI)

**xAPI Statement Example:**
```json
{
  "actor": {
    "mbox": "mailto:john@company.com",
    "name": "John Doe"
  },
  "verb": {
    "id": "http://adlnet.gov/expapi/verbs/completed",
    "display": {"en-US": "completed"}
  },
  "object": {
    "id": "https://rolevo-app.com/roleplay/RP_TVC2MN3M",
    "definition": {
      "name": {"en-US": "Difficult Team Member Conversation"},
      "type": "http://adlnet.gov/expapi/activities/simulation"
    }
  },
  "result": {
    "score": {
      "scaled": 0.6875,
      "raw": 68.75,
      "min": 0,
      "max": 100
    },
    "completion": true,
    "success": true,
    "duration": "PT25M00S"
  },
  "context": {
    "contextActivities": {
      "parent": [{
        "id": "https://rolevo-app.com/cluster/12",
        "definition": {
          "name": {"en-US": "Leadership Assessment Q1 2025"},
          "type": "http://adlnet.gov/expapi/activities/course"
        }
      }]
    }
  }
}
```

---

## 6. Configuration Requirements

### Environment Variables (.env)
```bash
# Database Configuration
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=roleplay

# Flask Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=production

# OpenAI API
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx

# File Upload Paths
UPLOAD_PATH_ROLEPLAY=data/roleplay
UPLOAD_PATH_IMAGES=data/images
UPLOAD_PATH_COMP=data/master
UPLOAD_PATH_SCENARIOS=data/scenarios
UPLOAD_PATH_LOGOS=data/logos

# Session Configuration (Optional)
PERMANENT_SESSION_LIFETIME=604800  # 7 days in seconds

# External Integration (if needed)
WEBHOOK_URL=https://your-system.com/api/webhooks/roleplay_completed
WEBHOOK_SECRET=webhook_secret_key
API_KEY=rolevo_api_key_for_third_party
```

---

## 7. API Endpoints Reference

### Suggested REST API for Integration (To Be Implemented)

```http
# User Management
POST   /api/v1/users                  # Create user
GET    /api/v1/users/<user_id>        # Get user details
PUT    /api/v1/users/<user_id>        # Update user
DELETE /api/v1/users/<user_id>        # Delete user

# Cluster Management
POST   /api/v1/clusters               # Create cluster
GET    /api/v1/clusters                # List all clusters
GET    /api/v1/clusters/<cluster_id>  # Get cluster details
POST   /api/v1/clusters/<cluster_id>/assign  # Assign user to cluster

# Roleplay Management
GET    /api/v1/roleplays              # List all roleplays
GET    /api/v1/roleplays/<roleplay_id> # Get roleplay details
POST   /api/v1/roleplays/<roleplay_id>/launch  # Launch roleplay for user

# Progress & Scoring
GET    /api/v1/plays/<play_id>        # Get play session details
GET    /api/v1/plays/<play_id>/scores # Get competency scores
GET    /api/v1/users/<user_id>/progress  # Get user progress across all roleplays

# Reports
GET    /api/v1/reports/<play_id>/pdf   # Download PDF report
GET    /api/v1/reports/<play_id>/json  # Get report data as JSON
```

---

## 8. Data Exchange Formats

### User Progress JSON
```json
{
  "user_id": 5,
  "email": "john@company.com",
  "total_roleplays_assigned": 15,
  "completed_roleplays": 8,
  "in_progress_roleplays": 2,
  "not_started_roleplays": 5,
  "average_score_percentage": 72.5,
  "clusters": [
    {
      "cluster_id": 12,
      "cluster_name": "Leadership Assessment Q1 2025",
      "cluster_type": "assessment",
      "roleplays": [
        {
          "roleplay_id": "RP_TVC2MN3M",
          "name": "Difficult Team Member",
          "status": "completed",
          "attempts": 1,
          "last_score": 68.75,
          "completed_at": "2025-01-15T14:55:00Z"
        }
      ]
    }
  ]
}
```

### Competency Scores JSON
```json
{
  "play_id": 1523,
  "roleplay_id": "RP_TVC2MN3M",
  "user_id": 5,
  "completed_at": "2025-01-15T14:55:00Z",
  "scores": [
    {
      "competency": "Empathy Level 2",
      "description": "Shows understanding of others' emotions and perspectives",
      "score": 8.5,
      "max_score": 12.0,
      "percentage": 70.83,
      "rating": "Good"
    },
    {
      "competency": "Active Listening",
      "description": "Pays attention and clarifies understanding",
      "score": 12.0,
      "max_score": 18.0,
      "percentage": 66.67,
      "rating": "Good"
    },
    {
      "competency": "Problem Solving",
      "description": "Identifies root causes and proposes solutions",
      "score": 9.0,
      "max_score": 15.0,
      "percentage": 60.0,
      "rating": "Satisfactory"
    }
  ],
  "overall": {
    "total_score": 29.5,
    "total_max_score": 45.0,
    "percentage": 65.56,
    "rating": "Good"
  }
}
```

---

## 9. Security Considerations

### Authentication
- **Current**: Session-based with bcrypt password hashing
- **Recommended for Integration**: JWT tokens or OAuth 2.0

### API Security Best Practices
```python
# API Key Authentication (Header)
Authorization: Bearer <api_key>

# Rate Limiting
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1705330800

# Input Validation
- Sanitize all Excel uploads
- Validate JSON payloads
- Escape user inputs before AI processing

# HTTPS Only
- Enforce SSL/TLS in production
- Secure cookie flags: HttpOnly, Secure, SameSite
```

---

## 10. Sample Integration Code

### Python Client Example
```python
import requests
import json

class RolevoClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    def create_user(self, email, password):
        """Create a new user in Rolevo"""
        response = requests.post(
            f'{self.base_url}/api/v1/users',
            headers=self.headers,
            json={'email': email, 'password': password}
        )
        return response.json()
    
    def assign_cluster(self, user_id, cluster_id):
        """Assign user to a cluster"""
        response = requests.post(
            f'{self.base_url}/api/v1/user_cluster/assign',
            headers=self.headers,
            json={'user_id': user_id, 'cluster_id': cluster_id}
        )
        return response.json()
    
    def get_user_progress(self, user_id):
        """Get user's progress across all roleplays"""
        response = requests.get(
            f'{self.base_url}/api/v1/users/{user_id}/progress',
            headers=self.headers
        )
        return response.json()
    
    def download_report(self, play_id, output_path):
        """Download PDF report"""
        response = requests.get(
            f'{self.base_url}/showreport/{play_id}',
            headers=self.headers,
            stream=True
        )
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

# Usage
client = RolevoClient('https://rolevo-app.com', 'your_api_key')
user = client.create_user('newuser@company.com', 'password123')
client.assign_cluster(user['id'], 12)
progress = client.get_user_progress(user['id'])
client.download_report(1523, 'report_1523.pdf')
```

---

## 11. Migration & Data Import

### Bulk User Import CSV Format
```csv
email,password,is_admin,cluster_ids
john@company.com,hashed_password,0,"12,15,18"
admin@company.com,hashed_password,1,""
jane@company.com,hashed_password,0,"12"
```

### Import Script
```python
import csv
import bcrypt
from app.queries import create_user, assign_user_to_cluster

with open('users.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Hash password
        hashed = bcrypt.hashpw(row['password'].encode(), bcrypt.gensalt())
        
        # Create user
        user_id = create_user(row['email'], hashed.decode(), int(row['is_admin']))
        
        # Assign clusters
        if row['cluster_ids']:
            for cluster_id in row['cluster_ids'].split(','):
                assign_user_to_cluster(user_id, int(cluster_id.strip()))
```

---

## 12. Support & Troubleshooting

### Common Integration Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Session expires quickly | SESSION_PERMANENT = False | Set to True in app/__init__.py |
| Scores not showing | cluster_type = 'assessment' | Check cluster type in DB |
| Audio not playing | Missing gTTS library | pip install gTTS |
| Excel parsing error | Wrong sheet name | Verify sheet names: "Main", "Tags" |
| OpenAI API failure | Invalid API key | Check OPENAI_API_KEY in .env |
| Database connection error | Wrong credentials | Verify DB_* variables in .env |

### Debug Mode
```python
# In config.py
DEBUG = True
TESTING = True

# Enable SQL query logging
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

---

## 13. Roadmap & Future Enhancements

### Planned API Features
- [ ] RESTful API with Swagger documentation
- [ ] Webhook support for real-time events
- [ ] GraphQL endpoint for flexible queries
- [ ] OAuth 2.0 / SAML SSO integration
- [ ] Real-time WebSocket for live scoring updates
- [ ] Bulk import/export APIs
- [ ] Advanced analytics endpoints

### Integration Requests
Contact the Rolevo team to request:
- Custom API endpoints
- Specific data format transformations
- Dedicated integration support
- White-label deployment

---

## Contact & Support

**Technical Contact**: [Your Email]  
**Documentation**: [GitHub/Wiki URL]  
**API Status**: [Status Page URL]

---

**Version**: 1.0  
**Last Updated**: December 23, 2025
