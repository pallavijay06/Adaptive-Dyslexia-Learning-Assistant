import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDocument } from '../contexts/DocumentContext';
import SimplifiedNotesPanel from '../components/SimplifiedNotesPanel';
import VisualLearningPanel from '../components/VisualLearningPanel';
import ListenModePanel from '../components/ListenModePanel';

const TABS = [
  { id: 'notes',  label: 'Simplified Notes', icon: '📝' },
  { id: 'visual', label: 'Visual Learning',  icon: '🗺️' },
  { id: 'listen', label: 'Listen Mode',      icon: '🎧' },
  { id: 'quiz',   label: 'Quiz',             icon: '✏️', sprint: 8 },
  { id: 'stem',   label: 'STEM Support',     icon: '🔬', sprint: 8 },
  { id: 'tutor',  label: 'AI Tutor',         icon: '🤖', sprint: 8 },
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

export default function WorkspacePage() {
  const navigate = useNavigate();
  const { activeDocument } = useDocument();
  const [activeTab, setActiveTab] = useState(TABS[0].id);
  const [simplifiedText, setSimplifiedText] = useState(null);

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
          <button
            type="button"
            className="button button-secondary workspace-back-btn"
            onClick={() => navigate('/dashboard')}
            aria-label="Back to Dashboard"
          >
            ← Dashboard
          </button>
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
        {currentTab?.sprint && (
          <div className="workspace-content card">
            <div className="workspace-placeholder">
              <span className="workspace-placeholder-icon" aria-hidden="true">
                {currentTab?.icon}
              </span>
              <h2 className="workspace-placeholder-title">{currentTab?.label}</h2>
              <p className="workspace-placeholder-text">
                This learning mode will be implemented in Sprint {currentTab?.sprint}.
              </p>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
