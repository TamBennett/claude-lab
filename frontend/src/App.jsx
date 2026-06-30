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

    const text = input;
    setMessages(prev => [...prev, { role: "user", content: text }]);
    setInput("");
    setLoading(true);
    setError(null);

    // add an empty assistant message; we'll append streamed tokens to it
    setMessages(prev => [...prev, { role: "assistant", content: "" }]);

    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/chat/agent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE frames are separated by a blank line
        const frames = buffer.split("\n\n");
        buffer = frames.pop();            // keep the last, maybe-incomplete frame

        for (const frame of frames) {
          const line = frame.trim();
          if (!line.startsWith("data:")) continue;
          const payload = line.slice(5).trim();
          if (payload === "[DONE]") continue;

          const event = JSON.parse(payload);

          if (event.type === "text") {
            setMessages(prev => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              updated[updated.length - 1] = { ...last, content: last.content + event.text };
              return updated;
            });
          } else if (event.type === "tool_use") {
            setMessages(prev => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              const note = `\n\n🔧 calling ${event.name}…\n\n`;
              updated[updated.length - 1] = { ...last, content: last.content + note };
              return updated;
            });
          } else if (event.type === "error") {
            setError(event.error);
          };
        }
      }
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