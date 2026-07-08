import { useState, useCallback } from 'react';
import { learningService } from '../services/learningService';

const DIAGRAM_TYPES = [
  { value: 'both',      label: 'Both (Flowchart + Mind Map)' },
  { value: 'flowchart', label: 'Flowchart' },
  { value: 'mind_map',  label: 'Mind Map' },
];

export default function VisualLearningPanel({ documentId }) {
  const [diagramType, setDiagramType] = useState('both');
  const [visual, setVisual]           = useState(null);
  const [loading, setLoading]         = useState(false);
  const [loadingMsg, setLoadingMsg]   = useState('');
  const [error, setError]             = useState('');
  const [fullscreen, setFullscreen]   = useState(null); // 'flowchart' | 'mindmap' | null

  const handleGenerate = useCallback(async () => {
    setLoading(true);
    setError('');
    setVisual(null);
    try {
      setLoadingMsg('Fetching document content…');
      const text = await learningService.fetchDocumentText(documentId);

      setLoadingMsg('Generating visual diagrams… this may take a moment.');
      const result = await learningService.generateVisual(
        text,
        diagramType === 'both' ? null : diagramType,
      );
      setVisual(result);
    } catch (err) {
      setError(err.message || 'Visual generation failed. Please try again.');
    } finally {
      setLoading(false);
      setLoadingMsg('');
    }
  }, [documentId, diagramType]);

  // Diagrams are served at /diagrams/<filename>; proxy rewrites /api → backend root
  const imgSrc = (url) => (url ? `/api${url}` : null);

  return (
    <div className="visual-panel">
      {/* ── Controls ─────────────────────────────────────────────────── */}
      <div className="visual-controls card">
        <div className="visual-controls-row">
          <label className="notes-control-group">
            <span className="notes-control-label">Diagram Type</span>
            <select
              className="notes-select"
              value={diagramType}
              onChange={(e) => setDiagramType(e.target.value)}
              aria-label="Diagram type"
              disabled={loading}
            >
              {DIAGRAM_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </label>

          <div className="visual-controls-actions">
            <button
              type="button"
              className="button button-primary"
              onClick={handleGenerate}
              disabled={loading}
              aria-busy={loading}
            >
              {loading ? 'Generating…' : visual ? 'Regenerate' : 'Generate Visual'}
            </button>
          </div>
        </div>
      </div>

      {/* ── Error ────────────────────────────────────────────────────── */}
      {error && (
        <p className="notes-error" role="alert">{error}</p>
      )}

      {/* ── Loading ──────────────────────────────────────────────────── */}
      {loading && (
        <div className="notes-loading card" role="status" aria-live="polite">
          <span className="notes-loading-spinner" aria-hidden="true" />
          <span>{loadingMsg}</span>
        </div>
      )}

      {/* ── Empty state ───────────────────────────────────────────────── */}
      {!loading && !visual && !error && (
        <div className="notes-empty card">
          <span className="notes-empty-icon" aria-hidden="true">🗺️</span>
          <p>
            Select a diagram type and click <strong>Generate Visual</strong> to
            create a visual learning diagram from your document.
          </p>
        </div>
      )}

      {/* ── Diagrams ─────────────────────────────────────────────────── */}
      {!loading && visual && (
        <div className="visual-results">
          {visual.title && (
            <div className="visual-meta card">
              <h2 className="visual-title">{visual.title}</h2>
              {visual.description && (
                <p className="visual-description">{visual.description}</p>
              )}
            </div>
          )}

          <div className="visual-diagrams-grid">
            {visual.flowchart_url && (
              <DiagramCard
                label="Flowchart"
                src={imgSrc(visual.flowchart_url)}
                onFullscreen={() => setFullscreen('flowchart')}
              />
            )}
            {visual.mindmap_url && (
              <DiagramCard
                label="Mind Map"
                src={imgSrc(visual.mindmap_url)}
                onFullscreen={() => setFullscreen('mindmap')}
              />
            )}
          </div>
        </div>
      )}

      {/* ── Fullscreen overlay ───────────────────────────────────────── */}
      {fullscreen && visual && (
        <div
          className="visual-fullscreen-overlay"
          role="dialog"
          aria-modal="true"
          aria-label={`${fullscreen === 'flowchart' ? 'Flowchart' : 'Mind Map'} fullscreen view`}
          onClick={() => setFullscreen(null)}
        >
          <button
            type="button"
            className="visual-fullscreen-close"
            onClick={() => setFullscreen(null)}
            aria-label="Close fullscreen"
          >
            ✕
          </button>
          <img
            src={imgSrc(fullscreen === 'flowchart' ? visual.flowchart_url : visual.mindmap_url)}
            alt={fullscreen === 'flowchart' ? 'Flowchart diagram' : 'Mind map diagram'}
            className="visual-fullscreen-img"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  );
}

function DiagramCard({ label, src, onFullscreen }) {
  return (
    <div className="visual-diagram-card card">
      <div className="visual-diagram-header">
        <span className="visual-diagram-label">{label}</span>
        <div className="visual-diagram-actions">
          <button
            type="button"
            className="button button-secondary visual-diagram-btn"
            onClick={onFullscreen}
            aria-label={`View ${label} fullscreen`}
          >
            ⛶ Fullscreen
          </button>
          <a
            href={src}
            download
            className="button button-secondary visual-diagram-btn"
            aria-label={`Download ${label}`}
          >
            ↓ Download
          </a>
        </div>
      </div>
      <div className="visual-diagram-viewer">
        <img
          src={src}
          alt={`${label} diagram`}
          className="visual-diagram-img"
        />
      </div>
    </div>
  );
}
