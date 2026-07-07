# Adaptive Dyslexia Learning Assistant
# UI / UX Specification

---

# 1. UI Philosophy

The application should feel like a modern AI-powered learning platform rather than a traditional document reader.

The interface should be:

- Clean
- Minimal
- Calm
- Accessible
- Distraction-free
- Easy to navigate
- Suitable for students with dyslexia

The user should never feel overwhelmed.

Every screen should focus on one primary action.

---

# 2. Complete User Journey

```

```
Login / Signup

↓

Dashboard

↓

Upload Learning Material

↓

Document Processing

↓

Choose Learning Experience

↓

🌟 Start Personalized Journey

OR

📚 Explore Learning Modes

↓

Learning Session

↓

Progress Dashboard

↓

Continue Learning

```

---

# 3. Login / Signup Screen

## Purpose

Authenticate the user.

## Layout

Centered authentication card.

Application logo.

Application title.

Short welcome message.

Login form.

Signup option.

Forgot password (future scope).

## Primary Actions

- Login
- Signup

## Behaviour

Successful login redirects to Dashboard.

Failed login displays friendly validation message.

---

# 4. Dashboard

## Purpose

The Dashboard is the student's home page.

It should immediately answer:

"What should I do next?"

## Sections

### Welcome Section

Displays:

- Welcome message
- Student name

---

### Upload Section

Large Upload Document button.

Drag & Drop upload area.

Quick upload.

---

### Progress Overview

Displays

- Documents Learned
- Learning Sessions
- Quiz Performance
- Current Progress

---

### Recent Documents

Displays recently uploaded documents.

Each card includes:

- Document name
- Upload date
- Continue button

---

### Quick Actions

Buttons

- Upload New Document
- Continue Learning
- View Progress

---

# 5. Upload Experience

## Purpose

Allow users to upload educational content.

## Flow

User selects file.

↓

Upload begins.

↓

Progress indicator.

↓

Backend processing.

↓

Processing animation.

↓

Processing completed.

↓

Navigate to Learning Selection screen.

---

# 6. Learning Selection Screen

This is the most important decision screen.

It should clearly present two choices.

-------------------------------------------------

🌟 Start Personalized Learning Journey

-------------------------------------------------

Description

A guided learning experience generated specifically for the student.

Primary Button

Start Journey

-------------------------------------------------

📚 Explore Learning Modes

-------------------------------------------------

Description

Choose any learning mode manually.

Primary Button

Explore

The two options should have equal visual importance.

---

# 7. Personalized Learning Journey

Purpose

Guide the learner step-by-step.

The frontend simply renders the Recommended Learning Path returned by the backend.

## Journey Home

Displays

Journey title.

Estimated duration.

Number of steps.

Current recommendation.

Primary button

Start Journey.

---

## Journey Step Screen

Only ONE learning step is displayed.

Information shown:

Step title.

Learning mode.

Description.

Estimated duration.

Reason for recommendation.

Primary action

Start Learning.

---

## During Learning

The selected learning mode opens.

After completion

Display

✓ Step Completed

Completion message.

Next recommended step.

Buttons

Continue Journey

Exit Journey

---

## Journey Complete

Celebration message.

Journey completed.

Summary

- Steps completed
- Total duration
- Completion percentage

Buttons

Return to Dashboard

Explore Learning Modes

---

# 8. Manual Learning

Purpose

Allow students to freely explore learning modes.

Display all available modes as cards.

Each card contains

Icon

Title

Short description

Open button

Available modes

- Simplified Notes
- Audio Learning
- Visual Learning
- Vocabulary
- Quiz
- STEM Support
- AI Tutor

---

# 9. Learning Workspace

Purpose

Display the selected learning mode.

Workspace layout

Document Header

↓

Learning Mode Navigation

↓

Content Area

↓

Action Bar

---

## Header

Displays

Document title.

Current learning mode.

Back button.

---

## Learning Mode Navigation

Tabs

- Notes
- Audio
- Visual
- Vocabulary
- Quiz
- STEM
- AI Tutor

---

## Content Area

Displays backend-generated content.

This area changes depending on the learning mode.

---

## Action Bar

Possible actions

Refresh

Regenerate

Download

Back

---

# 10. Simplified Notes Experience

Display

Readable content.

Short paragraphs.

Proper spacing.

Reading controls.

Possible controls

Increase font

Decrease font

Line spacing

Theme

---

# 11. Audio Learning Experience

Display

Audio player.

Playback controls.

Progress.

Playback speed.

Transcript.

---

# 12. Visual Learning Experience

Display

Visual explanation.

Flowchart.

Concept map.

Diagram.

Zoom controls.

Fullscreen.

---

# 13. Vocabulary Experience

Display

Word list.

Meaning.

Simple explanation.

Example.

Search.

---

# 14. Quiz Experience

Display

Question.

Options.

Progress.

Submit button.

After completion

Display

Score.

Correct answers.

Explanation.

Retry.

---

# 15. STEM Support Experience

Display available STEM tools.

Cards

Formula Explanation

Symbol Explanation

Diagram Explanation

Concept Breakdown

Step-by-Step Solver

Scientific Vocabulary

Only the selected tool is shown at one time.

---

# 16. AI Tutor Experience

Conversation layout.

Chat history.

Input box.

Send button.

Suggested prompts.

Loading animation while AI responds.

---

# 17. Progress Dashboard

Purpose

Visualize learning progress.

Sections

Learning Summary.

Quiz Performance.

Learning Activity.

Journey Progress.

Recent Sessions.

Learning Trends.

---

# 18. Settings

Purpose

Allow users to personalize the interface.

Possible settings

Theme.

Font size.

Dyslexia-friendly font.

Reading spacing.

Audio speed.

---

# 19. Navigation Behaviour

Dashboard

↓

Upload

↓

Learning Selection

↓

Journey OR Manual

↓

Workspace

↓

Progress

↓

Dashboard

The user should never become lost.

Every screen should have a clear way to return.

---

# 20. Empty States

Examples

No documents uploaded.

No progress yet.

No quiz history.

No recent activity.

Each empty state should encourage the next action.

---

# 21. Loading States

Examples

Uploading...

Processing...

Generating Notes...

Creating Quiz...

Preparing Audio...

Loading Journey...

Loading should always provide feedback.

---

# 22. Error States

Examples

Upload failed.

Network unavailable.

AI generation failed.

Session expired.

Errors should explain the problem and provide a retry action.

---

# 23. Accessibility Experience

Support

Keyboard navigation.

Screen readers.

Dyslexia-friendly font.

Adjustable font size.

Adjustable spacing.

High contrast mode.

Responsive layouts.

---

# 24. Mobile Experience

The application should remain fully usable on mobile devices.

Navigation should simplify while preserving all functionality.

No feature should be removed on smaller screens.

---

# 25. Final Experience Goal

The application should make students feel guided rather than overwhelmed.

The Personalized Learning Journey should provide a structured learning path for students who want AI guidance.

The Manual Learning Mode should provide complete freedom for students who prefer exploring independently.

Both experiences should coexist seamlessly while sharing the same backend intelligence.