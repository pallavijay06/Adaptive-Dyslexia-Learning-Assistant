import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useDocument } from '../contexts/DocumentContext';
import { useJourney } from '../contexts/JourneyContext';
import { adaptiveService } from '../services/adaptiveService';
import SimplifiedNotesPanel from '../components/SimplifiedNotesPanel';
import VisualLearningPanel from '../components/VisualLearningPanel';
import ListenModePanel from '../components/ListenModePanel';
import QuizPanel from '../components/QuizPanel';
import StemSupportPanel from '../components/StemSupportPanel';
import ChatPanel from '../components/ChatPanel';
import RevisionPanel from '../components/RevisionPanel';

// ── Step action → workspace tab mapping ──────────────────────────────────────
const MODE_TO_TAB = {
  'Simplified Notes': 'notes',
  'Visual Learning':  'visual',
  'Listen Mode':      'listen',
  'Audio Learning':   'listen',
  'Audio':            'listen',
  'Quiz':             'quiz',
  'STEM Support':     'stem',
  'AI Tutor':         'tutor',
  'Revision':         'notes',
};

const ACTION_TO_TAB = {
  revision:       'notes',
  learning_mode:  null,   // resolved via step.mode
  quiz:           'quiz',
  ai_tutor:       'tutor',
  stem_support:   'stem',
};

function resolveTab(step) {
  if (!step) return 'notes';
  if (step.mode && MODE_TO_TAB[step.mode]) return MODE_TO_TAB[step.mode];
  return ACTION_TO_TAB[step.action] ?? 'notes';
}

// ── Presentational helpers ────────────────────────────────────────────────────
const ACTION_ICONS = {
  revision:       '🔄',
  learning_mode:  '📖',
  quiz:           '✏️',
  ai_tutor:       '🤖',
};

const ACTION_LABELS = {
  revision:       'Revision',
  learning_mode:  'Learning Mode',
  quiz:           'Quiz',
  ai_tutor:       'AI Tutor',
};

function StepBadge({ action, mode }) {
  const label = (action === 'learning_mode' && mode) ? mode : (ACTION_LABELS[action] ?? action);
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '0.3rem',
      padding: '0.2rem 0.6rem', borderRadius: '999px',
      fontSize: '0.75rem', fontWeight: 600,
      background: 'var(--color-primary, #6366f1)', color: '#fff',
    }}>
      {ACTION_ICONS[action] ?? '📌'} {label}
    </span>
  );
}

function ConceptList({ label, concepts }) {
  if (!concepts?.length) return null;
  return (
    <p style={{ margin: '0.25rem 0', fontSize: '0.875rem' }}>
      <strong>{label}:</strong>{' '}
      {concepts.map((c, i) => (
        <span key={i} style={{
          display: 'inline-block',
          background: 'var(--color-surface-alt, #f3f4f6)',
          borderRadius: '4px', padding: '0 0.4rem',
          marginRight: '0.3rem', marginBottom: '0.2rem',
        }}>{c}</span>
      ))}
    </p>
  );
}

function SummaryCard({ summary }) {
  if (!summary) return null;
  const fields = [
    { key: 'teaching_style',    label: 'TEACHING STYLE' },
    { key: 'learning_strategy', label: 'LEARNING STRATEGY' },
    { key: 'session_duration',  label: 'SESSION DURATION' },
  ];
  return (
    <section className="card" aria-label="Learner profile summary" style={{ marginBottom: '1.5rem' }}>
      <h3 style={{ marginTop: 0 }}>Your Learner Profile</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '0.75rem' }}>
        {fields.map(({ key, label }) => summary[key] && (
          <div key={key}>
            <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--color-muted, #6b7280)', fontWeight: 600 }}>{label}</p>
            <p style={{ margin: 0 }}>{summary[key]}</p>
          </div>
        ))}
        {summary.overall_confidence != null && (
          <div>
            <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--color-muted, #6b7280)', fontWeight: 600 }}>PLAN CONFIDENCE</p>
            <p style={{ margin: 0 }}>{Math.round(summary.overall_confidence * 100)}%</p>
          </div>
        )}
      </div>
      {summary.focus_concepts?.length > 0 && (
        <div style={{ marginTop: '0.75rem' }}>
          <ConceptList label="Focus concepts" concepts={summary.focus_concepts} />
        </div>
      )}
    </section>
  );
}

function StepPanel({ step, docId, docName, simplifiedText, onNotesGenerated }) {
  if (step?.action === 'revision') {
    return (
      <RevisionPanel
        revisionTopics={step.revision_topics ?? []}
        revisionReason={step.reason ?? ''}
        documentId={docId}
      />
    );
  }
  const tab = resolveTab(step);
  if (tab === 'visual') return <VisualLearningPanel documentId={docId} />;
  if (tab === 'listen') return <ListenModePanel documentId={docId} simplifiedText={simplifiedText} />;
  if (tab === 'quiz')   return <QuizPanel documentId={docId} documentName={docName} />;
  if (tab === 'stem')   return <StemSupportPanel documentId={docId} />;
  if (tab === 'tutor')  return <ChatPanel />;
  // default: notes
  return <SimplifiedNotesPanel documentId={docId} onNotesGenerated={onNotesGenerated} />;
}

