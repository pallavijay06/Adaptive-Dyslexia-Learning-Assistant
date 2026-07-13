import { useEffect, useMemo, useRef, useState } from 'react';
import { SendHorizonal, Sparkles, UserRound } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useDocument } from '../contexts/DocumentContext';
import { chatService } from '../services/chatService';

function formatTime(date) {
  return new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit',
  }).format(date);
}

function renderMarkdown(text) {
  const parts = text.split(/(```[\s\S]*?```|`[^`]+`)/g).filter(Boolean);
  return parts.map((part, index) => {
    if (part.startsWith('```') && part.endsWith('```')) {
      return <pre key={index} className="chat-code-block">{part.slice(3, -3)}</pre>;
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={index} className="chat-inline-code">{part.slice(1, -1)}</code>;
    }
    return <span key={index}>{part}</span>;
  });
}

export default function ChatPanel() {
  const { user } = useAuth();
  const { activeDocument } = useDocument();
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Hi! I can help explain this document, simplify ideas, and answer your questions.',
      timestamp: new Date(),
    },
  ]);
  const [draft, setDraft] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState('');
  const endRef = useRef(null);

  const documentId = activeDocument?.id ?? activeDocument?.document_id;

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed) return;

    const userMessage = {
      id: `${Date.now()}-user`,
      role: 'user',
      content: trimmed,
      timestamp: new Date(),
    };

    setMessages((current) => [...current, userMessage]);
    setDraft('');
    setError('');
    setIsTyping(true);

    try {
      const result = await chatService.sendMessage({
        message: trimmed,
        document_id: documentId,
        user_id: user?.id,
      });

      const assistantMessage = {
        id: `${Date.now()}-assistant`,
        role: 'assistant',
        content: result?.response || 'I could not generate a response right now.',
        timestamp: new Date(),
      };

      setMessages((current) => [...current, assistantMessage]);
    } catch (err) {
      setError(err.message || 'Unable to send your message right now.');
    } finally {
      setIsTyping(false);
    }
  };

  const statusText = useMemo(() => {
    if (error) return error;
    if (isTyping) return 'AI Tutor is thinking…';
    return 'Ask anything about your learning material.';
  }, [error, isTyping]);

  return (
    <section className="chat-panel card" aria-label="AI Tutor chat">
      <header className="chat-header">
        <div className="chat-profile">
          <div className="chat-avatar chat-avatar--assistant">
            <Sparkles size={18} />
          </div>
          <div>
            <h3>AI Tutor</h3>
            <p>{statusText}</p>
          </div>
        </div>
      </header>

      <div className="chat-thread" role="log" aria-live="polite">
        {messages.map((message) => (
          <div key={message.id} className={`chat-bubble-row ${message.role === 'user' ? 'chat-bubble-row--user' : ''}`}>
            <div className={`chat-avatar ${message.role === 'user' ? 'chat-avatar--user' : 'chat-avatar--assistant'}`}>
              {message.role === 'user' ? <UserRound size={16} /> : <Sparkles size={16} />}
            </div>
            <div className={`chat-bubble ${message.role === 'user' ? 'chat-bubble--user' : 'chat-bubble--assistant'}`}>
              <div className="chat-bubble-content">{renderMarkdown(message.content)}</div>
              <div className="chat-bubble-meta">{formatTime(message.timestamp)}</div>
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="chat-bubble-row">
            <div className="chat-avatar chat-avatar--assistant">
              <Sparkles size={16} />
            </div>
            <div className="chat-bubble chat-bubble--assistant chat-bubble--typing">
              <span className="chat-dot" />
              <span className="chat-dot" />
              <span className="chat-dot" />
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form className="chat-composer" onSubmit={handleSubmit}>
        <input
          className="chat-input"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Ask the tutor about your material"
          aria-label="Message the AI tutor"
        />
        <button type="submit" className="chat-send-button" disabled={!draft.trim()}>
          <SendHorizonal size={18} />
        </button>
      </form>
    </section>
  );
}
