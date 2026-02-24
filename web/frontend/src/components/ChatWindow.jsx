import { useState, useRef, useEffect } from "react";
import Markdown from "react-markdown";

const TOOL_LABELS = {
  search_knowledge_base: { loading: "Searching knowledge base...", done: "Searched knowledge base" },
  create_ticket: { loading: "Creating support ticket...", done: "Created support ticket" },
  check_order: { loading: "Checking order status...", done: "Checked order status" },
  save_briefing: { loading: "Saving briefing...", done: "Saved briefing" },
  WebSearch: { loading: "Searching the web...", done: "Web search complete" },
  WebFetch: { loading: "Fetching web page...", done: "Fetched web page" },
  Bash: { loading: "Running analysis...", done: "Analysis complete" },
  Read: { loading: "Reading data...", done: "Read data" },
  Write: { loading: "Writing file...", done: "Wrote file" },
  Glob: { loading: "Searching files...", done: "File search complete" },
  Grep: { loading: "Searching content...", done: "Content search complete" },
};

function getToolLabel(text, isLoading) {
  let name = text.replace("Using: ", "");
  if (name.startsWith("mcp__")) name = name.split("__").pop();
  const label = TOOL_LABELS[name];
  if (!label) return isLoading ? `Running ${name}...` : `Used ${name}`;
  return isLoading ? label.loading : label.done;
}

const SUGGESTIONS = {
  customer_support: [
    "Do you offer free shipping?",
    "Where is my order ORD-002?",
    "How do I return an item?",
    "How do I reset my password?",
    "What's your warranty policy?",
  ],
  meeting_prep: [
    "Prepare a briefing for a meeting with Stripe",
    "Tell me about Anthropic",
    "Research Shopify for a sales call",
  ],
  retail_analyzer: [
    "What's my total revenue?",
    "Which products are low on stock?",
    "Who are my top 3 customers?",
    "Show me sales by category",
    "What are my profit margins?",
  ],
};

export default function ChatWindow({ agent }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState("Connecting...");
  const [isLoading, setIsLoading] = useState(false);
  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    setMessages([]);
    setStatus("Connecting...");

    const ws = new WebSocket(`ws://localhost:8000/ws/${agent.id}`);
    wsRef.current = ws;

    ws.onopen = () => setStatus("Connected");
    ws.onclose = () => setStatus("Disconnected");
    ws.onerror = () => setStatus("Connection error");

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      switch (data.type) {
        case "assistant":
          setMessages((prev) => [
            ...prev.map(m => m.loading ? { ...m, loading: false } : m),
            { role: "assistant", text: data.text },
          ]);
          setIsLoading(false);
          break;
        case "tool":
          setMessages((prev) => [...prev, { role: "tool", text: data.text, loading: true }]);
          break;
        case "status":
          if (data.text === "Thinking...") setIsLoading(true);
          if (data.text === "Connected") setStatus("Connected");
          break;
        case "error":
          setMessages((prev) => [
            ...prev.map(m => m.loading ? { ...m, loading: false } : m),
            { role: "error", text: data.text },
          ]);
          setIsLoading(false);
          break;
        case "done":
          setMessages((prev) => prev.map(m => m.loading ? { ...m, loading: false } : m));
          setIsLoading(false);
          break;
      }
    };

    return () => ws.close();
  }, [agent.id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendText = (text) => {
    if (!text.trim() || !wsRef.current) return;
    setMessages((prev) => [...prev, { role: "user", text }]);
    wsRef.current.send(JSON.stringify({ text }));
    setIsLoading(true);
  };

  const sendMessage = (e) => {
    e.preventDefault();
    sendText(input);
    setInput("");
  };

  const suggestions = SUGGESTIONS[agent.id] || [];

  return (
    <div className="chat-window">
      <div className="chat-header">
        <span className="chat-icon">{agent.icon}</span>
        <div>
          <h2>{agent.name}</h2>
          <span className={`status ${status === "Connected" ? "online" : ""}`}>
            {status}
          </span>
        </div>
      </div>

      <div className="messages">
        {messages.length === 0 && (
          <div className="empty-chat">
            <p>Start a conversation with {agent.name}</p>
            <div className="suggestions">
              {suggestions.map((s, i) => (
                <button key={i} onClick={() => sendText(s)}>{s}</button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            <span className="msg-label">
              {msg.role === "user" && "You"}
              {msg.role === "assistant" && `${agent.icon} ${agent.name}`}
              {msg.role === "tool" && "🔧 Tool"}
              {msg.role === "error" && "❌ Error"}
            </span>
            <div className="msg-text">
              {msg.role === "assistant" ? (
                <Markdown>{msg.text}</Markdown>
              ) : msg.role === "tool" ? (
                <>{getToolLabel(msg.text, msg.loading)}{msg.loading && <span className="tool-spinner"></span>}</>
              ) : (
                msg.text
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="message assistant">
            <span className="msg-label">{agent.icon} {agent.name}</span>
            <div className="msg-text typing">
              <span></span><span></span><span></span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form className="input-bar" onSubmit={sendMessage}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={`Message ${agent.name}...`}
          disabled={status !== "Connected"}
        />
        <button type="submit" disabled={!input.trim() || status !== "Connected"}>
          Send
        </button>
      </form>
    </div>
  );
}
