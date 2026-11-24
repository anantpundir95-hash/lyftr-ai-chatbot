import { useState } from "react";
import "./App.css";

const API_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000";

function createSessionId() {
  return `session-${crypto.randomUUID()}`;
}

function App() {
  const [sessionId] = useState(() => createSessionId());
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [loading, setLoading] = useState(false);

  async function sendMessage() {
    const trimmedMessage = input.trim();

    if (!trimmedMessage || loading) {
      return;
    }

    const userMessage = {
      role: "user",
      content: trimmedMessage,
    };

    setMessages((previous) => [...previous, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const body = {
        session_id: sessionId,
        message: trimmedMessage,
      };

      if (systemPrompt.trim()) {
        body.system_prompt = systemPrompt.trim();
      }

      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Something went wrong");
      }

      const assistantMessage = {
        role: "assistant",
        content: data.reply,
        metadata: data.metadata,
      };

      setMessages((previous) => [
        ...previous,
        assistantMessage,
      ]);
    } catch (error) {
      setMessages((previous) => [
        ...previous,
        {
          role: "error",
          content: error.message || "Unable to reach the backend.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>Lyftr AI</h1>
          <p>Resilient LLM Chat Assistant</p>
        </div>

        <div className="status">
          <span className="status-dot"></span>
          Backend Connected
        </div>
      </header>

      <main className="chat-container">
        <section className="system-section">
          <label htmlFor="system-prompt">
            System Prompt
          </label>

          <input
            id="system-prompt"
            data-testid="system-prompt-input"
            type="text"
            value={systemPrompt}
            onChange={(event) =>
              setSystemPrompt(event.target.value)
            }
            placeholder="Optional: Tell the assistant how to behave"
          />
        </section>

        <section className="messages">
          {messages.length === 0 && (
            <div className="welcome">
              <h2>How can I help you?</h2>
              <p>
                Start a conversation with the AI assistant.
              </p>
            </div>
          )}

          {messages.map((message, index) => {
            if (message.role === "user") {
              return (
                <div
                  className="message-row user-row"
                  key={index}
                >
                  <div className="message user-message">
                    <span className="message-label">
                      You
                    </span>
                    <p>{message.content}</p>
                  </div>
                </div>
              );
            }

            if (message.role === "error") {
              return (
                <div
                  className="error-message"
                  key={index}
                >
                  {message.content}
                </div>
              );
            }

            return (
              <div
                className="message-row assistant-row"
                key={index}
              >
                <div
                  className="message assistant-message"
                  data-testid="assistant-message"
                >
                  <span className="message-label">
                    AI Assistant
                  </span>

                  <p>{message.content}</p>

                  <div className="metadata">
                    <span>
                      Source:
                      {" "}
                      <strong data-testid="meta-source">
                        {message.metadata.resolution_source}
                      </strong>
                    </span>

                    <span>
                      Model:
                      {" "}
                      <strong data-testid="meta-model">
                        {message.metadata.model}
                      </strong>
                    </span>

                    <span>
                      Latency:
                      {" "}
                      <strong data-testid="meta-latency">
                        {message.metadata.latency_ms} ms
                      </strong>
                    </span>

                    <span>
                      Input:
                      {" "}
                      <strong data-testid="meta-input-tokens">
                        {message.metadata.input_tokens}
                      </strong>
                    </span>

                    <span>
                      Output:
                      {" "}
                      <strong data-testid="meta-output-tokens">
                        {message.metadata.output_tokens}
                      </strong>
                    </span>
                  </div>
                </div>
              </div>
            );
          })}

          {loading && (
            <div className="message-row assistant-row">
              <div className="message assistant-message loading">
                AI is thinking...
              </div>
            </div>
          )}
        </section>

        <section className="input-area">
          <textarea
            data-testid="chat-input"
            value={input}
            onChange={(event) =>
              setInput(event.target.value)
            }
            onKeyDown={handleKeyDown}
            placeholder="Ask anything..."
            rows="1"
            disabled={loading}
          />

          <button
            data-testid="send-button"
            onClick={sendMessage}
            disabled={loading || !input.trim()}
          >
            {loading ? "Sending..." : "Send"}
          </button>
        </section>
      </main>
    </div>
  );
}

export default App;