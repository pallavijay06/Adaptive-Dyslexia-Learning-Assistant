import { useState, useCallback, useRef, useEffect } from 'react';
import { learningService } from '../services/learningService';

/**
 * Listen Mode panel with sentence highlighting.
 *
 * Mirrors the Streamlit render_listen_mode() in app.py exactly:
 *
 * Timing algorithm (identical to Streamlit):
 *   - No timestamps exist in the audio file.
 *   - Each sentence is assigned a proportional slice of the total audio
 *     duration, weighted by its word count.
 *   - sentenceTimings[i] = { start, end } computed once on loadedmetadata.
 *   - On timeupdate / seeked: find the sentence whose window contains
 *     audio.currentTime and apply the "active" CSS class.
 *   - On ended: clear the active sentence.
 *
 * Audio events used (same as Streamlit JS):
 *   loadedmetadata, timeupdate, play, pause, seeked, ended
 */
export default function ListenModePanel({ documentId, simplifiedText }) {
  const [source, setSource]       = useState('original');
  const [audioUrl, setAudioUrl]   = useState(null);
  const [sentences, setSentences] = useState([]);   // string[]
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState('');
  const [generated, setGenerated] = useState(false);

  // Index of the currently active sentence (-1 = none)
  const [activeSentence, setActiveSentence] = useState(-1);

  const audioRef      = useRef(null);
  const timingsRef    = useRef([]);   // [{ start, end }]
  const sentenceRefs  = useRef([]);   // DOM refs for each sentence span

  const simplifiedReady = Boolean(simplifiedText?.trim());

  // ── Compute proportional timings (Streamlit algorithm) ──────────────────
  // Called once when audio metadata is loaded (duration is known).
  // Mirrors the Streamlit computeSentenceTimings() JS function exactly.
  const computeTimings = useCallback((duration, sentenceList) => {
    if (!duration || !sentenceList.length) { timingsRef.current = []; return; }

    const weights = sentenceList.map((s) => Math.max(1, s.trim().split(/\s+/).length));
    const totalWeight = weights.reduce((a, b) => a + b, 0);

    const timings = [];
    let start = 0;
    for (let i = 0; i < sentenceList.length; i++) {
      const len = (weights[i] / totalWeight) * duration;
      const end = Math.min(duration, start + len);
      timings.push({ start, end });
      start = end;
    }
    timingsRef.current = timings;
  }, []);

  // ── Find active sentence for a given currentTime ─────────────────────────
  // Mirrors Streamlit's findIndex logic exactly.
  const findActiveSentence = useCallback((currentTime, duration, ended) => {
    const timings = timingsRef.current;
    if (!timings.length) return -1;
    if (ended) return -1;

    let idx = timings.findIndex(
      (t) => currentTime >= t.start && currentTime < t.end,
    );
    if (idx === -1) {
      idx = currentTime >= duration ? timings.length - 1 : 0;
    }
    return idx;
  }, []);

  // ── Audio event handler ───────────────────────────────────────────────────
  const handleTimeUpdate = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const idx = findActiveSentence(audio.currentTime, audio.duration, false);
    setActiveSentence(idx);
  }, [findActiveSentence]);

  const handleLoadedMetadata = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    // sentences state is captured via closure — use the ref instead
    computeTimings(audio.duration, sentenceListRef.current);
    handleTimeUpdate();
  }, [computeTimings, handleTimeUpdate]);

  const handleEnded = useCallback(() => {
    setActiveSentence(-1);
  }, []);

  // Keep a ref to sentences so event handlers always see the latest value
  // without needing to be re-registered.
  const sentenceListRef = useRef([]);
  useEffect(() => {
    sentenceListRef.current = sentences;
  }, [sentences]);

  // ── Attach / detach audio event listeners ────────────────────────────────
  // Re-runs whenever audioUrl changes (new audio generated).
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('timeupdate',     handleTimeUpdate);
    audio.addEventListener('play',           handleTimeUpdate);
    audio.addEventListener('pause',          handleTimeUpdate);
    audio.addEventListener('seeked',         handleTimeUpdate);
    audio.addEventListener('ended',          handleEnded);

    return () => {
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('timeupdate',     handleTimeUpdate);
      audio.removeEventListener('play',           handleTimeUpdate);
      audio.removeEventListener('pause',          handleTimeUpdate);
      audio.removeEventListener('seeked',         handleTimeUpdate);
      audio.removeEventListener('ended',          handleEnded);
    };
  }, [audioUrl, handleLoadedMetadata, handleTimeUpdate, handleEnded]);

  // ── Generate audio ────────────────────────────────────────────────────────
  const handleGenerate = useCallback(async () => {
    setLoading(true);
    setError('');
    setAudioUrl(null);
    setSentences([]);
    setActiveSentence(-1);
    timingsRef.current = [];

    try {
      let data;
      if (source === 'simplified') {
        data = await learningService.generateAudioFromText(simplifiedText);
      } else {
        data = await learningService.generateAudio(documentId);
      }
      setAudioUrl(data.audio_url);
      setSentences(data.sentences ?? []);
      setGenerated(true);
    } catch (err) {
      setError(err.message || 'Could not generate audio. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [documentId, simplifiedText, source]);

  // ── Source change resets player ───────────────────────────────────────────
  const handleSourceChange = useCallback((val) => {
    setSource(val);
    setAudioUrl(null);
    setSentences([]);
    setActiveSentence(-1);
    setGenerated(false);
    timingsRef.current = [];
  }, []);

  return (
    <div className="listen-panel">
      {/* ── Controls ─────────────────────────────────────────────────── */}
      <div className="listen-controls card">
        <div className="listen-controls-header">
          <span className="listen-icon" aria-hidden="true">🎧</span>
          <div>
            <h2 className="listen-title">Listen Mode</h2>
            <p className="listen-subtitle">
              Generate an audio version of your document and listen at your own pace.
            </p>
          </div>
        </div>

        <fieldset className="listen-source-fieldset">
          <legend className="notes-control-label">What would you like to listen to?</legend>
          <div className="listen-source-options">
            <label className="listen-source-option">
              <input
                type="radio"
                name="listen-source"
                value="original"
                checked={source === 'original'}
                onChange={() => handleSourceChange('original')}
              />
              Original Document
            </label>
            <label className={`listen-source-option${!simplifiedReady ? ' listen-source-option--disabled' : ''}`}>
              <input
                type="radio"
                name="listen-source"
                value="simplified"
                checked={source === 'simplified'}
                disabled={!simplifiedReady}
                onChange={() => handleSourceChange('simplified')}
              />
              Simplified Notes
              {!simplifiedReady && (
                <span className="listen-source-hint"> (generate Simplified Notes first)</span>
              )}
            </label>
          </div>
        </fieldset>

        <button
          type="button"
          className="button button-primary"
          onClick={handleGenerate}
          disabled={loading || (source === 'simplified' && !simplifiedReady)}
          aria-busy={loading}
        >
          {loading ? 'Generating Audio…' : generated ? 'Regenerate Audio' : 'Generate Audio'}
        </button>
      </div>

      {/* ── Error ────────────────────────────────────────────────────── */}
      {error && <p className="notes-error" role="alert">{error}</p>}

      {/* ── Loading ──────────────────────────────────────────────────── */}
      {loading && (
        <div className="notes-loading card" role="status" aria-live="polite">
          <span className="notes-loading-spinner" aria-hidden="true" />
          <span>Generating audio — this may take a moment…</span>
        </div>
      )}

      {/* ── Audio Player + Sentence Transcript ───────────────────────── */}
      {!loading && audioUrl && (
        <div className="listen-player card">
          {/*
            key={audioUrl} forces React to unmount/remount the <audio> element
            whenever the URL changes so the browser loads the new stream.
          */}
          <audio
            key={audioUrl}
            ref={audioRef}
            className="listen-audio"
            src={audioUrl}
            controls
            aria-label="Document audio player"
          >
            Your browser does not support the audio element.
          </audio>

          <a
            className="button button-secondary listen-download"
            href={audioUrl}
            download
            aria-label="Download audio file"
          >
            ⬇ Download Audio
          </a>

          {/* ── Sentence transcript with highlighting ─────────────── */}
          {sentences.length > 0 && (
            <div className="listen-transcript" aria-live="polite" aria-label="Text being read">
              <p className="listen-transcript-label">Text being read:</p>
              <p className="listen-transcript-text">
                {sentences.map((sentence, i) => (
                  <span
                    key={i}
                    ref={(el) => { sentenceRefs.current[i] = el; }}
                    className={`listen-sentence${activeSentence === i ? ' listen-sentence--active' : ''}`}
                  >
                    {sentence}{' '}
                  </span>
                ))}
              </p>
            </div>
          )}
        </div>
      )}

      {/* ── Empty state ───────────────────────────────────────────────── */}
      {!loading && !audioUrl && !error && (
        <div className="notes-empty card">
          <span className="notes-empty-icon" aria-hidden="true">🎧</span>
          <p>
            Click <strong>Generate Audio</strong> to create a spoken version of your{' '}
            {source === 'simplified' ? 'simplified notes' : 'document'}.
          </p>
        </div>
      )}
    </div>
  );
}
