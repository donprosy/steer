import { useEffect, useRef, useState } from "react";
import Icon from "../components/Icon.jsx";
import { PageHeading } from "../components/UI.jsx";
import { aiApi } from "../services/aiApi.js";

const suggestedQuestions = [
  "Analyze my business performance.",
  "Show my monthly profit.",
  "What are my best-selling products?",
  "Analyze my expenses.",
  "Give me business improvement recommendations.",
];

function formatTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("en-NG", { hour: "numeric", minute: "2-digit" }).format(date);
}

export default function AssistantPage({ businessId }) {
  const [conversations, setConversations] = useState([]);
  const [activeConversation, setActiveConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [period, setPeriod] = useState("this_month");
  const [usage, setUsage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [retryText, setRetryText] = useState("");
  const messageEnd = useRef(null);

  async function loadConversations(selectConversationId) {
    const [conversationPayload, usagePayload] = await Promise.all([
      aiApi.listConversations(businessId),
      aiApi.getUsage(businessId),
    ]);
    const rows = conversationPayload.conversations || [];
    setConversations(rows);
    setUsage(usagePayload.usage);
    if (selectConversationId) {
      const payload = await aiApi.getConversation(businessId, selectConversationId);
      setActiveConversation(payload.conversation);
      setMessages(payload.conversation.messages || []);
    } else if (rows.length) {
      const payload = await aiApi.getConversation(businessId, rows[0].id);
      setActiveConversation(payload.conversation);
      setMessages(payload.conversation.messages || []);
    } else {
      setActiveConversation(null);
      setMessages([]);
    }
  }

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    loadConversations()
      .catch((failure) => { if (active) setError(failure.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [businessId]);

  useEffect(() => {
    messageEnd.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, sending]);

  async function openConversation(conversation) {
    setError("");
    try {
      const payload = await aiApi.getConversation(businessId, conversation.id);
      setActiveConversation(payload.conversation);
      setMessages(payload.conversation.messages || []);
    } catch (failure) {
      setError(failure.message);
    }
  }

  async function createConversation() {
    setError("");
    try {
      const payload = await aiApi.createConversation(businessId, "New business conversation");
      await loadConversations(payload.conversation.id);
    } catch (failure) {
      setError(failure.message);
    }
  }

  async function deleteConversation() {
    if (!activeConversation || !window.confirm("Delete this AI conversation?")) return;
    setError("");
    try {
      await aiApi.deleteConversation(businessId, activeConversation.id);
      await loadConversations();
    } catch (failure) {
      setError(failure.message);
    }
  }

  async function sendMessage(event, overrideMessage) {
    event?.preventDefault();
    const text = (overrideMessage ?? input).trim();
    if (!text || sending) return;
    setSending(true);
    setError("");
    setRetryText("");
    const requestId = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setMessages((current) => [...current, {
      id: `local-user-${requestId}`,
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    }]);
    setInput("");
    try {
      const payload = await aiApi.chat(businessId, {
        conversation_id: activeConversation?.id,
        message: text,
        period,
        request_id: requestId,
      });
      setActiveConversation(payload.conversation);
      setMessages(payload.conversation.messages || []);
      setUsage(payload.usage);
      await loadConversations(payload.conversation.id);
    } catch (failure) {
      setRetryText(text);
      setError(failure.message);
    } finally {
      setSending(false);
    }
  }

  async function retryMessage() {
    if (!retryText) return;
    await sendMessage(null, retryText);
  }

  return (
    <>
      <PageHeading
        eyebrow="AI BUSINESS ASSISTANT"
        title="Steer Assistant"
        description="Analyze authorized business records. Recommendations are generated assistance, not guaranteed financial advice."
        action={<label className="select-wrap"><span>Period</span><select value={period} onChange={(event) => setPeriod(event.target.value)}><option value="today">Today</option><option value="this_week">This week</option><option value="this_month">This month</option><option value="this_year">This year</option></select></label>}
      />
      {error && <div className="ai-error" role="alert"><span>{error}</span>{retryText && <button type="button" onClick={retryMessage}>Retry</button>}</div>}
      <div className="assistant-layout">
        <aside className="assistant-sidebar panel">
          <button type="button" className="primary-button" onClick={createConversation}><Icon name="sparkles" size={15} />New conversation</button>
          <div className="assistant-conversation-list">
            {conversations.map((conversation) => (
              <button
                type="button"
                key={conversation.id}
                className={activeConversation?.id === conversation.id ? "is-active" : ""}
                onClick={() => openConversation(conversation)}
              >
                <b>{conversation.title}</b>
                <small>{formatTime(conversation.updated_at)}</small>
              </button>
            ))}
            {!conversations.length && <p className="assistant-empty">No conversations yet.</p>}
          </div>
          {usage && <div className="ai-usage"><span>AI replies</span><strong>{usage.reply_count} / {usage.limit}</strong><div><i style={{ width: `${Math.min(100, (usage.reply_count / usage.limit) * 100)}%` }} /></div><small>{usage.remaining} remaining this month</small></div>}
        </aside>
        <section className="assistant-chat panel">
          <div className="assistant-chat__header">
            <div><span className="assistant-avatar"><Icon name="sparkles" size={18} /></span><div><b>{activeConversation?.title || "New business conversation"}</b><small>Read-only business analysis</small></div></div>
            {activeConversation && <button type="button" className="quiet-button" onClick={deleteConversation}>Clear conversation</button>}
          </div>
          <div className="assistant-messages" aria-live="polite">
            {loading ? <div className="empty-state">Loading conversations…</div> : messages.length ? messages.map((message) => (
              <div key={message.id} className={`assistant-message assistant-message--${message.role}`}>
                <span>{message.role === "assistant" ? "Steer AI" : "You"} · {formatTime(message.created_at)}</span>
                <div>{message.content}</div>
              </div>
            )) : (
              <div className="assistant-welcome">
                <span className="assistant-welcome__icon"><Icon name="sparkles" size={22} /></span>
                <h2>How can I help your business?</h2>
                <p>Ask about sales, profit, expenses, customers, stock or recent performance.</p>
                <div className="assistant-suggestions">
                  {suggestedQuestions.map((question) => <button type="button" key={question} onClick={(event) => sendMessage(event, question)}>{question}</button>)}
                </div>
              </div>
            )}
            {sending && <div className="assistant-message assistant-message--assistant"><span>Steer AI</span><div className="assistant-typing"><i /><i /><i /></div></div>}
            <div ref={messageEnd} />
          </div>
          <form className="assistant-composer" onSubmit={sendMessage}>
            <textarea
              value={input}
              maxLength={4000}
              rows={2}
              placeholder="Ask about your business…"
              aria-label="Message Steer Assistant"
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  sendMessage(event);
                }
              }}
            />
            <button type="submit" className="primary-button" disabled={sending || !input.trim()} aria-label="Send message"><Icon name="arrowRight" size={17} /></button>
          </form>
          <p className="assistant-footnote">Business analysis is read-only. AI responses may contain errors; verify important decisions against your reports.</p>
        </section>
      </div>
    </>
  );
}
