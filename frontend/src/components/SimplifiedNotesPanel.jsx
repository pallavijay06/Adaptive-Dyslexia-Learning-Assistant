import React, { useState, useCallback, useRef, useMemo } from 'react';
import { learningService } from '../services/learningService';
import VocabularyPopover from './VocabularyPopover';
import WordExplorerPanel from './WordExplorerPanel';

// ── Accessibility option tables ────────────────────────────────────────────
const FONT_SIZES = {
  Small:         { px: 16 },
  Medium:        { px: 20 },
  Large:         { px: 24 },
  'Extra Large': { px: 28 },
};
const FONT_FAMILIES = ['Arial', 'Verdana', 'Courier'];
const CHARACTER_SPACING = { Normal: '0px', Relaxed: '2px', 'Extra Relaxed': '4px' };
const THEMES = {
  Light:  { bg: '#FFFFFF', text: '#1F2933', cardBg: '#F5F7FA', border: '#D9E2EC', vocabColor: '#1D4ED8' },
  Dark:   { bg: '#121826', text: '#F5F7FA', cardBg: '#1F2933', border: '#52606D', vocabColor: '#93C5FD' },
  Cream:  { bg: '#FFF8E7', text: '#2F2A1F', cardBg: '#F4E8C1', border: '#D6C79B', vocabColor: '#1D4ED8' },
  Yellow: { bg: '#FFF9C4', text: '#2B2B2B', cardBg: '#FFF59D', border: '#E6D75A', vocabColor: '#1D4ED8' },
};
const LINE_HEIGHT = 1.8;
const DEFAULT_PREFS = { fontSize: 'Medium', fontFamily: 'Arial', charSpacing: 'Normal', theme: 'Light' };

// ── Word difficulty heuristic (mirrors Streamlit vocabulary_popup.py) ──────
const STOP_WORDS = new Set([
  'about','above','after','again','because','before','between','could','during',
  'every','from','have','into','mainly','other','should','their','there','these',
  'thing','things','through','water','where','which','while','with','would',
]);
const GENERIC_WORDS = new Set([
  'understand','understanding','understood','learn','learns','learned','learning',
  'basic','rule','rules','together','topic','important','use','using','need',
  'needs','help','helps','helping',
]);
const BUILT_IN = new Set([
  'adaptation','byproduct','carbon','chlorophyll','chloroplast','condensation',
  'ecosystem','evaporation','glucose','mitochondria','nutrients','organism',
  'oxygen','photosynthesis','precipitation','required','respiration','sunlight',
  'transpiration',
]);

function isDifficult(word) {
  const w = word.toLowerCase();
  return (w.length >= 9 || BUILT_IN.has(w)) && !STOP_WORDS.has(w) && !GENERIC_WORDS.has(w);
}

function isTitleCase(line) {
  const words = line.split(/\s+/).filter(Boolean);
  if (!words.length) return false;
  return words.every((w) => /^[A-Z][a-z]*$/.test(w));
}

