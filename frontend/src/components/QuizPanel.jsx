import { useRef, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { quizService } from '../services/quizService';

const STATE = { IDLE: 'idle', LOADING: 'loading', ACTIVE: 'active', SUBMITTING: 'submitting', RESULTS: 'results' };

export default function QuizPanel({ documentId, documentName }) {
  const { user } = useAuth();
  const [state, setState] = useState(STATE.IDLE);
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [report, setReport] = useState(null);
  const [hints, setHints] = useState({});
  const [hintLoading, setHintLoading] = useState({});
  const [hintError, setHintError] = useState({});
  const [error, setError] = useState('');

  const startTimesRef = useRef({});
  const userId = user?.id ?? null;

  // ── Generate ──────────────────────────────────────────────────────────────
  const handleGenerate = async () => {
    setError('');
    setState(STATE.LOADING);
    try {
      const data = await quizService.generateQuiz({ documentId, userId, numMcqs: 4, numShortQuestions: 4 });
      if (!data.success) throw new Error(data.error || 'Quiz generation failed.');
      const mcqs = (data.mcqs || []).map((q) => ({ ...q, _type: 'MCQ' }));
      const shorts = (data.short_questions || []).map((q) => ({ ...q, _type: 'Short Answer' }));
      const unified = [...mcqs, ...shorts];
      setQuestions(unified);
      setAnswers(new Array(unified.length).fill(''));
      setCurrentIndex(0);
      setReport(null);
      setHints({});
      setHintLoading({});
      setHintError({});
      startTimesRef.current = {};
      setState(STATE.ACTIVE);
    } catch (err) {
      setError(err.message || 'Could not generate quiz.');
      setState(STATE.IDLE);
    }
  };

  // ── Navigation ────────────────────────────────────────────────────────────
  const goTo = (index) => {
    if (startTimesRef.current[index] === undefined) startTimesRef.current[index] = Date.now();
    setCurrentIndex(index);
  };

  if (startTimesRef.current[currentIndex] === undefined) {
    startTimesRef.current[currentIndex] = Date.now();
  }

  // ── Answer change ─────────────────────────────────────────────────────────
  const setAnswer = (index, value) => {
    setAnswers((prev) => { const next = [...prev]; next[index] = value; return next; });
  };

  // ── Hint ──────────────────────────────────────────────────────────────────
  const handleHint = async (index) => {
    if (hints[index]) return;
    const q = questions[index];
    setHintLoading((prev) => ({ ...prev, [index]: true }));
    setHintError((prev) => ({ ...prev, [index]: '' }));
    try {
      const data = await quizService.getHint({
        question: q.question,
        correctAnswer: q.answer,
        concept: q.concept || null,
        questionType: q._type,
      });
      if (data?.success && data.hint) {
        setHints((prev) => ({ ...prev, [index]: data.hint }));
        quizService.logSupportEvent({ userId, questionId: q.question_id || `q_${index}`, supportType: 'hint', quizId: null });
      } else {
        setHintError((prev) => ({ ...prev, [index]: data?.error || 'Hint unavailable. Please try again.' }));
      }
    } catch {
      setHintError((prev) => ({ ...prev, [index]: 'Could not load hint. Please try again.' }));
    } finally {
      setHintLoading((prev) => ({ ...prev, [index]: false }));
    }
  };

  // ── Submit — sends everything to backend, renders what backend returns ────
  const handleSubmit = async () => {
    setState(STATE.SUBMITTING);
    setError('');
    try {
      const now = Date.now();
      const mcqs = questions.filter((q) => q._type === 'MCQ');
      const shorts = questions.filter((q) => q._type === 'Short Answer');
      const mcqAnswers = mcqs.map((q) => answers[questions.indexOf(q)] || '');
      const shortAnswers = shorts.map((q) => answers[questions.indexOf(q)] || '');

      const questionTimings = questions.map((q, i) => {
        const startMs = startTimesRef.current[i] ?? now;
        return {
          question_id: q.question_id || `q_${i}`,
          question_start_time: new Date(startMs).toISOString(),
          time_taken_seconds: Math.round((now - startMs) / 1000),
        };
      });

      const data = await quizService.submitFull({
        mcqAnswers,
        mcqData: mcqs,
        shortAnswers,
        shortData: shorts,
        userId,
        documentId,
        documentName,
        questionTimings,
      });

      if (!data.success) throw new Error(data.error || 'Quiz submission failed.');
      setReport(data.report);
      setState(STATE.RESULTS);
    } catch (err) {
      setError(err.message || 'Could not submit quiz.');
      setState(STATE.ACTIVE);
    }
  };

  // ── Retake ────────────────────────────────────────────────────────────────
  const handleRetake = () => {
    setAnswers(new Array(questions.length).fill(''));
    setCurrentIndex(0);
    setReport(null);
    setHints({});
    setHintLoading({});
    setHintError({});
    startTimesRef.current = {};
    setState(STATE.ACTIVE);
  };

  const handleNewQuiz = () => {
    setQuestions([]);
    setAnswers([]);
    setReport(null);
    setState(STATE.IDLE);
  };

  // ── Idle ──────────────────────────────────────────────────────────────────
  if (state === STATE.IDLE) {
    return (
      <div className="workspace-content card">
        <div className="quiz-panel-start">
          <span className="workspace-placeholder-icon" aria-hidden="true">✏️</span>
          <h2>Quiz</h2>
          <p>Test your understanding of the uploaded document with auto-generated questions.</p>
          <button type="button" className="button button-primary" onClick={handleGenerate}>
            Generate Quiz
          </button>
          {error && <p className="quiz-error">{error}</p>}
        </div>
      </div>
    );
  }

  // ── Loading ───────────────────────────────────────────────────────────────
  if (state === STATE.LOADING) {
    return (
      <div className="workspace-content card">
        <div className="quiz-panel-start">
          <span className="workspace-placeholder-icon" aria-hidden="true">✏️</span>
          <p><strong>Generating your personalized quiz…</strong></p>
          <p>This may take up to 30 seconds.</p>
        </div>
      </div>
    );
  }

  // ── Submitting ────────────────────────────────────────────────────────────
  if (state === STATE.SUBMITTING) {
    return (
      <div className="workspace-content card">
        <div className="quiz-panel-start">
          <span className="workspace-placeholder-icon" aria-hidden="true">⏳</span>
          <p><strong>Evaluating your answers…</strong></p>
          <p>This may take a few seconds.</p>
        </div>
      </div>
    );
  }

  // ── Results — pure display of backend report fields ───────────────────────
  if (state === STATE.RESULTS && report) {
    const pct = report.percentage ?? 0;
    const evaluations = report.evaluations || [];

    return (
      <div className="workspace-content card quiz-results">
        <h2>Quiz Results</h2>

        {/* Score headline — from backend */}
        <p className="quiz-score-headline">
          {report.score ?? 0} / {report.total ?? questions.length} correct — {pct}%
        </p>

        {/* Comprehension score — from backend */}
        {report.comprehension_score != null && (
          <div className="quiz-section">
            <h3>Comprehension Score</h3>
            <p>{report.comprehension_score}%</p>
          </div>
        )}

        {/* Personalized feedback — from backend generate_personalized_quiz_feedback() */}
        {report.feedback_strengths && (
          <div className="quiz-section">
            <h3>💪 Strengths</h3>
            <p>{report.feedback_strengths}</p>
          </div>
        )}
        {report.feedback_weaknesses && (
          <div className="quiz-section">
            <h3>🎯 Areas to Improve</h3>
            <p>{report.feedback_weaknesses}</p>
          </div>
        )}
        {report.feedback_recommended_concepts && (
          <div className="quiz-section">
            <h3>📚 Recommended Concepts</h3>
            <p>{report.feedback_recommended_concepts}</p>
          </div>
        )}
        {report.feedback_suggested_learning_mode && (
          <div className="quiz-section">
            <h3>💡 Suggested Learning Mode</h3>
            <p>{report.feedback_suggested_learning_mode}</p>
          </div>
        )}

        {/* General strengths/weaknesses/recommendations — from backend evaluate_mcq() */}
        {report.strengths && !report.feedback_strengths && (
          <div className="quiz-section">
            <h3>Strengths</h3>
            <p>{report.strengths}</p>
          </div>
        )}
        {report.weaknesses && !report.feedback_weaknesses && (
          <div className="quiz-section">
            <h3>Areas to Improve</h3>
            <p>{report.weaknesses}</p>
          </div>
        )}
        {report.recommendations && !report.feedback_recommended_concepts && (
          <div className="quiz-section">
            <h3>Recommendations</h3>
            <p>{report.recommendations}</p>
          </div>
        )}

        {/* Per-question breakdown — from backend evaluations[] */}
        {evaluations.length > 0 && (
          <div className="quiz-section">
            <h3>Question Breakdown</h3>
            {evaluations.map((ev, i) => {
              const result = ev.result || 'Incorrect';
              const isCorrect = result === 'Correct';
              const isPartial = result === 'Partially Correct';
              return (
                <div
                  key={i}
                  className={`quiz-eval-item${isCorrect ? ' quiz-eval-correct' : isPartial ? ' quiz-eval-partial' : ' quiz-eval-wrong'}`}
                >
                  <p className="quiz-eval-q"><strong>Q{i + 1}:</strong> {ev.question}</p>
                  <p className="quiz-eval-result">
                    {isCorrect ? '✅ Correct' : isPartial ? '⚠️ Partially Correct' : '❌ Incorrect'}
                  </p>
                  {ev.correct_answer && (
                    <p className="quiz-eval-answer"><strong>Correct answer:</strong> {ev.correct_answer}</p>
                  )}
                  {ev.explanation && <p className="quiz-eval-feedback">{ev.explanation}</p>}
                  {ev.improvement_tip && <p className="quiz-eval-tip"><em>{ev.improvement_tip}</em></p>}
                </div>
              );
            })}
          </div>
        )}

        <div className="quiz-actions">
          <button type="button" className="button button-secondary" onClick={handleRetake}>Retake Quiz</button>
          <button type="button" className="button button-primary" onClick={handleNewQuiz}>New Quiz</button>
        </div>
      </div>
    );
  }

  // ── Active ────────────────────────────────────────────────────────────────
  const total = questions.length;
  const q = questions[currentIndex];
  if (!q) return null;

  const answered = answers.filter((a) => a && a.trim()).length;
  const progressPct = total > 0 ? Math.round((answered / total) * 100) : 0;
  const isMCQ = q._type === 'MCQ';
  const currentAnswer = answers[currentIndex] || '';

  return (
    <div className="workspace-content card quiz-active">
      {/* Progress */}
      <div className="quiz-phase-header">
        <span className="quiz-phase-label">
          Question {currentIndex + 1} of {total} — {answered} answered ({progressPct}%)
        </span>
        <div className="quiz-phase-track">
          <div className="quiz-phase-track-fill" style={{ width: `${progressPct}%` }} />
        </div>
      </div>

      {/* Question card */}
      <div className="quiz-question">
        <span className="quiz-type-badge">{isMCQ ? 'Multiple Choice' : 'Short Answer'}</span>
        <p className="quiz-question-text">
          <strong>Q{currentIndex + 1}.</strong> {q.question}
        </p>

        {isMCQ ? (
          <ul className="quiz-options">
            {(q.options || []).map((opt, oi) => (
              <li key={oi}>
                <label className={`quiz-option${currentAnswer === opt ? ' quiz-option--selected' : ''}`}>
                  <input
                    type="radio"
                    name={`q-${currentIndex}`}
                    value={opt}
                    checked={currentAnswer === opt}
                    onChange={() => setAnswer(currentIndex, opt)}
                  />
                  {opt}
                </label>
              </li>
            ))}
          </ul>
        ) : (
          <textarea
            className="quiz-short-input"
            rows={3}
            placeholder="Your answer…"
            value={currentAnswer}
            onChange={(e) => setAnswer(currentIndex, e.target.value)}
          />
        )}
      </div>

      {/* Hint */}
      <div className="quiz-hint-row">
        {!hints[currentIndex] && (
          <button
            type="button"
            className="button button-secondary quiz-hint-btn"
            onClick={() => handleHint(currentIndex)}
            disabled={hintLoading[currentIndex]}
          >
            {hintLoading[currentIndex] ? 'Getting hint…' : '💡 Show Hint'}
          </button>
        )}
        {hintError[currentIndex] && <p className="quiz-hint-error">{hintError[currentIndex]}</p>}
        {hints[currentIndex] && (
          <div className="quiz-hint-box">
            <strong>💡 Hint:</strong> {hints[currentIndex]}
          </div>
        )}
      </div>

      {error && <p className="quiz-error">{error}</p>}

      {/* Navigation */}
      <div className="quiz-actions quiz-actions--between">
        <button
          type="button"
          className="button button-secondary"
          onClick={() => goTo(currentIndex - 1)}
          disabled={currentIndex === 0}
        >
          ◀ Previous
        </button>

        {currentIndex < total - 1 ? (
          <button type="button" className="button button-primary" onClick={() => goTo(currentIndex + 1)}>
            Next ▶
          </button>
        ) : (
          <button
            type="button"
            className="button button-primary"
            onClick={handleSubmit}
            disabled={state === STATE.SUBMITTING}
          >
            {state === STATE.SUBMITTING ? 'Submitting…' : '✅ Submit Quiz'}
          </button>
        )}
      </div>
    </div>
  );
}
