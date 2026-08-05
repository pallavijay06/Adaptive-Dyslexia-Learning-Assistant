# Dashboard API Response Structure - Updated

## New Top-Level Sections

The dashboard API response now includes four new sections that expose all missing learner metrics:

### 1. `learner_profile` ← NEW

Exposes learner's profile characteristics and adaptive profile:

```json
{
  "learner_profile": {
    "teaching_style": "Very Simple, Step-by-Step, Many Examples" | null,
    "preferred_learning_mode": "Audio Learning" | "Visual Learning" | "Simplified Notes" | null,
    "learning_strategy": "Audio Learning" | "Visual Learning" | "Simplified Notes" | null,
    "confidence_level": 0.75,
    "comprehension_level": "Advanced" | "Intermediate" | "Beginner" | null
  }
}
```

**Field Details:**
- `teaching_style` - Computed from Master Decision Engine based on learner's comprehension level and needs
- `preferred_learning_mode` - Retrieved from stored learner profile
- `learning_strategy` - Computed from Learning Strategy Engine based on effectiveness scores and behaviour analytics
- `confidence_level` - Learner's self-reported confidence (0-1 scale)
- `comprehension_level` - Classification of learner's understanding level

---

### 2. `learning_performance` ← NEW

Exposes all performance metrics related to learning outcomes:

```json
{
  "learning_performance": {
    "conceptual_answer_score": 75.5,
    "learning_support_score": 82.0,
    "response_efficiency_score": 88.3,
    "quiz_accuracy_score": 78.0,
    "comprehension_score": 79.5,
    "first_attempt_score": 71.2
  }
}
```

**Field Details:**
- `conceptual_answer_score` - Average score on short-answer conceptual questions
- `learning_support_score` - Measure of independence (higher = less dependent on support)
- `response_efficiency_score` - How quickly learner responds to questions
- `quiz_accuracy_score` - Percentage accuracy across all quizzes (previously exposed as `progress.quiz_accuracy`)
- `comprehension_score` - Weighted overall comprehension metric
- `first_attempt_score` - Percentage of questions answered correctly on first attempt

---

### 3. `learning_behaviour` ← NEW

Exposes all behaviour analytics metrics:

```json
{
  "learning_behaviour": {
    "behaviour_analytics_score": 72.5,
    "mode_engagement_score": 68.0,
    "mode_retention_score": 81.3
  }
}
```

**Field Details:**
- `behaviour_analytics_score` - Overall learning behaviour analytics (weighted average of engagement, switching, utilization, improvement, retention)
- `mode_engagement_score` - How actively the learner engages with each learning mode
- `mode_retention_score` - How well the learner retains knowledge across mode switches

---

### 4. `adaptive_intelligence` ← NEW

Exposes adaptive learning path recommendations:

```json
{
  "adaptive_intelligence": {
    "recommended_learning_path": [
      {
        "step": 1,
        "action": "revision",
        "revision_topics": ["Quadratic Equations", "Factorization"]
      },
      {
        "step": 2,
        "action": "learning_mode",
        "mode": "Visual Learning"
      },
      {
        "step": 3,
        "action": "quiz",
        "quiz_length": 8,
        "focus_concepts": ["Quadratic Equations", "Factorization"]
      },
      {
        "step": 4,
        "action": "ai_tutor",
        "enabled": true
      }
    ] | null
  }
}
```

**Field Details:**
- `recommended_learning_path` - Ordered sequence of learning steps generated from Master Decision Engine
- Each step includes:
  - `step` - Sequential step number
  - `action` - Type of step (revision, learning_mode, quiz, ai_tutor, stem_support, extra_examples)
  - Additional fields based on action type (mode, concepts, quiz_length, focus_concepts, etc.)

---

## Existing Sections (Preserved)

The following existing sections remain unchanged:

