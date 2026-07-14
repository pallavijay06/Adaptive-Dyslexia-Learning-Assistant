import { useState } from 'react';
import { adaptiveService } from '../services/adaptiveService';

/**
 * RevisionPanel
 *
 * Receives revision_topics from the backend-generated adaptive plan step.
 * Calls POST /adaptive-plan/revision-notes and displays the result.
 * Contains zero adaptive business logic.
 */
export default function RevisionPanel({ revisionTopics = [], revisionReason }) {
  const [notes, setNotes]     = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');

  const handleGenerate = async () => {
    setLoading(true);
    setError('');
    setNotes('');
    try {
      const data = await adaptiveService.generateRevisionNotes(revisionTopics);
      setNotes(data.revision_notes);
    } catch (err) {
      setError(err.message || 'Failed to generate revision notes.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {revisionReason && (
        <p style={{ marginBottom: '0.75rem', fontSize: '0.875rem', color: 'var(--color-muted, #6b7280)' }}>
          <strong>Why revision?</strong> {revisionReason}
        </p>
      )}

      {revisionTopics.length > 0 && (
        <div style={{ marginBottom: '1rem' }}>
          <p style={{ margin: '0 0 0.4rem', fontSize: '0.875rem', fontWeight: 600 }}>Topics to revise:</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
            {revisionTopics.map((t, i) => (
              <span key={i} style={{
                background: 'var(--color-surface-alt, #f3f4f6)',
                borderRadius: '4px', padding: '0.1rem 0.5rem',
                fontSize: '0.85rem',
              }}>{t}</span>
            ))}
          </div>
        </div>
      )}

      {!notes && (
        <button
          type="button"
          className="button button-primary"
          onClick={handleGenerate}
          disabled={loading || revisionTopics.length === 0}
        >
          {loading ? 'Generating…' : 'Generate Revision Notes'}
        </button>
      )}

      {error && (
        <p className="upload-error" role="alert" style={{ marginTop: '0.75rem' }}>{error}</p>
      )}

      {notes && (
        <div style={{ marginTop: '1rem' }}>
          <h4 style={{ marginTop: 0, marginBottom: '0.5rem' }}>Revision Notes</h4>
          <pre style={{
            whiteSpace: 'pre-wrap', wordBreak: 'break-word',
            background: 'var(--color-surface-alt, #f9fafb)',
            border: '1px solid var(--color-border, #e5e7eb)',
            borderRadius: '8px', padding: '1rem',
            fontSize: '0.9rem', lineHeight: 1.6,
          }}>{notes}</pre>
        </div>
      )}
    </div>
  );
}
