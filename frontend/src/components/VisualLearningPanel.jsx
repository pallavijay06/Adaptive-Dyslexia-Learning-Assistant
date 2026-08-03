import { useState, useCallback } from 'react';
import { learningService } from '../services/learningService';

export default function VisualLearningPanel({ documentId }) {
  const [visual, setVisual]         = useState(null);
  const [loading, setLoading]       = useState(false);
  const [loadingMsg, setLoadingMsg] = useState('');
  const [error, setError]           = useState('');
  const [fullscreen, setFullscreen] = useState(null);

  const handleGenerate = useCallback(async () => {
    setLoading(true);
    setError('');
    setVisual(null);
    try {
      setLoadingMsg('Fetching document content…');
      const text = await learningService.fetchDocumentText(documentId);

      setLoadingMsg('Generating flowchart… this may take a moment.');
      const result = await learningService.generateVisual(text);
      setVisual(result);
    } catch (err) {
      setError(err.message || 'Visual generation failed. Please try again.');
    } finally {
      setLoading(false);
      setLoadingMsg('');
    }
  }, [documentId]);

  // Diagrams are served at /diagrams/<filename>; proxy rewrites /api → backend root
  const imgSrc = (url) => (url ? `/api${url}` : null);

  return (
    <div className="visual-panel">
      {/* ── Controls ─────────────────────────────────────────────────── */}
      <div className="visual-controls card">
        <div className="visual-controls-row">
          <div className="visual-controls-actions">
            <button
              type="button"
              className="button button-primary"
              onClick={handleGenerate}
              disabled={loading}
              aria-busy={loading}
            >
              {loading ? 'Generating…' : visual ? 'Regenerate Flowchart' : 'Generate Flowchart'}
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
          <span className="notes-empty-icon" aria-hidden="true">�</span>
          <p>
            Click <strong>Generate Flowchart</strong> to create a flowchart from your document.
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
          </div>
        </div>
      )}

      {/* ── Fullscreen overlay ───────────────────────────────────────── */}
      {fullscreen && visual && (
        <div
          className="visual-fullscreen-overlay"
          role="dialog"
          aria-modal="true"
          aria-label="Flowchart fullscreen view"
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
            src={imgSrc(visual.flowchart_url)}
            alt="Flowchart diagram"
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
