"""
STREAMLIT FRONTEND INTEGRATION - QUICK START

This guide explains how to integrate the Adaptive AI Tutor into the Streamlit frontend.

========================================
## QUICK INTEGRATION CHECKLIST
========================================

□ 1. Add user_id to chat requests
□ 2. Display adaptive recommendations
□ 3. Track quiz attempts
□ 4. Track mode usage
□ 5. Track document uploads
□ 6. Display learner profile in dashboard
□ 7. Show personalized greetings
□ 8. Test end-to-end flow

========================================
## STEP-BY-STEP INTEGRATION
========================================

### Step 1: Update Chat Requests (In app.py or chat component)

BEFORE:
```python
response = requests.post(
    "http://localhost:5000/chat",
    json={
        "message": user_message,
        "document_id": document_id,
        "document_text": document_text,
    }
)
result = response.json()
ai_response = result["response"]
```

AFTER:
```python
# Add user_id to request
payload = {
    "message": user_message,
    "document_id": document_id,
    "document_text": document_text,
}

# Include authenticated user ID if available
if st.session_state.get("authenticated") and st.session_state.get("current_user_id"):
    payload["user_id"] = st.session_state.current_user_id

# Optional: include topic context for better adaptation
if "current_topic" in st.session_state:
    payload["topic"] = st.session_state.current_topic

response = requests.post(
    "http://localhost:5000/chat",
    json=payload
)
result = response.json()
ai_response = result["response"]

# NEW: Extract adaptive data
adaptive_data = result.get("adaptive", {})
recommendations = adaptive_data.get("recommendations", [])
learner_profile = adaptive_data.get("learner_profile", {})

# Display recommendations
if recommendations:
    st.write("---")
    st.subheader("💡 Personalized Tips")
    for rec in recommendations:
        if rec.get("type") == "mode_suggestion":
            st.info(f"📚 {rec.get('message', '')}")
        elif rec.get("type") == "practice_suggestion":
            st.warning(f"🎯 {rec.get('message', '')}")
        elif rec.get("type") == "adjustment_suggestion":
            st.success(f"✨ {rec.get('message', '')}")
```

### Step 2: Track Quiz Attempts (In quiz component)

```python
# After quiz is completed and scored
if st.session_state.get("current_user_id"):
    try:
        requests.post(
            "http://localhost:5000/adaptive/record-quiz",
            json={
                "user_id": st.session_state.current_user_id,
                "topic": quiz_topic,
                "score": quiz_score,  # 0-100
                "total_questions": total_questions,
                "session_id": st.session_state.get("session_id"),
            }
        )
        st.success(f"Quiz recorded! Your score: {quiz_score}%")
    except Exception as e:
        logger.error(f"Failed to record quiz: {e}")
```

### Step 3: Track Learning Mode Usage (In mode switcher)

```python
# When user selects a learning mode
if selected_mode != st.session_state.get("selected_learning_mode"):
    st.session_state.selected_learning_mode = selected_mode
    
    # Track mode usage
    if st.session_state.get("current_user_id"):
        try:
            requests.post(
                "http://localhost:5000/adaptive/track-mode",
                json={
                    "user_id": st.session_state.current_user_id,
                    "mode": selected_mode,
                    "session_id": st.session_state.get("session_id"),
                }
            )
        except Exception as e:
            logger.error(f"Failed to track mode: {e}")
    
    # Render the selected mode...
```

### Step 4: Track Document Uploads

```python
# In document upload section
if uploaded_file:
    try:
        # ... existing upload logic ...
        
        # Track upload for adaptive system
        if st.session_state.get("current_user_id"):
            requests.post(
                "http://localhost:5000/adaptive/track-document",
                json={
                    "user_id": st.session_state.current_user_id,
                    "session_id": st.session_state.get("session_id"),
                }
            )
    except Exception as e:
        logger.error(f"Failed to track upload: {e}")
```

### Step 5: Initialize Learner Profile (After Login)

```python
# In _handle_login() function
def _handle_login(email: str, password: str) -> bool:
    """Authenticate the user and initialize session state."""
    # ... existing auth logic ...
    
    st.session_state.current_user_id = user.id
    st.session_state.current_user_name = user.name
    st.session_state.login_timestamp = datetime.utcnow()
    st.session_state.authenticated = True
    
    # NEW: Initialize adaptive tutor profile
    try:
        requests.post(
            "http://localhost:5000/adaptive/initialize-profile",
            json={"user_id": user.id}
        )
        logger.info(f"Initialized adaptive profile for user {user.id}")
    except Exception as e:
        logger.error(f"Failed to initialize profile: {e}")
    
    st.success(f"Welcome back, {user.name}!")
    st.rerun()
    return True
```

### Step 6: Display Learner Dashboard

```python
# In a new dashboard tab/section
if st.session_state.get("authenticated"):
    st.header("📊 Your Learning Dashboard")
    
    # Get profile data
    try:
        response = requests.get(
            f"http://localhost:5000/adaptive/profile/{st.session_state.current_user_id}"
        )
        profile_data = response.json()
        profile = profile_data.get("profile", {})
        
        # Display key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "📚 Topics Studied",
                profile.get("unique_topics_studied", 0)
            )
        
        with col2:
            st.metric(
                "⏱️ Study Time",
                f"{profile.get('total_study_time_minutes', 0)} min"
            )
        
        with col3:
            st.metric(
                "📈 Avg Quiz Score",
                f"{profile.get('average_quiz_score', 0):.1f}%"
            )
        
        with col4:
            confidence = profile.get('confidence_level', 0)
            confidence_pct = f"{confidence * 100:.0f}%"
            st.metric("💪 Confidence", confidence_pct)
        
        # Display recommendations
        rec_response = requests.get(
            f"http://localhost:5000/adaptive/recommendations/{st.session_state.current_user_id}"
        )
        rec_data = rec_response.json()
        
        # Show greeting
        st.info(rec_data.get("greeting", ""))
        
        # Show recommendations
        recommendations = rec_data.get("recommendations", [])
        if recommendations:
            st.subheader("🎯 Your Next Steps")
            for rec in recommendations:
                rec_type = rec.get("type", "")
                if rec_type == "mode_suggestion":
                    st.success(f"📚 {rec.get('title', '')}: {rec.get('text', '')}")
                elif rec_type == "quiz_suggestion":
                    st.warning(f"🎯 {rec.get('title', '')}: {rec.get('text', '')}")
                elif rec_type == "milestone":
                    st.success(f"⭐ {rec.get('title', '')}: {rec.get('text', '')}")
                else:
                    st.info(f"💡 {rec.get('title', '')}: {rec.get('text', '')}")
        
        # Display profile info
        with st.expander("📋 Detailed Profile"):
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Learning Preferences**")
                st.write(f"- Preferred Mode: {profile.get('preferred_learning_mode', 'N/A')}")
                st.write(f"- Learning Frequency: {profile.get('learning_frequency', 'N/A')}")
                st.write(f"- Explanation Level: {profile.get('explanation_complexity', 'N/A')}")
            with col2:
                st.write("**Style Preferences**")
                st.write(f"- Prefers Examples: {'✓' if profile.get('prefers_examples') else '✗'}")
                st.write(f"- Prefers Analogies: {'✓' if profile.get('prefers_analogies') else '✗'}")
                st.write(f"- Prefers Bullet Points: {'✓' if profile.get('prefers_bullet_points') else '✗'}")
                st.write(f"- Avg Response Length: {profile.get('avg_response_length_preference', 0)} words")
        
    except Exception as e:
        st.error(f"Could not load dashboard: {e}")
        logger.error(f"Dashboard error: {e}")
```

### Step 7: Add Personalized Greeting

```python
# At the top of the main chat interface
if st.session_state.get("authenticated"):
    try:
        response = requests.get(
            f"http://localhost:5000/adaptive/recommendations/{st.session_state.current_user_id}"
        )
        greeting = response.json().get("greeting", "")
        st.info(f"👋 {greeting}")
    except Exception as e:
        logger.error(f"Failed to get greeting: {e}")
```

### Step 8: Create Session Tracking

```python
# At the start of app initialization
if st.session_state.get("authenticated") and not st.session_state.get("session_id"):
    # Generate a unique session ID for this learning session
    import uuid
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.session_start_time = datetime.utcnow()
```

========================================
## EXAMPLE: COMPLETE CHAT COMPONENT
========================================

```python
def render_chat_interface():
    \"\"\"Render the adaptive chat interface.\"\"\"
    st.header("💬 Ask Your AI Tutor")
    
    # Display personalized greeting
    if st.session_state.get("authenticated"):
        try:
            response = requests.get(
                f"http://localhost:5000/adaptive/recommendations/{st.session_state.current_user_id}"
            )
            greeting = response.json().get("greeting", "")
            st.info(f"👋 {greeting}")
        except Exception as e:
            logger.error(f"Failed to get greeting: {e}")
    
    # Display chat history
    for message in st.session_state.get("chat_history", []):
        if message["role"] == "user":
            with st.chat_message("user"):
                st.write(message["content"])
        else:
            with st.chat_message("assistant"):
                st.write(message["content"])
                
                # Display recommendations if available
                if "recommendations" in message:
                    with st.expander("💡 Tips"):
                        for rec in message["recommendations"]:
                            st.info(rec.get("message", ""))
    
    # Chat input
    user_message = st.chat_input("Ask me anything about your learning material...")
    
    if user_message:
        # Add user message to history
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Get AI response with adaptation
        try:
            payload = {
                "message": user_message,
                "document_id": st.session_state.get("document_record", {}).get("id"),
                "document_text": st.session_state.get("document_text"),
            }
            
            if st.session_state.get("authenticated"):
                payload["user_id"] = st.session_state.current_user_id
                payload["topic"] = st.session_state.get("current_topic")
            
            response = requests.post("http://localhost:5000/chat", json=payload)
            result = response.json()
            
            ai_response = result["response"]
            adaptive_data = result.get("adaptive", {})
            recommendations = adaptive_data.get("recommendations", [])
            
            # Add to history
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": ai_response,
                "recommendations": recommendations
            })
            
            st.rerun()
        
        except Exception as e:
            st.error(f"Error: {e}")
            logger.error(f"Chat error: {e}")
```

========================================
## TESTING CHECKLIST
========================================

□ User can log in
□ Learner profile is initialized after login
□ Chat requests include user_id
□ Chat responses include adaptive recommendations
□ Quiz attempts are recorded and update profile
□ Mode usage is tracked when user switches modes
□ Document uploads are tracked
□ Dashboard shows updated metrics
□ Personalized greeting displays
□ Recommendations appear based on behavior

========================================
## DEBUGGING TIPS
========================================

1. **Check requests are being sent:**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Verify user_id in requests:**
   ```python
   st.write(f"Current User ID: {st.session_state.current_user_id}")
   ```

3. **Check backend logs:**
   - Look at Flask app logs for errors
   - Check database.db for tables
   - Query tables directly to verify data

4. **Test endpoints directly:**
   ```bash
   curl -X POST http://localhost:5000/chat \\
     -H "Content-Type: application/json" \\
     -d '{"message": "Hello", "user_id": 1}'
   ```

5. **Monitor database:**
   ```python
   import sqlite3
   conn = sqlite3.connect("data.sqlite")
   cursor = conn.cursor()
   cursor.execute("SELECT * FROM learner_profile LIMIT 5")
   ```

========================================
## NEXT STEPS
========================================

1. Implement the changes above in your Streamlit app
2. Test with a logged-in user
3. Monitor database to verify data is being stored
4. Adjust UI/UX based on recommendations display
5. Gather feedback from users
6. Iterate on adaptation logic

========================================
## SUPPORT
========================================

For issues:
1. Check ADAPTIVE_TUTOR_GUIDE.md for architecture details
2. Review backend/chat_routes.py for endpoint specifications
3. Check services/*.py for implementation details
4. Review database/db.py for database functions
"""
