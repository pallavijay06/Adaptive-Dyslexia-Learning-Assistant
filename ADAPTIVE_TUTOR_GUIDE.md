"""
ADAPTIVE AI TUTOR - IMPLEMENTATION GUIDE

This document explains the Adaptive AI Tutor system that has been integrated into the 
Dyslexic Learning Assistant to provide personalized, adaptive learning experiences.

========================================
## SYSTEM OVERVIEW
========================================

The Adaptive AI Tutor system automatically learns from each student's behavior and 
adapts its teaching style accordingly. It tracks learning patterns, identifies weak 
concepts, and provides personalized recommendations.

### Key Components

1. **learner_profile_service.py** - Manages learner profiles
   - Initializes profiles from user registration data
   - Updates profile based on learning behavior
   - Tracks study time, topics, confidence levels, etc.

2. **behavior_tracker.py** - Tracks learner interactions
   - Records questions asked
   - Tracks quiz attempts and scores
   - Monitors document uploads
   - Identifies weak and strong concepts
   - Tracks learning mode preferences

3. **recommendation_engine.py** - Generates personalized recommendations
   - Recommends appropriate learning modes
   - Suggests practice quizzes on weak areas
   - Recommends concept review
   - Adjusts explanation complexity
   - Generates personalized greetings

4. **adaptive_tutor.py** - Core orchestrator service
   - Initializes adaptive context for responses
   - Tracks interactions
   - Generates adaptive system prompts for the LLM
   - Manages all recommendations

5. **chat_routes.py** (updated) - Backend API endpoints
   - /chat - Main chat endpoint (now with adaptive support)
   - /adaptive/record-quiz - Record quiz attempts
   - /adaptive/track-mode - Track learning mode usage
   - /adaptive/record-concept - Record concept questions
   - /adaptive/track-document - Track document uploads
   - /adaptive/profile/<user_id> - Get learner profile summary
   - /adaptive/recommendations/<user_id> - Get recommendations
   - /adaptive/initialize-profile - Initialize new profiles

========================================
## DATABASE SCHEMA
========================================

### New Tables

1. **learner_profile**
   - Stores comprehensive learner profile information
   - total_study_time_minutes, documents_uploaded, unique_topics_studied
   - average_quiz_score, confidence_level, explanation_complexity
   - Preferences: prefers_examples, prefers_analogies, prefers_bullet_points

2. **learning_history**
   - Tracks every learning activity (questions, quizzes, uploads, etc.)
   - activity_type: 'question', 'quiz', 'upload', 'read', 'listen', 'visual'
   - topic: The topic being studied (optional)
   - duration_seconds: Time spent on activity

3. **topic_progress**
   - Tracks progress on specific topics
   - questions_asked, quiz_attempts, best_score
   - mastery_level (0-1 scale), times_studied
   - is_weak_area (mastery < 60%), is_strong_area (mastery > 85%)

4. **concept_mastery**
   - Tracks mastery of individual concepts within topics
   - times_asked, times_answered_correctly, mastery_percentage
   - is_frequently_asked (asked 3+ times), is_frequently_missed

5. **adaptive_preferences**
   - Learns conversation preferences from user behavior
   - preferred_explanation_complexity, prefers_visual_aids, prefers_audio
   - prefers_bullet_points, prefers_short_sentences, prefers_analogies
   - avg_successful_response_length, response_time_patience

========================================
## HOW IT WORKS
========================================

### 1. User Registration
When a user registers, their profile is initialized based on:
- Age/Grade → Determines initial explanation complexity (simple/medium/advanced)
- Dyslexia Status → Enables accessibility features (bullet points, shorter sentences)
- Preferences → Set initial learning mode preferences

### 2. Interaction Tracking
Every interaction is automatically tracked:
- User asks a question → BehaviorTracker records it
- Quiz attempt → Mastery levels updated
- Mode usage → Preference patterns identified
- Document upload → Engagement tracked

### 3. Profile Updates
Based on interactions:
- Quiz scores → Confidence level adjusted
- Concept accuracy → Mastery percentages calculated
- Mode usage patterns → Preferred learning mode updated
- Study time → Learning frequency inferred (daily/weekly/occasional)

### 4. Adaptive Responses
Before generating responses, the system:
- Prepares adaptive context (learner preferences, weak concepts, etc.)
- Generates an adapted system prompt for the LLM
- Includes recommendations (practice quizzes, mode changes, etc.)

### 5. Recommendations
The system provides personalized recommendations:
- Mode Suggestions: "You often use Visual Learning - want a diagram?"
- Practice Opportunities: "Let's practice Newton's Laws where you scored 45%"
- Difficulty Adjustments: "Your confidence is high - ready for harder questions?"
- Progress Milestones: "Great! You've mastered 3 topics!"

========================================
## FRONTEND INTEGRATION GUIDE
========================================

### 1. Initialize Learner Profile (After Login)

```python
import requests

# After user logs in
user_id = st.session_state.current_user_id
response = requests.post(
    "http://localhost:5000/adaptive/initialize-profile",
    json={"user_id": user_id}
)
profile_data = response.json()
st.session_state.learner_profile = profile_data['profile']
```

### 2. Send User ID with Chat Requests

```python
# In chat interface
if st.session_state.authenticated:
    user_id = st.session_state.current_user_id
else:
    user_id = None

response = requests.post(
    "http://localhost:5000/chat",
    json={
        "message": user_message,
        "document_id": doc_id,
        "document_text": doc_text,
        "user_id": user_id,  # NEW: Pass authenticated user ID
        "topic": extracted_topic,  # OPTIONAL: Include topic context
    }
)

# Response now includes adaptive data
result = response.json()
ai_response = result["response"]
adaptive_data = result.get("adaptive", {})
recommendations = adaptive_data.get("recommendations", [])

# Display recommendations
for rec in recommendations:
    if rec["type"] == "mode_suggestion":
        st.info(rec["message"])
    elif rec["type"] == "practice_suggestion":
        st.warning(rec["message"])
```

### 3. Track Quiz Results

```python
# After quiz is completed
requests.post(
    "http://localhost:5000/adaptive/record-quiz",
    json={
        "user_id": user_id,
        "topic": quiz_topic,
        "score": quiz_score,  # 0-100
        "total_questions": len(quiz_questions),
        "session_id": current_session_id,
    }
)
```

### 4. Track Learning Mode Usage

```python
# When user switches to a learning mode
requests.post(
    "http://localhost:5000/adaptive/track-mode",
    json={
        "user_id": user_id,
        "mode": "Audio",  # or "Visual", "Simplified Notes", "Quiz"
        "session_id": current_session_id,
    }
)
```

### 5. Track Document Uploads

```python
# When user uploads a document
requests.post(
    "http://localhost:5000/adaptive/track-document",
    json={
        "user_id": user_id,
        "session_id": current_session_id,
    }
)
```

### 6. Display Learner Profile and Recommendations

```python
# Display user dashboard
if st.session_state.authenticated:
    response = requests.get(
        f"http://localhost:5000/adaptive/profile/{user_id}"
    )
    profile_data = response.json()
    
    # Display profile
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Study Time", f"{profile_data['profile']['total_study_time_minutes']} min")
        st.metric("Topics Studied", profile_data['profile']['unique_topics_studied'])
    with col2:
        st.metric("Avg Quiz Score", f"{profile_data['profile']['average_quiz_score']:.1f}%")
        st.metric("Confidence Level", f"{profile_data['profile']['confidence_level']:.0%}")
    
    # Get recommendations
    rec_response = requests.get(
        f"http://localhost:5000/adaptive/recommendations/{user_id}"
    )
    rec_data = rec_response.json()
    
    st.info(rec_data['greeting'])
    
    for rec in rec_data['recommendations']:
        if rec['type'] == 'mode_suggestion':
            st.success(rec['text'])
        elif rec['type'] == 'quiz_suggestion':
            st.warning(rec['text'])
```

### 7. Display Adaptive System Prompt

```python
# For debugging/understanding learner adaptation
if st.session_state.authenticated:
    tutor = AdaptiveAITutor(user_id)
    system_prompt = tutor.generate_adaptive_system_prompt()
    with st.expander("Adaptive Tutor Configuration"):
        st.text(system_prompt)
```

========================================
## EXAMPLE: CHAT FLOW WITH ADAPTATION
========================================

1. User asks: "What is photosynthesis?"
   - Request includes user_id, message, and optional topic
   
2. Backend processes:
   - Creates AdaptiveAITutor instance
   - Retrieves learner profile (complexity level, preferences, etc.)
   - Tracks question asked
   - Retrieves any previous questions about photosynthesis
   - Checks if it's a weak area
   
3. Response generation:
   - Gets adaptive system prompt customized for this learner
   - If dyslexic → shorter sentences, bullet points
   - If low confidence → simpler explanation with examples
   - If high confidence → more technical depth
   
4. Recommendations added:
   - If learner prefers visual → "Want to see a diagram?"
   - If previously asked about "chlorophyll" → "Remember chlorophyll?"
   - If score was low on related quiz → "Ready for a practice quiz?"
   
5. Response sent to frontend with:
   - Main AI response
   - Adaptive context
   - Personalized recommendations
   - Updated learner profile snippet

========================================
## METRICS TRACKED
========================================

Per User:
- Total study time (minutes)
- Documents uploaded
- Unique topics studied
- Total questions asked
- Average quiz score
- Preferred learning mode
- Learning frequency (daily/weekly/occasional)
- Confidence level (0-1 scale)

Per Topic:
- Questions asked
- Quiz attempts
- Best score
- Times studied
- Mastery level (0-1 scale)
- Is weak area? (mastery < 60%)
- Is strong area? (mastery > 85%)

Per Concept:
- Times asked
- Times answered correctly
- Mastery percentage
- Is frequently asked? (3+ times)
- Is frequently missed? (3+ attempts, <50% accuracy)

Adaptive Preferences:
- Preferred explanation complexity
- Visual aids preference
- Audio preference
- Bullet points preference
- Short sentences preference
- Analogies preference
- Real-world examples preference
- Average successful response length
- Response time patience

========================================
## ADMIN/ANALYTICS
========================================

### Getting Learner Summary

```python
tutor = AdaptiveAITutor(user_id)
summary = tutor.get_learner_summary()

# Returns:
# {
#     "user_info": {...},
#     "profile": {...},
#     "activity_summary": {...},
#     "recommendations": [...]
# }
```

### Identifying Weak Concepts

```python
weak_concepts = BehaviorTracker.identify_weak_concepts(user_id, "Physics")
# Returns list of concepts with low mastery

strong_concepts = BehaviorTracker.identify_strong_concepts(user_id, "Physics")
# Returns list of concepts with high mastery
```

### Getting Recent Activity

```python
activity_summary = BehaviorTracker.get_recent_activity_summary(user_id)
# Returns:
# {
#     "activity_counts": {...},
#     "topics_studied": [...],
#     "most_studied_topic": "...",
#     "total_activities": 42
# }
```

========================================
## EXISTING FUNCTIONALITY PRESERVED
========================================

✓ Document upload and parsing
✓ RAG-based question answering
✓ Quiz generation and evaluation
✓ Simplified content generation
✓ Visual learning (diagrams, mind maps)
✓ Text-to-speech audio
✓ OCR for images
✓ STEM support
✓ Vocabulary learning

The adaptive tutor ENHANCES these features by:
- Personalizing responses based on learner profile
- Recommending appropriate learning modes
- Tracking what works for each student
- Providing progress insights
- Identifying struggling areas

========================================
## MIGRATION NOTES
========================================

### Backward Compatibility
- Existing users without profiles will get default profiles on first chat
- Anonymous users still work as before
- All existing chat functionality preserved
- No breaking changes to existing APIs

### Database Migration
- New tables are created automatically on first run
- init_db() handles schema creation
- No manual migrations needed

### Testing
- Existing tests still work
- New services are independent modules
- Can be tested separately or integrated

========================================
## FUTURE ENHANCEMENTS
========================================

1. Spaced Repetition: Recommend reviewing concepts at optimal intervals
2. Peer Comparison: Anonymous benchmarking against similar learners
3. Learning Path Recommendation: Suggest optimal topic sequences
4. Predictive Analysis: Predict future struggles based on patterns
5. Multi-Modal Adaptive: Combine results from different modalities
6. Real-time Difficulty Adjustment: Dynamically adjust quiz difficulty
7. Concept Graph: Build knowledge graphs for each learner
8. Export Progress Reports: PDF/email progress reports
9. Parent/Teacher Dashboard: Track progress of multiple students
10. AI Tutor Dialog System: More conversational adaptive responses

========================================
## TROUBLESHOOTING
========================================

### Profile not updating
- Check that user_id is being passed correctly
- Verify database tables were created
- Check for errors in behavior_tracker logs

### Recommendations not appearing
- Check if learner_profile exists
- Verify topic_progress has data
- Review recommendation_engine logic for conditions

### Adaptive responses not personalized
- Verify adaptive_tutor is initialized with correct user_id
- Check that system prompt is being used
- Review llm_router for prompt handling

### Quiz tracking not working
- Verify record-quiz endpoint receives correct parameters
- Check topic_progress table for records
- Review mastery_level calculations

========================================
## SUPPORT & DOCUMENTATION
========================================

For issues or questions:
1. Check the logs: database/logs/ or Flask logs
2. Review database.db tables directly
3. Test individual services in isolation
4. Check that user_id is properly authenticated

Key Files:
- services/adaptive_tutor.py - Main orchestrator
- services/learner_profile_service.py - Profile management
- services/behavior_tracker.py - Interaction tracking
- services/recommendation_engine.py - Recommendations
- backend/chat_routes.py - API endpoints
- database/models.py - Data models
- database/db.py - Database functions
"""
