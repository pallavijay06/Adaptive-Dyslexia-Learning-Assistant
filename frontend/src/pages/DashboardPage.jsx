import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { dashboardService } from '../services/dashboardService';

const defaultDashboard = {
  overview: {},
  progress: {},
  recommendations: [],
  insights: [],
  badges: [],
  quiz_performance: {},
  concept_mastery: [],
  learning_mode_usage: [],
  timeline: [],
};

function formatValue(value) {
  if (value === null || value === undefined || value === '') {
    return '—';
  }
  return value;
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
  const insights = dashboard.insights ?? [];
  const badges = dashboard.badges ?? [];
  const quizPerformance = dashboard.quiz_performance ?? {};
  const conceptMastery = dashboard.concept_mastery ?? [];
  const learningModeUsage = dashboard.learning_mode_usage ?? [];
  const timeline = dashboard.timeline ?? [];
  const welcomeName = overview.student_name || '';

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
        <>
          <section className="dashboard-grid" aria-label="Dashboard overview cards">
            <article className="card dashboard-card">
              <h3>Upload</h3>
              <p>Continue by uploading a new document for the next study session.</p>
              <Link className="button button-primary" to="/upload">Go to Upload</Link>
            </article>

            <article className="card dashboard-card">
              <h3>Continue Learning</h3>
              <p>No backend recommendation card is available for this view.</p>
            </article>
          </section>

          <section className="dashboard-grid" aria-label="Progress summary">
            <article className="card dashboard-card stat-card">
              <h3>Documents studied</h3>
              <p className="stat-value">{formatValue(progress.documents_studied)}</p>
            </article>
            <article className="card dashboard-card stat-card">
              <h3>Topics covered</h3>
              <p className="stat-value">{formatValue(progress.topics_covered)}</p>
            </article>
            <article className="card dashboard-card stat-card">
              <h3>Concepts learned</h3>
              <p className="stat-value">{formatValue(progress.concepts_learned)}</p>
            </article>
            <article className="card dashboard-card stat-card">
              <h3>Questions asked</h3>
              <p className="stat-value">{formatValue(progress.questions_asked)}</p>
            </article>
          </section>

          <section className="dashboard-grid" aria-label="Dashboard overview data">
            <article className="card dashboard-card">
              <h3>Dashboard overview</h3>
              <ul className="detail-list">
                <li><span>Total study time</span><strong>{formatValue(overview.total_study_time)}</strong></li>
                <li><span>Learning sessions</span><strong>{formatValue(overview.total_learning_sessions)}</strong></li>
                <li><span>Days active</span><strong>{formatValue(overview.days_active)}</strong></li>
                <li><span>Current streak</span><strong>{formatValue(overview.current_streak)}</strong></li>
              </ul>
            </article>

            <article className="card dashboard-card">
              <h3>Profile summary</h3>
              <ul className="detail-list">
                <li><span>Name</span><strong>{formatValue(user?.name || overview.student_name)}</strong></li>
                <li><span>Email</span><strong>{formatValue(user?.email)}</strong></li>
                <li><span>Grade</span><strong>{formatValue(overview.grade)}</strong></li>
                <li><span>Institution</span><strong>{formatValue(overview.institution)}</strong></li>
              </ul>
            </article>
          </section>

          <section className="dashboard-grid" aria-label="Recommendations and insights">
            <article className="card dashboard-card wide-card">
              <h3>Recommendations</h3>
              {recommendations.length > 0 ? (
                <ul className="stack-list">
                  {recommendations.map((item, index) => (
                    <li key={`${item.title}-${index}`}>
                      <strong>{item.title}</strong>
                      <p>{item.detail}</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>No recommendations were returned by the backend.</p>
              )}
            </article>

            <article className="card dashboard-card wide-card">
              <h3>Insights</h3>
              {insights.length > 0 ? (
                <ul className="stack-list">
                  {insights.map((item, index) => (
                    <li key={`${item}-${index}`}>{item}</li>
                  ))}
                </ul>
              ) : (
                <p>No insights were returned by the backend.</p>
              )}
            </article>
          </section>

          <section className="dashboard-grid" aria-label="Progress details">
            <article className="card dashboard-card">
              <h3>Progress metrics</h3>
              <ul className="detail-list">
                <li><span>Quiz attempts</span><strong>{formatValue(progress.quiz_attempts)}</strong></li>
                <li><span>Quiz accuracy</span><strong>{formatValue(progress.quiz_accuracy)}</strong></li>
                <li><span>Comprehension score</span><strong>{formatValue(progress.comprehension_score)}</strong></li>
                <li><span>Average session duration</span><strong>{formatValue(progress.avg_session_duration)}</strong></li>
              </ul>
            </article>

            <article className="card dashboard-card">
              <h3>Quiz performance</h3>
              <ul className="detail-list">
                <li><span>Total quizzes</span><strong>{formatValue(quizPerformance.total_quizzes)}</strong></li>
                <li><span>Average score</span><strong>{formatValue(quizPerformance.average_score)}</strong></li>
                <li><span>Highest score</span><strong>{formatValue(quizPerformance.highest_score)}</strong></li>
                <li><span>Lowest score</span><strong>{formatValue(quizPerformance.lowest_score)}</strong></li>
              </ul>
            </article>
          </section>

          <section className="dashboard-grid" aria-label="Learning details">
            <article className="card dashboard-card">
              <h3>Badges</h3>
              {badges.length > 0 ? (
                <ul className="chip-list">
                  {badges.map((badge, index) => (
                    <li key={`${badge}-${index}`}>{badge}</li>
                  ))}
                </ul>
              ) : (
                <p>No badges were returned by the backend.</p>
              )}
            </article>

            <article className="card dashboard-card">
              <h3>Learning modes</h3>
              {learningModeUsage.length > 0 ? (
                <ul className="stack-list">
                  {learningModeUsage.map((item, index) => (
                    <li key={`${item.mode}-${index}`}>
                      <strong>{item.mode}</strong>
                      <p>{item.count} sessions · {item.percentage}%</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>No learning mode usage data was returned by the backend.</p>
              )}
            </article>
          </section>

          <section className="dashboard-grid" aria-label="Recent activity">
            <article className="card dashboard-card wide-card">
              <h3>Recent activity</h3>
              {timeline.length > 0 ? (
                <ul className="stack-list">
                  {timeline.map((item, index) => (
                    <li key={`${item.time}-${item.event}-${index}`}>
                      <strong>{item.time}</strong>
                      <p>{item.event}</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>No activity timeline data was returned by the backend.</p>
              )}
            </article>

            <article className="card dashboard-card wide-card">
              <h3>Concept mastery</h3>
              {conceptMastery.length > 0 ? (
                <ul className="stack-list">
                  {conceptMastery.map((item, index) => (
                    <li key={`${item['Concept Name']}-${index}`}>
                      <strong>{item['Concept Name']}</strong>
                      <p>{item['Current Status']} · {item['Mastery Score']}% mastery</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>No concept mastery data was returned by the backend.</p>
              )}
            </article>
          </section>
        </>
      )}
    </div>
  );
}