function StepCard({ step, isCurrent, isCompleted, isLastStep, onNext, onComplete, actionLoading, docId, docName, simplifiedText, onNotesGenerated }) {
  const dimmed = !isCurrent && !isCompleted;
  return (
    <article
      aria-current={isCurrent ? 'step' : undefined}
      style={{
        border: isCurrent
          ? '2px solid var(--color-primary, #6366f1)'
          : '1px solid var(--color-border, #e5e7eb)',
        borderRadius: '10px',
        padding: '1rem 1.25rem',
        opacity: dimmed ? 0.45 : 1,
        background: isCompleted ? 'var(--color-surface-alt, #f9fafb)' : 'var(--color-surface, #fff)',
        transition: 'opacity 0.2s',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
        <span style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--color-muted, #6b7280)' }}>
          Step {step.step}
        </span>
        <StepBadge action={step.action} mode={step.mode} />
        {isCompleted && (
          <span style={{ marginLeft: 'auto', color: '#10b981', fontWeight: 700 }}>✓ Done</span>
        )}
      </div>

      {step.action !== 'learning_mode' && step.mode && (
        <p style={{ margin: '0.25rem 0', fontSize: '0.875rem' }}>
          <strong>Mode:</strong> {step.mode}
        </p>
      )}
      {step.quiz_length != null && (
        <p style={{ margin: '0.25rem 0', fontSize: '0.875rem' }}>
          <strong>Questions:</strong> {step.quiz_length}
          {step.quiz_timing ? ` · ${step.quiz_timing}` : ''}
        </p>
      )}
      <ConceptList label="Focus concepts" concepts={step.focus_concepts} />
      <ConceptList label="Concepts" concepts={step.concepts} />

      {isCurrent && (
        <>
          {/* Inline learning panel — no navigation */}
          <div style={{ marginTop: '1rem', borderTop: '1px solid var(--color-border, #e5e7eb)', paddingTop: '1rem' }}>
            <StepPanel
              step={step}
              docId={docId}
              docName={docName}
              simplifiedText={simplifiedText}
              onNotesGenerated={onNotesGenerated}
            />
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem', flexWrap: 'wrap' }}>
            {isLastStep ? (
              <button
                type="button"
                className="button button-primary"
                onClick={() => onComplete(step)}
                disabled={actionLoading}
              >
                {actionLoading ? 'Saving…' : 'Complete Learning Session'}
              </button>
            ) : (
              <button
                type="button"
                className="button button-primary"
                onClick={() => onNext(step)}
                disabled={actionLoading}
              >
                {actionLoading ? 'Saving…' : 'Next Step →'}
              </button>
            )}
          </div>
        </>
      )}
    </article>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function JourneyRoute() {
  const navigate  = useNavigate();
  const { user }  = useAuth();
  const { activeDocument } = useDocument();
  const { adaptiveLearningPlan, setCurrentStep, setCurrentRecommendation, setLearningPath } = useJourney();
  const [simplifiedText, setSimplifiedText] = useState(null);

  const [recommendation,   setRecommendation]   = useState(null);
  const [learningPathData, setLearningPathData] = useState(null);
  const [loading,          setLoading]          = useState(true);
  const [actionLoading,    setActionLoading]    = useState(false);
  const [error,            setError]            = useState('');
  const [journeyComplete,  setJourneyComplete]  = useState(false);

  const summary = adaptiveLearningPlan?.decision_summary ?? null;

  // ── Fetch live journey state from backend ─────────────────────────────────
  const fetchJourneyState = useCallback(async () => {
    if (!user?.id) return;
    const [recData, pathData] = await Promise.all([
      adaptiveService.getCurrentRecommendation(user.id),
      adaptiveService.getLearningPath(user.id),
    ]);
    setRecommendation(recData);
    setCurrentRecommendation(recData);
    setLearningPathData(pathData);
    setLearningPath(pathData);
    if (recData.current_step != null) setCurrentStep(recData.current_step);
  }, [user?.id, setCurrentRecommendation, setLearningPath, setCurrentStep]);

  // ── On mount: load journey state ───────────────────────────────────────
  useEffect(() => {
    const init = async () => {
      try {
        if (!adaptiveLearningPlan && user?.id) {
          // Landed directly — try to resume an existing backend session
          try {
            await fetchJourneyState();
          } catch {
            navigate('/learning-selection', { replace: true });
          }
        } else {
          await fetchJourneyState();
        }
      } catch (err) {
        setError(err.message || 'Could not load your learning journey.');
      } finally {
        setLoading(false);
      }
    };

    init();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── "Next Step" — complete current step and refresh journey in-place ──────
  const handleNextStep = async (step) => {
    setActionLoading(true);
    setError('');
    try {
      await adaptiveService.completeStep(user.id, step.step);
      const nextData = await adaptiveService.nextStep(user.id);
      if (nextData.journey_complete) {
        setJourneyComplete(true);
        return;
      }
      await fetchJourneyState();
    } catch (err) {
      setError(err.message || 'Could not advance to the next step.');
    } finally {
      setActionLoading(false);
    }
  };

  // ── "Complete Learning Session" — final step completion ───────────────────
  const handleCompleteSession = async (step) => {
    setActionLoading(true);
    setError('');
    try {
      await adaptiveService.completeStep(user.id, step.step);
      await adaptiveService.nextStep(user.id); // returns journey_complete: true
      setJourneyComplete(true);
    } catch (err) {
      setError(err.message || 'Could not complete the learning session.');
    } finally {
      setActionLoading(false);
    }
  };

  // ── Render states ─────────────────────────────────────────────────────────
  if (loading) {
    return (
      <section className="card" style={{ maxWidth: '640px', margin: '0 auto' }}>
        <p>{actionLoading ? 'Saving progress…' : 'Loading your personalized learning journey…'}</p>
      </section>
    );
  }

  if (journeyComplete) {
    return (
      <section className="card" style={{ maxWidth: '640px', margin: '0 auto', textAlign: 'center' }}>
        <div style={{ fontSize: '3rem', marginBottom: '0.5rem' }}>🎉</div>
        <h2>Journey Complete!</h2>
        <p>You have completed all steps in your personalized learning journey.</p>
        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', marginTop: '1.25rem' }}>
          <button type="button" className="button button-primary"
            onClick={() => navigate('/learning-selection')}>
            Start a New Journey
          </button>
          <button type="button" className="button button-secondary"
            onClick={() => navigate('/dashboard')}>
            Go to Dashboard
          </button>
        </div>
      </section>
    );
  }

  const flow          = learningPathData?.learning_path ?? adaptiveLearningPlan?.adaptive_learning_flow ?? [];
  const currentStepNum = recommendation?.current_step  ?? learningPathData?.current_step  ?? 1;
  const completedSteps = recommendation?.completed_steps ?? learningPathData?.completed_steps ?? [];
  const totalSteps     = recommendation?.total_steps    ?? flow.length;
  const docId   = activeDocument?.id ?? activeDocument?.document_id;
  const docName = activeDocument?.file_name ?? '';

  return (
    <div style={{ maxWidth: '760px', margin: '0 auto' }}>

      {/* Header + progress bar */}
      <section className="card" style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ marginTop: 0 }}>Personalized Learning Journey</h2>
        {totalSteps > 0 && (
          <>
            <p style={{ margin: '0 0 0.5rem', color: 'var(--color-muted, #6b7280)', fontSize: '0.875rem' }}>
              Step {currentStepNum} of {totalSteps}
            </p>
            <div
              role="progressbar"
              aria-valuenow={completedSteps.length}
              aria-valuemin={0}
              aria-valuemax={totalSteps}
              aria-label="Journey progress"
              style={{ height: '6px', borderRadius: '999px', background: 'var(--color-border, #e5e7eb)', overflow: 'hidden' }}
            >
              <div style={{
                height: '100%',
                width: `${Math.round((completedSteps.length / totalSteps) * 100)}%`,
                background: 'var(--color-primary, #6366f1)',
                transition: 'width 0.4s ease',
              }} />
            </div>
          </>
        )}
      </section>

      {/* Learner profile */}
      <SummaryCard summary={summary ?? recommendation?.summary} />

      {/* Error */}
      {error && (
        <p className="upload-error" role="alert" style={{ marginBottom: '1rem' }}>{error}</p>
      )}

      {/* Adaptive learning steps */}
      {flow.length > 0 && (
        <section aria-label="Adaptive learning steps">
          <h3 style={{ marginBottom: '0.75rem' }}>Your Adaptive Learning Steps</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {flow.map((step) => (
              <StepCard
                key={step.step}
                step={step}
                isCurrent={step.step === currentStepNum}
                isCompleted={completedSteps.includes(step.step)}
                isLastStep={step.step === totalSteps}
                onNext={handleNextStep}
                onComplete={handleCompleteSession}
                actionLoading={actionLoading}
                docId={docId}
                docName={docName}
                simplifiedText={simplifiedText}
                onNotesGenerated={setSimplifiedText}
              />
            ))}
          </div>
        </section>
      )}

      {/* Footer nav */}
      <div style={{ display: 'flex', gap: '0.75rem', marginTop: '2rem', flexWrap: 'wrap' }}>
        <button type="button" className="button button-secondary"
          onClick={() => navigate('/learning-selection')}>
          ← Back to Learning Selection
        </button>
        <button type="button" className="button button-secondary"
          onClick={() => navigate('/dashboard')}>
          Dashboard
        </button>
      </div>
    </div>
  );
}
