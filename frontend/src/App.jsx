// src/App.jsx
import { useState } from "react";

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function sendMessage(e) {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = { role: "user", content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: input }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? `HTTP ${res.status}`);
      }

      const data = await res.json();
      setMessages(prev => [...prev, { role: "assistant", content: data.reply }]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div>
        {messages.map((msg, i) => (
          <div key={i}><strong>{msg.role}:</strong> {msg.content}</div>
        ))}
        {loading && <div>Thinking...</div>}
        {error && <div style={{ color: "red" }}>Error: {error}</div>}
      </div>
      <form onSubmit={sendMessage}>
        <input value={input} onChange={e => setInput(e.target.value)} />
        <button type="submit" disabled={loading}>Send</button>
      </form>
    </div>
  );
}

export default App;