import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useDocument } from '../contexts/DocumentContext';
import { useJourney } from '../contexts/JourneyContext';
import { adaptiveService } from '../services/adaptiveService';

export default function LearningSelectionRoute() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { activeDocument } = useDocument();
  const { setAdaptiveLearningPlan, setDocumentId } = useJourney();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!activeDocument) {
    return (
      <section className="card" style={{ maxWidth: '560px', margin: '0 auto' }}>
        <h2>No document loaded</h2>
        <p>Please upload a document before choosing a learning experience.</p>
        <button
          type="button"
          className="button button-primary"
          onClick={() => navigate('/upload')}
          style={{ marginTop: '1rem' }}
        >
          Go to Upload
        </button>
      </section>
    );
  }

  const handleStartJourney = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await adaptiveService.generatePlan(user.id);
      setAdaptiveLearningPlan(data.plan);
      setDocumentId(activeDocument.document_id ?? activeDocument.id ?? null);
      navigate('/journey');
    } catch (err) {
      setError(err.message || 'Could not start your journey. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="learning-selection-page">
      <section className="card learning-selection-header" aria-labelledby="ls-heading">
        <p className="eyebrow">Document ready</p>
        <h2 id="ls-heading">Choose a Learning Experience</h2>
        <p className="hero-copy">
          <strong>{activeDocument.file_name}</strong> has been processed and is ready.
          Select how you would like to study it.
        </p>
      </section>

      {error && (
        <p className="upload-error" role="alert" style={{ textAlign: 'center' }}>
          {error}
        </p>
      )}

      <div className="learning-selection-grid">
        <article className="card learning-selection-card learning-selection-card--primary" aria-labelledby="ls-journey-title">
          <div className="ls-card-icon" aria-hidden="true">🌟</div>
          <h3 id="ls-journey-title">Personalized Learning Journey</h3>
          <p>
            A guided learning experience generated specifically for you.
            The assistant recommends the best sequence of activities based on your learner profile.
          </p>
          <button
            type="button"
            className="button button-primary"
            onClick={handleStartJourney}
            disabled={loading}
            aria-busy={loading}
          >
            {loading ? 'Loading Journey…' : 'Start Journey'}
          </button>
        </article>

        <article className="card learning-selection-card" aria-labelledby="ls-manual-title">
          <div className="ls-card-icon" aria-hidden="true">📚</div>
          <h3 id="ls-manual-title">Explore Learning Modes</h3>
          <p>
            Choose any learning mode manually. Explore notes, audio, visuals,
            vocabulary, quizzes, STEM support, and the AI tutor at your own pace.
          </p>
          <button
            type="button"
            className="button button-primary"
            onClick={() => navigate('/manual-learning')}
            disabled={loading}
          >
            Explore
          </button>
        </article>
      </div>

      <div style={{ textAlign: 'center', marginTop: '0.5rem' }}>
        <button
          type="button"
          className="button button-secondary"
          onClick={() => navigate('/dashboard')}
          disabled={loading}
        >
          Return to Dashboard
        </button>
      </div>
    </div>
  );
}