```json
{
  "overview": { ... },      // Student demographics and activity overview
  "progress": { ... },      // Aggregate progress metrics
  "concept_mastery": [ ... ],  // Concept mastery details
  "weak_concepts": [ ... ], // Weak concept highlights
  "learning_mode_usage": [ ... ],  // Mode usage statistics
  "study_activity": { ... },  // Daily/weekly/monthly study time
  "quiz_performance": { ... },  // Quiz statistics
  "badges": [ ... ],        // Achievement badges
  "timeline": [ ... ],      // Activity timeline
  "insights": [ ... ],      // AI-generated insights
  "recommendations": [ ... ],  // Personalized recommendations
  "learning_mode_effectiveness": { ... },  // Mode effectiveness analysis
  "difficulty_profile": { ... },  // Difficulty profile data
  "learning_progress_analytics": { ... }  // Learning progress analytics
}
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│         Frontend Dashboard (Pure Presentation)                   │
│  Displays metrics from new sections without recalculation        │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │
                              │ GET /dashboard/<user_id>
                              │
                              │ Returns JSON with 4 new sections
                              │
┌─────────────────────────────────────────────────────────────────┐
│         Dashboard Service (Orchestration Layer)                   │
│         services/progress_dashboard_service.py                    │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐                      │
│  │ Profile Mapping  │  │ On-Demand Compute│                      │
│  │                  │  │                  │                      │
│  │ • confidence     │  │ • teaching_style │                      │
│  │ • comprehension  │  │ • learning_strat │                      │
│  │ • support_score  │  │ • learning_path  │                      │
│  │ • engagement     │  │                  │                      │
│  │ • retention      │  │                  │                      │
│  └──────────────────┘  └──────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
       │                           │
       │                           │
       ▼                           ▼
┌──────────────────┐    ┌──────────────────────────────────────┐
│ Learner Profile  │    │ Adaptive Decision Engines              │
│ (Database)       │    │                                        │
│                  │    │ • Master Decision Engine              │
│ • confidence     │    │ • Learning Strategy Engine            │
│ • comprehension  │    │                                        │
│ • support_score  │    │ Input: User behavior & history        │
│ • engagement     │    │ Output: Teaching style, strategy,     │
│ • retention      │    │         learning path                 │
└──────────────────┘    └──────────────────────────────────────┘
       ▲                           ▲
       │                           │
       └─────────────────┬─────────┘
                         │
                         │
       ┌─────────────────┴──────────────────┐
       │  Specialized Backend Services       │
       │                                     │
       │ • Learner Model Service             │
       │ • Learning Behaviour Analytics      │
       │ • Difficulty Profile Service        │
       │ • Mode Effectiveness Service        │
       │ • And 20+ other specialized         │
       │   computation engines               │
       └─────────────────────────────────────┘
```

---

## Example API Response (Snippet)

```json
{
  "success": true,
  "dashboard": {
    "overview": { ... },
    
    "learner_profile": {
      "teaching_style": "Intermediate, Worked Examples, Step-by-Step",
      "preferred_learning_mode": "Audio Learning",
      "learning_strategy": "Visual Learning",
      "confidence_level": 0.68,
      "comprehension_level": "Intermediate"
    },
    
    "learning_performance": {
      "conceptual_answer_score": 72.3,
      "learning_support_score": 79.1,
      "response_efficiency_score": 85.6,
      "quiz_accuracy_score": 76.5,
      "comprehension_score": 77.8,
      "first_attempt_score": 69.2
    },
    
    "learning_behaviour": {
      "behaviour_analytics_score": 71.2,
      "mode_engagement_score": 66.8,
      "mode_retention_score": 79.5
    },
    
    "adaptive_intelligence": {
      "recommended_learning_path": [
        {
          "step": 1,
          "action": "learning_mode",
          "mode": "Audio Learning"
        },
        {
          "step": 2,
          "action": "quiz",
          "quiz_length": 8,
          "focus_concepts": ["Quadratic Equations", "Polynomial Division"]
        },
        {
          "step": 3,
          "action": "ai_tutor",
          "enabled": true
        }
      ]
    },
    
    "progress": { ... },
    "quiz_performance": { ... },
    ... other sections ...
  }
}
```

---

## Backward Compatibility

✓ **All existing fields preserved**
✓ **Existing sections unchanged**
✓ **Endpoint signature unchanged**: `GET /dashboard/<int:user_id>`
✓ **No breaking changes for existing frontend consumers**

New sections can be safely added to the frontend without affecting existing functionality.

---

## Frontend Usage Example

```javascript
// Fetch dashboard data
const response = await fetch(`/dashboard/${userId}`);
const dashboard = await response.json();

// Access new metrics
const teachingStyle = dashboard.dashboard.learner_profile.teaching_style;
const supportScore = dashboard.dashboard.learning_performance.learning_support_score;
const engagementScore = dashboard.dashboard.learning_behaviour.mode_engagement_score;
const recommendedPath = dashboard.dashboard.adaptive_intelligence.recommended_learning_path;

// Render components
renderLearnerProfile(dashboard.dashboard.learner_profile);
renderPerformanceMetrics(dashboard.dashboard.learning_performance);
renderBehaviourAnalytics(dashboard.dashboard.learning_behaviour);
renderAdaptivePathway(dashboard.dashboard.adaptive_intelligence.recommended_learning_path);
```
