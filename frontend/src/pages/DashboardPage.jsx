import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { dashboardService } from '../services/dashboardService';

const defaultDashboard = {
  overview: {},
  progress: {},
  recommendations: [],
  badges: [],
  learning_mode_usage: [],
  learner_profile: {},
  learning_performance: {},
  learning_behaviour: {},
  adaptive_intelligence: {},
};

function isMissingValue(value) {
  return value === null || value === undefined || value === '';
}

function formatValue(value) {
  if (isMissingValue(value)) {
    return 'Not Available';
  }
  return value;
}

function formatMetricValue(value) {
  if (isMissingValue(value)) {
    return 'Not Available';
  }

  if (typeof value === 'number') {
    return `${value}%`;
  }

  return value;
}

function formatLearningPathStep(step) {
  if (step == null) {
    return 'Not Available';
  }

  if (typeof step === 'string') {
    return step;
  }

  if (typeof step === 'object') {
    if (step.action === 'learning_mode' && step.mode) {
      return `Step ${step.step ?? '•'}: ${step.mode}`;
    }
    if (step.action === 'quiz') {
      return `Step ${step.step ?? '•'}: Quiz (${step.quiz_length ?? 'unknown'} questions)`;
    }
    return JSON.stringify(step);
  }

  return String(step);
}

