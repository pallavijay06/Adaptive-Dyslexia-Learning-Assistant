import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { quizService } from '../services/quizService';

const STATE = { IDLE: 'idle', LOADING: 'loading', ACTIVE: 'active', SUBMITTING: 'submitting', RESULTS: 'results' };
const PHASE = { MCQ: 'mcq', SHORT: 'short' };

export default function QuizPanel({ documentId, documentName }) {
  const { user } = useAuth();
  const [state, setState] = useState(STATE.IDLE);
  const [phase, setPhase] = useState(PHASE.MCQ);
  const [mcqs, setMcqs] = useState([]);
  const [shortQuestions, setShortQuestions] = useState([]);
  const [mcqAnswers, setMcqAnswers] = useState({});
  const [shortAnswers, setShortAnswers] = useState({});
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');

  const handleGenerate = async () => {
    setError('');
    setState(STATE.LOADING);
    try {
      const data = await quizService.generateQuiz({ documentId });
      if (!data.success) throw new Error(data.error || 'Quiz generation failed.');
      setMcqs(data.mcqs || []);
      setShortQuestions(data.short_questions || []);
      setMcqAnswers({});
      setShortAnswers({});
      setReport(null);
      setPhase(PHASE.MCQ);
      setState(STATE.ACTIVE);
    } catch (err) {
      setError(err.message || 'Could not generate quiz.');
      setState(STATE.IDLE);
    }
  };

  const handleNextToShort = () => {
    setPhase(PHASE.SHORT);
  };

  const handleBackToMcq = () => {
    setError('');
    setPhase(PHASE.MCQ);
  };

  const handleSubmit = async () => {
    setState(STATE.SUBMITTING);
    try {
      const answers = mcqs.map((_, i) => mcqAnswers[i] ?? null);
      const data = await quizService.submitQuiz({
        answers,
        quizData: mcqs,
        userId: user?.id,
        documentId,
        documentName,
      });
      if (!data.success) throw new Error(data.error || 'Submission failed.');
      setReport(data.report);
      setState(STATE.RESULTS);
    } catch (err) {
      setError(err.message || 'Could not submit quiz.');
      setState(STATE.ACTIVE);
    }
  };

  const handleRetake = () => {
    setReport(null);
    setMcqAnswers({});
    setShortAnswers({});
    setPhase(PHASE.MCQ);
    setState(STATE.ACTIVE);
  };

  const handleNewQuiz = () => {
    setMcqs([]);
    setShortQuestions([]);
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

  // ── Results ───────────────────────────────────────────────────────────────
  if (state === STATE.RESULTS && report) {
    const pct = report.percentage ?? Math.round(((report.score ?? 0) / (report.total || 1)) * 100);
    return (
      <div className="workspace-content card quiz-results">
        <h2>Quiz Results</h2>
        <p className="quiz-score-headline">
          {report.score ?? 0} / {report.total ?? mcqs.length} correct — {pct}%
        </p>

        {report.strengths?.length > 0 && (
          <div className="quiz-section">
            <h3>Strengths</h3>
            <ul>{report.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
          </div>
        )}
        {report.weaknesses?.length > 0 && (
          <div className="quiz-section">
            <h3>Areas to Improve</h3>
            <ul>{report.weaknesses.map((w, i) => <li key={i}>{w}</li>)}</ul>
          </div>
        )}
        {report.recommendations?.length > 0 && (
          <div className="quiz-section">
            <h3>Recommendations</h3>
            <ul>{report.recommendations.map((r, i) => <li key={i}>{r}</li>)}</ul>
          </div>
        )}

        <div className="quiz-actions">
          <button type="button" className="button button-secondary" onClick={handleRetake}>Retake Quiz</button>
          <button type="button" className="button button-primary" onClick={handleNewQuiz}>New Quiz</button>
        </div>
      </div>
    );
  }

  // ── Active (Phase 1: MCQ) ─────────────────────────────────────────────────
  if (state === STATE.ACTIVE && phase === PHASE.MCQ) {
    return (
      <div className="workspace-content card quiz-active">
        <div className="quiz-phase-header">
          <span className="quiz-phase-label">Part 1 of 2 – Multiple Choice</span>
          <div className="quiz-phase-track">
            <div className="quiz-phase-track-fill quiz-phase-track-fill--half" />
          </div>
        </div>

        <section className="quiz-section">
          <h3>Multiple Choice</h3>
          {mcqs.map((q, qi) => (
            <div key={qi} className="quiz-question">
              <p className="quiz-question-text"><strong>Q{qi + 1}.</strong> {q.question}</p>
              <ul className="quiz-options">
                {(q.options || []).map((opt, oi) => (
                  <li key={oi}>
                    <label className={`quiz-option${mcqAnswers[qi] === oi ? ' quiz-option--selected' : ''}`}>
                      <input
                        type="radio"
                        name={`mcq-${qi}`}
                        value={oi}
                        checked={mcqAnswers[qi] === oi}
                        onChange={() => setMcqAnswers((prev) => ({ ...prev, [qi]: oi }))}
                      />
                      {opt}
                    </label>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </section>

        {error && <p className="quiz-error">{error}</p>}

        <div className="quiz-actions quiz-actions--end">
          <button type="button" className="button button-primary" onClick={handleNextToShort}>
            Next →
          </button>
        </div>
      </div>
    );
  }

  // ── Active (Phase 2: Short Answer) ────────────────────────────────────────
  return (
    <div className="workspace-content card quiz-active">
      <div className="quiz-phase-header">
        <span className="quiz-phase-label">Part 2 of 2 – Short Answer</span>
        <div className="quiz-phase-track">
          <div className="quiz-phase-track-fill quiz-phase-track-fill--full" />
        </div>
      </div>

      <section className="quiz-section">
        <h3>Short Answer</h3>
        {shortQuestions.map((q, qi) => (
          <div key={qi} className="quiz-question">
            <p className="quiz-question-text"><strong>Q{qi + 1}.</strong> {q.question}</p>
            <textarea
              className="quiz-short-input"
              rows={3}
              placeholder="Your answer…"
              value={shortAnswers[qi] || ''}
              onChange={(e) => setShortAnswers((prev) => ({ ...prev, [qi]: e.target.value }))}
            />
          </div>
        ))}
      </section>

      {error && <p className="quiz-error">{error}</p>}

      <div className="quiz-actions quiz-actions--between">
        <button type="button" className="button button-secondary" onClick={handleBackToMcq}>
          ← Back
        </button>
        <button
          type="button"
          className="button button-primary"
          onClick={handleSubmit}
          disabled={state === STATE.SUBMITTING}
        >
          {state === STATE.SUBMITTING ? 'Submitting…' : 'Submit Quiz'}
        </button>
      </div>
    </div>
  );
}
