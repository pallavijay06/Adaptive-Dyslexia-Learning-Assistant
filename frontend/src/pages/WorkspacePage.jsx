import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useDocument } from '../contexts/DocumentContext';
import { useJourney } from '../contexts/JourneyContext';
import SimplifiedNotesPanel from '../components/SimplifiedNotesPanel';
import VisualLearningPanel from '../components/VisualLearningPanel';
import ListenModePanel from '../components/ListenModePanel';
import StemSupportPanel from '../components/StemSupportPanel';
import ChatPanel from '../components/ChatPanel';
import QuizPanel from '../components/QuizPanel';

const TABS = [
  { id: 'notes',  label: 'Simplified Notes', icon: '📝' },
  { id: 'visual', label: 'Visual Learning',  icon: '🗺️' },
  { id: 'listen', label: 'Listen Mode',      icon: '🎧' },
  { id: 'quiz',   label: 'Quiz',             icon: '✏️' },
  { id: 'stem',   label: 'STEM Support',     icon: '🔬' },
  { id: 'tutor',  label: 'AI Tutor',         icon: '🤖' },
];

function formatUploadTime(isoString) {
  if (!isoString) return null;
  try {
    return new Date(isoString).toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    });
  } catch {
    return null;
  }
}

// Map mode names coming from the Decision Engine → workspace tab id
const MODE_TO_TAB = {
  'Simplified Notes':  'notes',
  'Visual Learning':   'visual',
  'Listen Mode':       'listen',
  'Audio Learning':    'listen',
  'Audio':             'listen',
  'Quiz':              'quiz',
  'STEM Support':      'stem',
  'AI Tutor':          'tutor',
  'Revision':          'notes',   // revision falls back to notes
  'Extra Examples':    'notes',
};

export default function WorkspacePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { activeDocument } = useDocument();
  const { adaptiveLearningPlan } = useJourney();

  // If the journey navigated here with a target tab, honour it
  const initialTab = (location.state?.tab && TABS.find(t => t.id === location.state.tab))
    ? location.state.tab
    : TABS[0].id;

  const [activeTab, setActiveTab] = useState(initialTab);
  const [simplifiedText, setSimplifiedText] = useState(null);

  // True when the learner arrived here as part of a guided journey step
  const journeyStepActive = Boolean(location.state?.journeyStep);
  const journeyStep = location.state?.journeyStep ?? null;

  if (!activeDocument) {
    navigate('/upload', { replace: true });
    return null;
  }

  const docId = activeDocument.id ?? activeDocument.document_id;
  const uploadedAt = formatUploadTime(activeDocument.upload_time);
  const currentTab = TABS.find((t) => t.id === activeTab);

  return (
    <div className="workspace-page">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className="workspace-header card">
        <div className="workspace-header-meta">
          {journeyStepActive ? (
            <button
              type="button"
              className="button button-primary workspace-back-btn"
              onClick={() => navigate('/journey', { state: { completedStep: journeyStep } })}
              aria-label="Done — return to journey"
            >
              ✓ Done — Back to Journey
            </button>
          ) : (
            <button
              type="button"
              className="button button-secondary workspace-back-btn"
              onClick={() => navigate('/dashboard')}
              aria-label="Back to Dashboard"
            >
              ← Dashboard
            </button>
          )}
          <div className="workspace-doc-info">
            <h1 className="workspace-doc-title">{activeDocument.file_name}</h1>
            <div className="workspace-doc-badges">
              {activeDocument.file_type && (
                <span className="workspace-badge workspace-badge--type">
                  {activeDocument.file_type.toUpperCase()}
                </span>
              )}
              {uploadedAt && (
                <span className="workspace-badge workspace-badge--time">
                  Uploaded {uploadedAt}
                </span>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* ── Tab Navigation ─────────────────────────────────────────────── */}
      <nav className="workspace-nav" aria-label="Learning modes">
        <ul className="workspace-tab-list" role="tablist">
          {TABS.map((tab) => (
            <li key={tab.id} role="presentation">
              <button
                type="button"
                role="tab"
                id={`tab-${tab.id}`}
                aria-selected={activeTab === tab.id}
                aria-controls={`panel-${tab.id}`}
                className={`workspace-tab${activeTab === tab.id ? ' workspace-tab--active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                <span className="workspace-tab-icon" aria-hidden="true">{tab.icon}</span>
                <span className="workspace-tab-label">{tab.label}</span>
              </button>
            </li>
          ))}
        </ul>
      </nav>

      {/* ── Content Area ───────────────────────────────────────────────── */}
      <section
        role="tabpanel"
        id={`panel-${activeTab}`}
        aria-labelledby={`tab-${activeTab}`}
      >
        {activeTab === 'notes' && (
          <SimplifiedNotesPanel documentId={docId} onNotesGenerated={setSimplifiedText} />
        )}
        {activeTab === 'visual' && (
          <VisualLearningPanel documentId={docId} />
        )}
        {activeTab === 'listen' && (
          <ListenModePanel documentId={docId} simplifiedText={simplifiedText} />
        )}
        {activeTab === 'quiz' && (
          <QuizPanel documentId={activeDocument.document_id} documentName={activeDocument.file_name} />
        )}
        {activeTab === 'stem' && (
          <StemSupportPanel documentId={docId} />
        )}
        {activeTab === 'tutor' && (
          <ChatPanel />
        )}
      </section>
    </div>
  );
}