function parseBlocks(text) {
  if (!text?.trim()) return [];
  const blocks = [];
  let paraLines = [];
  let bulletItems = [];
  let lineIndex = 0;

  const flushPara = () => {
    if (!paraLines.length) return;
    blocks.push({ kind: 'paragraph', text: paraLines.join(' ') });
    paraLines = [];
  };
  const flushBullets = () => {
    if (!bulletItems.length) return;
    blocks.push({ kind: 'bullets', items: [...bulletItems] });
    bulletItems = [];
  };

  for (const raw of text.split('\n')) {
    const line = raw.trim();
    if (!line) { flushBullets(); flushPara(); lineIndex++; continue; }

    const cleanBullet = line.match(/^(?:[-*•]|\d+[.)]) (.+)$/);
    if (cleanBullet) { flushPara(); bulletItems.push(cleanBullet[1].trim()); lineIndex++; continue; }
    const looseBullet = line.match(/^[-*•]\s*/);
    if (looseBullet) { flushPara(); bulletItems.push(line.replace(/^[-*•]\s*/, '').trim()); lineIndex++; continue; }

    flushBullets();

    const hasPendingParagraph = paraLines.length > 0;
    const hasBlocks = blocks.length > 0;
    let isHeading = false;
    if (line.startsWith('#')) {
      isHeading = true;
    } else if (!hasPendingParagraph &&
               !/[.!?;,]$/.test(line) &&
               line.length <= 90 &&
               (lineIndex === 0 || hasBlocks || isTitleCase(line))) {
      isHeading = true;
    }

    if (isHeading) { flushPara(); blocks.push({ kind: 'heading', text: line.replace(/^#+\s*/, '') }); }
    else { paraLines.push(line); }
    lineIndex++;
  }
  flushBullets();
  flushPara();
  return blocks;
}

const WORD_RE = /\b([A-Za-z][A-Za-z'-]*)\b/g;

function tokeniseText(text, seenWords, vocabColor, onWordClick) {
  if (!text) return [];
  const parts = [];
  let last = 0;
  let m;
  WORD_RE.lastIndex = 0;
  while ((m = WORD_RE.exec(text)) !== null) {
    const word = m[1];
    const lower = word.toLowerCase().replace(/^'+|'+$/g, '');
    if (last < m.index) parts.push(text.slice(last, m.index));
    if (isDifficult(lower) && !seenWords.has(lower)) {
      seenWords.add(lower);
      parts.push(
        <button
          key={`${lower}-${m.index}`}
          type="button"
          className="vocab-word"
          style={{ color: vocabColor }}
          onClick={(e) => onWordClick(lower, e.currentTarget.getBoundingClientRect())}
          aria-label={`Look up: ${word}`}
        >
          {word}
        </button>
      );
    } else {
      parts.push(word);
    }
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

// ── Main component ─────────────────────────────────────────────────────────
export default function SimplifiedNotesPanel({ documentId, onNotesGenerated }) {
  const [prefs, setPrefs]   = useState(DEFAULT_PREFS);
  const [notes, setNotes]   = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState('');

  // Vocabulary popover state
  const [popover, setPopover] = useState(null);
  const [vocabLoading, setVocabLoading] = useState(false);
  const [vocabError, setVocabError]     = useState('');
  const [vocabData, setVocabData]       = useState(null);
  const vocabCache = useRef({});

  const theme = THEMES[prefs.theme];
  const fsPx  = FONT_SIZES[prefs.fontSize].px;
  const lsVal = CHARACTER_SPACING[prefs.charSpacing];

  const handleGenerate = useCallback(async () => {
    setLoading(true);
    setError('');
    setPopover(null);
    try {
      const text = await learningService.simplifyDocument(documentId);
      setNotes(text);
      onNotesGenerated?.(text);
    } catch (err) {
      setError(err.message || 'Could not generate notes. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [documentId]);

  const handleWordClick = useCallback(async (word, anchorRect) => {
    setPopover({ word, anchorRect });
    setVocabError('');
    setVocabData(null);

    if (vocabCache.current[word]) {
      setVocabData(vocabCache.current[word]);
      return;
    }

    setVocabLoading(true);
    try {
      const explanation = await learningService.explainWord(word);
      vocabCache.current[word] = explanation;
      setVocabData(explanation);
    } catch (err) {
      setVocabError(err.message || 'Could not load explanation.');
    } finally {
      setVocabLoading(false);
    }
  }, []);

  const closePopover = useCallback(() => {
    setPopover(null);
    setVocabData(null);
    setVocabError('');
  }, []);

  const setPref = (key, val) => setPrefs((p) => ({ ...p, [key]: val }));

  const renderedBlocks = useMemo(() => {
    if (!notes) return [];
    const blocks = parseBlocks(notes);
    const seenWords = new Set();
    return blocks.map((block, i) => {
      if (block.kind === 'heading') {
        return (
          <div key={i} className="notes-section-card" style={{ background: theme.cardBg, borderColor: theme.border }}>
            <h2 className="notes-heading" style={{ color: theme.text }}>
              {tokeniseText(block.text, seenWords, theme.vocabColor, handleWordClick)}
            </h2>
          </div>
        );
      }
      if (block.kind === 'bullets') {
        return (
          <div key={i} className="notes-section-card" style={{ background: theme.cardBg, borderColor: theme.border }}>
            <ul className="notes-bullet-list" style={{ color: theme.text }}>
              {block.items.map((item, j) => (
                <li key={j}>{tokeniseText(item, seenWords, theme.vocabColor, handleWordClick)}</li>
              ))}
            </ul>
          </div>
        );
      }
      return (
        <div key={i} className="notes-section-card" style={{ background: theme.cardBg, borderColor: theme.border }}>
          <p className="notes-paragraph" style={{ color: theme.text }}>
            {tokeniseText(block.text, seenWords, theme.vocabColor, handleWordClick)}
          </p>
        </div>
      );
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [notes, theme.vocabColor]);

  return (
    <div className="notes-panel">
      {/* ── Controls ─────────────────────────────────────────────────── */}
      <div className="notes-controls card">
        <div className="notes-controls-grid">
          <label className="notes-control-group">
            <span className="notes-control-label">Font Size</span>
            <select className="notes-select" value={prefs.fontSize} onChange={(e) => setPref('fontSize', e.target.value)} aria-label="Font size">
              {Object.keys(FONT_SIZES).map((k) => <option key={k} value={k}>{k}</option>)}
            </select>
          </label>
          <label className="notes-control-group">
            <span className="notes-control-label">Font Family</span>
            <select className="notes-select" value={prefs.fontFamily} onChange={(e) => setPref('fontFamily', e.target.value)} aria-label="Font family">
              {FONT_FAMILIES.map((f) => <option key={f} value={f}>{f}</option>)}
            </select>
          </label>
          <label className="notes-control-group">
            <span className="notes-control-label">Character Spacing</span>
            <select className="notes-select" value={prefs.charSpacing} onChange={(e) => setPref('charSpacing', e.target.value)} aria-label="Character spacing">
              {Object.keys(CHARACTER_SPACING).map((k) => <option key={k} value={k}>{k}</option>)}
            </select>
          </label>
          <label className="notes-control-group">
            <span className="notes-control-label">Theme</span>
            <select className="notes-select" value={prefs.theme} onChange={(e) => setPref('theme', e.target.value)} aria-label="Reading theme">
              {Object.keys(THEMES).map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </label>
        </div>
        <div className="notes-controls-actions">
          <button
            type="button"
            className="button button-primary"
            onClick={handleGenerate}
            disabled={loading}
            aria-busy={loading}
          >
            {loading ? 'Generating…' : notes ? 'Regenerate Notes' : 'Generate Simplified Notes'}
          </button>
          {notes && (
            <button
              type="button"
              className="button button-secondary"
              onClick={() => navigator.clipboard?.writeText(notes).catch(() => {})}
              aria-label="Copy notes to clipboard"
            >
              Copy
            </button>
          )}
        </div>
      </div>

      {/* ── Error ────────────────────────────────────────────────────── */}
      {error && <p className="notes-error" role="alert">{error}</p>}

      {/* ── Loading ──────────────────────────────────────────────────── */}
      {loading && (
        <div className="notes-loading card" role="status" aria-live="polite">
          <span className="notes-loading-spinner" aria-hidden="true" />
          <span>Generating Simplified Notes…</span>
        </div>
      )}

      {/* ── Empty state ───────────────────────────────────────────────── */}
      {!loading && !notes && !error && (
        <div className="notes-empty card">
          <span className="notes-empty-icon" aria-hidden="true">📝</span>
          <p>Click <strong>Generate Simplified Notes</strong> to create a dyslexia-friendly version of your document.</p>
        </div>
      )}

      {/* ── Reading area ─────────────────────────────────────────────── */}
      {!loading && notes && (
        <div
          className="notes-reading-area"
          style={{
            background: theme.bg,
            color: theme.text,
            fontFamily: `"${prefs.fontFamily}", sans-serif`,
            fontSize: `${fsPx}px`,
            letterSpacing: lsVal,
            lineHeight: LINE_HEIGHT,
          }}
          aria-label="Simplified notes reading area"
        >
          <p className="notes-vocab-hint" style={{ color: theme.vocabColor }}>
            💡 Tap any <strong>highlighted word</strong> to see its meaning.
          </p>

          {renderedBlocks}
        </div>
      )}

      {/* ── Vocabulary Popover ────────────────────────────────────────── */}
      {popover && (
        <VocabularyPopover
          anchorRect={popover.anchorRect}
          explanation={vocabData}
          loading={vocabLoading}
          error={vocabError}
          onClose={closePopover}
        />
      )}

      {/* ── Word Explorer ─────────────────────────────────────────────── */}
      {/* Mirrors Streamlit: render_word_explorer() is called after         */}
      {/* render_learning_modes() on the same page, below the reading area. */}
      <div className="notes-word-explorer-divider" role="separator" aria-hidden="true" />
      <WordExplorerPanel />
    </div>
  );
}
