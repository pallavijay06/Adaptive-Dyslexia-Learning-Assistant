"""
ADAPTIVE AI TUTOR - API REFERENCE

Complete reference for all new and updated endpoints for the Adaptive AI Tutor system.

========================================
## MAIN CHAT ENDPOINT (UPDATED)
========================================

### POST /chat

Enhanced chat endpoint that now supports adaptive tutor functionality.

**Request:**
```json
{
  "message": "What is photosynthesis?",
  "document_id": 123,
  "document_text": "Full document content...",
  "user_id": 5,
  "topic": "Biology"
}
```

**Parameters:**
- `message` (required, string): User's question
- `document_id` (optional, int): ID of the document being studied
- `document_text` (optional, string): Full document content
- `user_id` (optional, int): Authenticated user ID (if not provided, uses anonymous)
- `topic` (optional, string): Topic being discussed (improves adaptation)

**Response:**
```json
{
  "response": "Photosynthesis is the process by which plants...",
  "adaptive": {
    "context": {
      "user_name": "Alice",
      "user_age": 15,
      "user_grade": "10th Grade",
      "is_dyslexic": false,
      "explanation_complexity": "medium",
      "prefers_examples": true,
      "prefers_analogies": true,
      "prefers_bullet_points": false,
      "avg_response_length": 250,
      "confidence_level": 0.75,
      "learning_frequency": "weekly",
      "preferred_mode": "Simplified Notes",
      "topic": "Biology",
      "weak_concepts": ["Chlorophyll", "Light reactions"],
      "strong_concepts": ["Photosystem II"]
    },
    "recommendations": [
      {
        "type": "mode_suggestion",
        "message": "Would you like a Visual explanation?",
        "mode": "Visual"
      }
    ],
    "learner_profile": {
      "explanation_complexity": "medium",
      "preferred_mode": "Simplified Notes",
      "confidence_level": 0.75
    }
  }
}
```

**Status Codes:**
- `200`: Success
- `400`: Missing message or invalid parameters
- `500`: Server error

---

========================================
## QUIZ TRACKING
========================================

### POST /adaptive/record-quiz

Records a quiz attempt and updates learner profile accordingly.

**Request:**
```json
{
  "user_id": 5,
  "topic": "Photosynthesis",
  "score": 78.5,
  "total_questions": 10,
  "session_id": "session-uuid-12345"
}
```

**Parameters:**
- `user_id` (required, int): User ID
- `topic` (required, string): Quiz topic
- `score` (required, float): Score percentage (0-100)
- `total_questions` (required, int): Number of questions in quiz
- `session_id` (optional, string): Current session ID

**Response:**
```json
{
  "success": true,
  "message": "Quiz recorded. Your score: 78.5%",
  "profile_update": {
    "total_study_time_minutes": 245,
    "documents_uploaded": 3,
    "unique_topics_studied": 7,
    "total_questions_asked": 42,
    "average_quiz_score": 72.3,
    "preferred_learning_mode": "Simplified Notes",
    "learning_frequency": "weekly",
    "confidence_level": 0.72,
    "explanation_complexity": "medium"
  }
}
```

**Status Codes:**
- `200`: Success
- `400`: Missing required fields
- `500`: Server error

---

========================================
## MODE TRACKING
========================================

### POST /adaptive/track-mode

Tracks when a learner uses a specific learning mode.

**Request:**
```json
{
  "user_id": 5,
  "mode": "Audio",
  "session_id": "session-uuid-12345"
}
```

**Parameters:**
- `user_id` (required, int): User ID
- `mode` (required, string): Learning mode ("Audio", "Visual", "Simplified Notes", "Quiz")
- `session_id` (optional, string): Current session ID

**Response:**
```json
{
  "success": true,
  "message": "Tracked Audio usage."
}
```

**Status Codes:**
- `200`: Success
- `400`: Missing required fields
- `500`: Server error

---

========================================
## CONCEPT TRACKING
========================================

### POST /adaptive/record-concept

Records a question about a specific concept within a topic.

**Request:**
```json
{
  "user_id": 5,
  "topic": "Physics",
  "concept": "Newton's Laws",
  "is_correct": true
}
```

**Parameters:**
- `user_id` (required, int): User ID
- `topic` (required, string): Topic name
- `concept` (required, string): Specific concept name
- `is_correct` (optional, boolean): Whether the answer was correct (default: false)

**Response:**
```json
{
  "success": true,
  "message": "Concept recorded."
}
```

**Status Codes:**
- `200`: Success
- `400`: Missing required fields
- `500`: Server error

---

========================================
## DOCUMENT TRACKING
========================================

### POST /adaptive/track-document

Tracks when a learner uploads a document.

**Request:**
```json
{
  "user_id": 5,
  "session_id": "session-uuid-12345"
}
```

**Parameters:**
- `user_id` (required, int): User ID
- `session_id` (optional, string): Current session ID

**Response:**
```json
{
  "success": true
}
```

**Status Codes:**
- `200`: Success
- `400`: Missing user_id
- `500`: Server error

---

========================================
## LEARNER PROFILE
========================================

### GET /adaptive/profile/<user_id>

Retrieves the complete learner profile summary for a user.

**Request:**
```
GET /adaptive/profile/5
```

**Response:**
```json
{
  "user_info": {
    "name": "Alice Chen",
    "age": 15,
    "grade": "10th Grade",
    "institution": "Central High School",
    "dyslexia_status": "No"
  },
  "profile": {
    "total_study_time_minutes": 245,
    "documents_uploaded": 3,
    "unique_topics_studied": 7,
    "total_questions_asked": 42,
    "average_quiz_score": 72.3,
    "preferred_learning_mode": "Simplified Notes",
    "learning_frequency": "weekly",
    "confidence_level": 0.72,
    "explanation_complexity": "medium",
    "prefers_examples": true,
    "prefers_analogies": true,
    "prefers_bullet_points": false,
    "avg_response_length_preference": 250
  },
  "activity_summary": {
    "activity_counts": {
      "question": 42,
      "quiz": 8,
      "upload": 3,
      "audio": 5,
      "visual": 12
    },
    "topics_studied": ["Biology", "Physics", "Chemistry"],
    "most_studied_topic": "Biology",
    "total_activities": 70
  },
  "recommendations": [
    {
      "type": "mode_suggestion",
      "title": "Suggested Learning Mode",
      "text": "Based on your preferences, try learning with Visual Learning!",
      "mode": "Visual"
    }
  ]
}
```

**Status Codes:**
- `200`: Success
- `500`: Server error

---

========================================
## RECOMMENDATIONS
========================================

### GET /adaptive/recommendations/<user_id>

Gets personalized recommendations for a learner.

**Request:**
```
GET /adaptive/recommendations/5
```

**Response:**
```json
{
  "greeting": "Welcome back, Alice! You've studied 7 topics so far. Let's continue learning!",
  "recommendations": [
    {
      "type": "mode_suggestion",
      "title": "Suggested Learning Mode",
      "text": "Based on your preferences, try learning with Visual Learning!",
      "mode": "Visual"
    },
    {
      "type": "quiz_suggestion",
      "title": "Practice Opportunity",
      "text": "Let's practice Photosynthesis! You're at 45% mastery.",
      "topic": "Photosynthesis"
    },
    {
      "type": "frequency_suggestion",
      "title": "Learning Frequency",
      "text": "You've made great progress! Studying regularly will help you learn faster."
    },
    {
      "type": "milestone",
      "title": "Great Progress!",
      "text": "You've mastered 2 topic(s)! Keep it up!",
      "topics": ["Biology Basics", "Cellular Transport"]
    }
  ]
}
```

**Status Codes:**
- `200`: Success
- `500`: Server error

---

========================================
## PROFILE INITIALIZATION
========================================

### POST /adaptive/initialize-profile

Initializes a learner profile for a new user (called after registration/login).

**Request:**
```json
{
  "user_id": 5
}
```

**Parameters:**
- `user_id` (required, int): User ID to initialize profile for

**Response:**
```json
{
  "success": true,
  "profile": {
    "total_study_time_minutes": 0,
    "documents_uploaded": 0,
    "unique_topics_studied": 0,
    "total_questions_asked": 0,
    "average_quiz_score": 0.0,
    "preferred_learning_mode": "Simplified Notes",
    "learning_frequency": "occasional",
    "confidence_level": 0.5,
    "explanation_complexity": "medium",
    "prefers_examples": true,
    "prefers_analogies": true,
    "prefers_bullet_points": false,
    "avg_response_length_preference": 250
  }
}
```

**Status Codes:**
- `200`: Success
- `400`: Invalid user_id
- `404`: User not found
- `500`: Server error

---

========================================
## DATA MODELS
========================================

### LearnerProfile

```python
{
    "id": int,
    "user_id": int,
    "total_study_time_minutes": int,
    "documents_uploaded": int,
    "unique_topics_studied": int,
    "total_questions_asked": int,
    "average_quiz_score": float,  # 0-100
    "preferred_learning_mode": str,  # "Simplified Notes", "Audio", "Visual", "Quiz"
    "learning_frequency": str,  # "daily", "weekly", "occasional"
    "confidence_level": float,  # 0-1
    "explanation_complexity": str,  # "simple", "medium", "advanced"
    "prefers_examples": bool,
    "prefers_analogies": bool,
    "prefers_bullet_points": bool,
    "avg_response_length_preference": int,  # words
    "last_updated": datetime,
    "created_at": datetime
}
```

### TopicProgress

```python
{
    "id": int,
    "user_id": int,
    "topic": str,
    "questions_asked": int,
    "quiz_attempts": int,
    "best_score": float,  # 0-100
    "last_studied": datetime,
    "times_studied": int,
    "mastery_level": float,  # 0-1
    "is_weak_area": bool,  # mastery < 60%
    "is_strong_area": bool  # mastery > 85%
}
```

### ConceptMastery

```python
{
    "id": int,
    "user_id": int,
    "topic": str,
    "concept": str,
    "times_asked": int,
    "times_answered_correctly": int,
    "mastery_percentage": float,  # 0-100
    "last_asked": datetime,
    "is_frequently_asked": bool,  # asked 3+ times
    "is_frequently_missed": bool  # 3+ attempts, <50% accuracy
}
```

### AdaptivePreferences

```python
{
    "id": int,
    "user_id": int,
    "preferred_explanation_complexity": str,  # "simple", "medium", "advanced"
    "prefers_visual_aids": bool,
    "prefers_audio": bool,
    "prefers_bullet_points": bool,
    "prefers_short_sentences": bool,
    "prefers_analogies": bool,
    "prefers_real_world_examples": bool,
    "avg_successful_response_length": int,
    "response_time_patience": int,  # seconds
    "quiz_difficulty_preference": str,  # "easy", "medium", "hard", "adaptive"
    "last_updated": datetime,
    "created_at": datetime
}
```

---

========================================
## ERROR RESPONSES
========================================

### Standard Error Response

```json
{
  "error": "Error message explaining what went wrong"
}
```

### Common Error Codes

- `400 Bad Request`: Missing required fields or invalid parameters
- `404 Not Found`: User or resource not found
- `500 Internal Server Error`: Unexpected server error

### Example Error Response

```json
{
  "error": "Missing required fields: user_id, topic, score."
}
```

---

========================================
## RATE LIMITING
========================================

No rate limiting is currently implemented. 
Recommended limits for production:
- 100 requests per minute per IP
- 1000 requests per day per user

---

========================================
## AUTHENTICATION
========================================

All endpoints that accept `user_id` should verify the user is authenticated.

Current implementation:
- User IDs are passed from frontend (Streamlit session state)
- No token-based authentication in place
- Anonymous users default to user_id lookup by email

**Recommended:** Implement JWT or session token validation before accepting requests.

---

========================================
## VERSIONING
========================================

Current API version: 1.0
- All endpoints at: `/`
- No version prefix currently used
- Future versions may use: `/v2/adaptive/...`

---

========================================
## TESTING WITH CURL
========================================

### Test Chat Endpoint

```bash
curl -X POST http://localhost:5000/chat \\
  -H "Content-Type: application/json" \\
  -d '{
    "message": "What is DNA?",
    "user_id": 5,
    "topic": "Biology"
  }'
```

### Test Quiz Recording

```bash
curl -X POST http://localhost:5000/adaptive/record-quiz \\
  -H "Content-Type: application/json" \\
  -d '{
    "user_id": 5,
    "topic": "Biology",
    "score": 85,
    "total_questions": 10
  }'
```

### Test Profile Retrieval

```bash
curl -X GET http://localhost:5000/adaptive/profile/5
```

### Test Recommendations

```bash
curl -X GET http://localhost:5000/adaptive/recommendations/5
```

---

========================================
## WEBHOOK SUPPORT
========================================

Not currently implemented. Future enhancement:
- Send progress notifications to external services
- Integrate with third-party LMS systems
- Send email/SMS alerts to parents/teachers

---

========================================
## BACKWARDS COMPATIBILITY
========================================

✓ All existing endpoints remain unchanged
✓ New fields are optional in responses
✓ Anonymous users still supported
✓ No breaking changes to existing API

---

========================================
## CHANGELOG
========================================

### Version 1.0 (Current)
- Added 7 new endpoints for adaptive tutor
- Enhanced /chat endpoint with adaptive support
- Created 5 new database tables
- Implemented learner profile management
- Implemented behavior tracking
- Implemented recommendation engine

### Planned for Future
- Version 2.0: Token-based authentication
- Version 2.1: WebSocket support for real-time updates
- Version 3.0: Multi-user collaboration features
"""
