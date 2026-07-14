import { useState, useRef } from 'react';
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
  const quizStartTime = useRef(null);

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
      quizStartTime.current = Date.now();
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
      // Step 1: submit MCQ answers → get MCQ report
      const answers = mcqs.map((_, i) => mcqAnswers[i] ?? null);
      const mcqData = await quizService.submitQuiz({
        answers,
        quizData: mcqs,
        userId: user?.id,
        documentId,
        documentName,
      });
      if (!mcqData.success) throw new Error(mcqData.error || 'Submission failed.');

      const mcqReport = mcqData.report;

      // Step 2: evaluate each short answer in parallel
      const shortEvals = await Promise.all(
        shortQuestions.map((q, i) =>
          quizService.evaluateShortAnswer({
            studentAnswer: shortAnswers[i] || '',
            expectedAnswer: q.answer || '',
          }).then((res) => ({
            question: q.question,
            expected_answer: q.answer || '',
            student_answer: shortAnswers[i] || '',
            evaluation: res.success ? res.evaluation : {},
            ...q,
          })).catch(() => ({
            question: q.question,
            expected_answer: q.answer || '',
            student_answer: shortAnswers[i] || '',
            evaluation: {},
            ...q,
          }))
        )
      );

      // Step 3: merge short-answer evaluations into the MCQ report client-side
      // Mirrors the logic of combine_quiz_report_with_short_answers in quiz_service.py
      const merged = _mergeShortAnswers(mcqReport, shortEvals);

      // Step 4: attach time taken
      if (quizStartTime.current) {
        merged.time_taken_seconds = Math.round((Date.now() - quizStartTime.current) / 1000);
      }

      setReport(merged);
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
    quizStartTime.current = Date.now();
    setState(STATE.ACTIVE);
  };

  const handleNewQuiz = () => {
    setMcqs([]);
    setShortQuestions([]);
    setReport(null);
    quizStartTime.current = null;
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

  // ── Submitting / Evaluating ───────────────────────────────────────────────
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

  // ── Results ───────────────────────────────────────────────────────────────
  if (state === STATE.RESULTS && report) {
    const pct = report.percentage ?? Math.round(((report.score ?? 0) / (report.total || 1)) * 100);
    const notAnswered = (report.question_results || []).filter((r) => r.not_answered).length;
    const timeTaken = report.time_taken_seconds;

    return (
      <div className="workspace-content card quiz-results">
        <h2>Quiz Results</h2>

        {/* Score summary */}
        <p className="quiz-score-headline">
          {report.score ?? 0} / {report.total ?? mcqs.length} correct — {pct}%
        </p>
        {notAnswered > 0 && (
          <p className="quiz-not-answered-note">{notAnswered} question{notAnswered > 1 ? 's' : ''} not answered</p>
        )}
        {timeTaken != null && (
          <p className="quiz-time-note">Time taken: {_formatTime(timeTaken)}</p>
        )}

        {/* Per-question feedback */}
        {(report.evaluations || []).length > 0 && (
          <div className="quiz-section">
            <h3>Question Feedback</h3>
            {report.evaluations.map((ev, i) => (
              <div key={i} className={`quiz-feedback-card quiz-feedback-card--${_resultClass(ev.result)}`}>
                <p className="quiz-feedback-question"><strong>Q{i + 1}.</strong> {ev.question}</p>
                <p className="quiz-feedback-your-answer">
                  <span className="quiz-feedback-label">Your answer:</span> {ev.your_answer || ev.student_answer || 'Not Answered'}
                </p>
                <p className="quiz-feedback-correct-answer">
                  <span className="quiz-feedback-label">Correct answer:</span> {ev.correct_answer}
                </p>
                <p className={`quiz-feedback-result quiz-feedback-result--${_resultClass(ev.result)}`}>
                  {_resultIcon(ev.result)} {ev.result}
                </p>
                {ev.explanation && (
                  <p className="quiz-feedback-explanation">{ev.explanation}</p>
                )}
                {ev.improvement_tip && (
                  <p className="quiz-feedback-tip">💡 {ev.improvement_tip}</p>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Concept performance */}
        {report.assessment_analytics?.concept_accuracy &&
          Object.keys(report.assessment_analytics.concept_accuracy).length > 0 && (
          <div className="quiz-section">
            <h3>Concept Performance</h3>
            <ul className="quiz-concept-list">
              {Object.entries(report.assessment_analytics.concept_accuracy).map(([concept, data]) => (
                <li key={concept} className="quiz-concept-item">
                  <span className="quiz-concept-name">{concept}</span>
                  <span className="quiz-concept-score">{data.correct}/{data.total} ({data.accuracy}%)</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Strengths */}
        {report.strengths && (
          <div className="quiz-section">
            <h3>Strengths</h3>
            <p>{report.strengths}</p>
          </div>
        )}

        {/* Areas to improve */}
        {report.weaknesses && (
          <div className="quiz-section">
            <h3>Areas to Improve</h3>
            <p>{report.weaknesses}</p>
          </div>
        )}

        {/* Recommendations */}
        {report.recommendations && (
          <div className="quiz-section">
            <h3>Recommendations</h3>
            <p>{report.recommendations}</p>
          </div>
        )}

        {/* Adaptive insights */}
        {(report.assessment_analytics?.assessment_insights || []).length > 0 && (
          <div className="quiz-section">
            <h3>Learning Insights</h3>
            <ul>
              {report.assessment_analytics.assessment_insights.map((insight, i) => (
                <li key={i}>{insight}</li>
              ))}
            </ul>
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
          Submit Quiz
        </button>
      </div>
    </div>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function _resultClass(result) {
  if (result === 'Correct') return 'correct';
  if (result === 'Not Answered') return 'not-answered';
  if (result === 'Partially Correct') return 'partial';
  return 'incorrect';
}

function _resultIcon(result) {
  if (result === 'Correct') return '✅';
  if (result === 'Not Answered') return '⬜';
  if (result === 'Partially Correct') return '🟡';
  return '❌';
}

function _formatTime(seconds) {
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

/**
 * Client-side mirror of combine_quiz_report_with_short_answers (quiz_service.py).
 * Merges short-answer evaluations into the MCQ report returned by /quiz/submit.
 */
function _mergeShortAnswers(mcqReport, shortFeedback) {
  const report = { ...mcqReport };
  const evaluations = [...(report.evaluations || [])];
  const questionResults = [...(report.question_results || [])];
  let correctCount = report.correct_answers ?? report.score ?? 0;
  let totalCount = report.total ?? 0;
  let weakCount = report.incorrect_answers ?? Math.max(totalCount - correctCount, 0);

  shortFeedback.forEach((item, idx) => {
    const evaluation = item.evaluation || {};
    const score = parseInt(evaluation.score ?? 0, 10);
    const maxScore = Math.max(parseInt(evaluation.max_score ?? 5, 10), 1);
    const question = item.question || '';
    const expectedAnswer = item.expected_answer || '';
    const studentAnswer = item.student_answer || '';
    const rawResult = (evaluation.result || '').trim();
    const result = ['Correct', 'Partially Correct', 'Incorrect'].includes(rawResult)
      ? rawResult
      : score >= maxScore * 0.8 ? 'Correct' : score >= maxScore * 0.4 ? 'Partially Correct' : 'Incorrect';

    totalCount += 1;
    if (result === 'Correct') {
      correctCount += 1;
    } else {
      weakCount += 1;
    }

    evaluations.push({
      question,
      your_answer: studentAnswer || 'No answer',
      correct_answer: expectedAnswer,
      result,
      explanation: evaluation.feedback || evaluation.local_explanation || '',
      feedback: evaluation.feedback || '',
      improvement_tip: evaluation.improvement_tip || '',
      concept: evaluation.concept || '',
      difficulty: item.difficulty || '',
      skill: item.skill || '',
      is_correct: result === 'Correct',
      not_answered: !studentAnswer,
      identified_keywords: evaluation.identified_keywords || [],
      missing_keywords: evaluation.missing_keywords || [],
    });

    questionResults.push({
      question_id: item.question_id || `SA${String(idx + 1).padStart(3, '0')}`,
      question_type: 'Short Answer',
      concept: evaluation.concept || item.concept || '',
      difficulty: item.difficulty || '',
      skill: item.skill || '',
      question,
      your_answer: studentAnswer || 'No answer',
      student_answer: studentAnswer,
      correct_answer: expectedAnswer,
      is_correct: result === 'Correct',
      not_answered: !studentAnswer,
      score,
      feedback: evaluation.feedback || '',
      improvement_tip: evaluation.improvement_tip || '',
      local_explanation: evaluation.local_explanation || '',
    });
  });

  report.evaluations = evaluations;
  report.score = correctCount;
  report.total = totalCount;
  report.percentage = totalCount > 0 ? Math.round((correctCount / totalCount) * 100) : 0;
  report.correct_answers = correctCount;
  report.incorrect_answers = weakCount;
  report.question_results = questionResults;
  return report;
}