function MetricBar({ value }) {
  if (isMissingValue(value)) {
    return <p className="metric-placeholder">TODO: expose this field from the backend</p>;
  }

  const numericValue = typeof value === 'number' ? value : Number.parseFloat(String(value));
  if (!Number.isFinite(numericValue)) {
    return <p className="metric-placeholder">TODO: expose this field from the backend</p>;
  }

  const safeWidth = Math.min(100, Math.max(0, numericValue));

  return (
    <div className="metric-bar" aria-hidden="true">
      <div className="metric-bar-fill" style={{ width: `${safeWidth}%` }} />
    </div>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [dashboard, setDashboard] = useState(defaultDashboard);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user?.id) {
      setLoading(false);
      return;
    }

    let isMounted = true;
    const loadDashboard = async () => {
      setLoading(true);
      setError('');

      try {
        const data = await dashboardService.getDashboard(user.id);
        if (isMounted) {
          setDashboard({
            ...defaultDashboard,
            ...data,
          });
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message || 'Unable to load dashboard data.');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    loadDashboard();

    return () => {
      isMounted = false;
    };
  }, [user?.id]);

  const overview = dashboard.overview ?? {};
  const progress = dashboard.progress ?? {};
  const recommendations = dashboard.recommendations ?? [];
  const badges = dashboard.badges ?? [];
  const learningModeUsage = dashboard.learning_mode_usage ?? [];
  const learnerProfile = dashboard.learner_profile ?? {};
  const learningPerformance = dashboard.learning_performance ?? {};
  const learningBehaviour = dashboard.learning_behaviour ?? {};
  const adaptiveIntelligence = dashboard.adaptive_intelligence ?? {};
  const welcomeName = overview.student_name || '';
  const latestRecommendation = recommendations[0] ?? null;

  return (
    <div className="dashboard-page">
      <section className="card hero-card" aria-labelledby="dashboard-welcome">
        <p className="eyebrow">Welcome Back</p>
        <h2 id="dashboard-welcome">{welcomeName ? `Hello, ${welcomeName} 👋` : 'Hello 👋'}</h2>
        <p className="hero-copy">Ready for today's learning session?</p>
      </section>

      {loading && <div className="card loading-card">Loading your dashboard…</div>}
      {error && !loading && <div className="card error-card">{error}</div>}

      {!loading && !error && (
        <section className="dashboard-grid dashboard-grid--adaptive" aria-label="Adaptive learner profile dashboard">
          <article className="card dashboard-card dashboard-card--adaptive">
            <div className="card-heading">
              <h3>Learner Profile</h3>
              <p className="card-subtitle">Backend values only</p>
            </div>
            <div className="metric-table">
              <div className="metric-row">
                <span>Teaching Style</span>
                <strong>{formatValue(learnerProfile.teaching_style)}</strong>
              </div>
              <div className="metric-row">
                <span>Preferred Learning Mode</span>
                <strong>{formatValue(learnerProfile.preferred_learning_mode)}</strong>
              </div>
              <div className="metric-row">
                <span>Learning Strategy</span>
                <strong>{formatValue(learnerProfile.learning_strategy)}</strong>
              </div>
              <div className="metric-row">
                <span>Comprehension Level</span>
                <strong>{formatValue(learnerProfile.comprehension_level)}</strong>
              </div>
            </div>
          </article>

          <article className="card dashboard-card dashboard-card--adaptive">
            <div className="card-heading">
              <h3>Learning Performance</h3>
              <p className="card-subtitle">Backend performance scores</p>
            </div>
            <div className="metric-stack">
              <div className="metric-item">
                <div className="metric-item-label">Comprehension Score</div>
                <MetricBar value={learningPerformance.comprehension_score} />
                <div className="metric-value">{formatMetricValue(learningPerformance.comprehension_score)}</div>
              </div>
              <div className="metric-item">
                <div className="metric-item-label">Quiz Accuracy Score</div>
                <MetricBar value={learningPerformance.quiz_accuracy_score} />
                <div className="metric-value">{formatMetricValue(learningPerformance.quiz_accuracy_score)}</div>
              </div>
            </div>
          </article>

          <article className="card dashboard-card dashboard-card--adaptive">
            <div className="card-heading">
              <h3>Learning Behaviour</h3>
              <p className="card-subtitle">Backend behaviour metrics</p>
            </div>
            <div className="metric-table">
              <div className="metric-row">
                <span>Behaviour Analytics Score</span>
                <strong>{formatMetricValue(learningBehaviour.behaviour_analytics_score)}</strong>
              </div>
              <div className="metric-row">
                <span>Mode Engagement Score</span>
                <strong>{formatMetricValue(learningBehaviour.mode_engagement_score)}</strong>
              </div>
              <div className="metric-row">
                <span>Mode Retention Score</span>
                <strong>{formatMetricValue(learningBehaviour.mode_retention_score)}</strong>
              </div>
            </div>
            <div className="metric-section">
              <div className="metric-item-label">Learning Modes</div>
              {learningModeUsage.length > 0 ? (
                <div className="mode-list">
                  {learningModeUsage.map((item, index) => (
                    <div key={`${item.mode}-${index}`} className="mode-list-item">
                      <span>{item.mode}</span>
                      <strong>{item.percentage}%</strong>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="metric-placeholder">No learning mode data available</p>
              )}
            </div>
          </article>

          <article className="card dashboard-card dashboard-card--adaptive">
            <div className="card-heading">
              <h3>Learning Progress</h3>
              <p className="card-subtitle">Backend progress counters</p>
            </div>
            <div className="metric-table">
              <div className="metric-row">
                <span>Documents Studied</span>
                <strong>{formatValue(progress.documents_studied)}</strong>
              </div>
              <div className="metric-row">
                <span>Topics Covered</span>
                <strong>{formatValue(progress.topics_covered)}</strong>
              </div>
              <div className="metric-row">
                <span>Concepts Learned</span>
                <strong>{formatValue(progress.concepts_learned)}</strong>
              </div>
              <div className="metric-row">
                <span>Quiz Attempts</span>
                <strong>{formatValue(progress.quiz_attempts)}</strong>
              </div>
              <div className="metric-row">
                <span>Current Streak</span>
                <strong>{formatValue(overview.current_streak)}</strong>
              </div>
              <div className="metric-row">
                <span>Total Study Time</span>
                <strong>{formatValue(overview.total_study_time)}</strong>
              </div>
            </div>
          </article>

          <article className="card dashboard-card dashboard-card--adaptive">
            <div className="card-heading">
              <h3>Adaptive Intelligence</h3>
              <p className="card-subtitle">Backend adaptive outputs</p>
            </div>
            <div className="metric-table">
              <div className="metric-row">
                <span>Recommended Learning Mode</span>
                <strong>{formatValue(dashboard.favorite_mode || null)}</strong>
              </div>
              <div className="metric-row">
                <span>Latest Recommendation</span>
                <strong>{latestRecommendation ? latestRecommendation.detail || latestRecommendation.title : 'Not Available'}</strong>
              </div>
            </div>
            {adaptiveIntelligence.recommended_learning_path && adaptiveIntelligence.recommended_learning_path.length > 0 && (
              <div className="metric-section">
                <div className="metric-item-label">Recommended Learning Path</div>
                <ol className="learning-path-list">
                  {adaptiveIntelligence.recommended_learning_path.map((step, index) => (
                    <li key={`learning-step-${index}`}>{formatLearningPathStep(step)}</li>
                  ))}
                </ol>
              </div>
            )}
            <div className="metric-section">
              <div className="metric-item-label">Badges</div>
              {badges.length > 0 ? (
                <ul className="chip-list chip-list--compact">
                  {badges.map((badge, index) => (
                    <li key={`${badge}-${index}`}>{badge}</li>
                  ))}
                </ul>
              ) : (
                <p className="metric-placeholder">No badges earned yet</p>
              )}
            </div>
          </article>

          <article className="card dashboard-card dashboard-card--adaptive">
            <div className="card-heading">
              <h3>Upload Document</h3>
              <p className="card-subtitle">Continue the current study flow</p>
            </div>
            <p>Continue by uploading a new document for the next study session.</p>
            <Link className="button button-primary" to="/upload">Go to Upload</Link>
          </article>
        </section>
      )}
    </div>
  );
}
