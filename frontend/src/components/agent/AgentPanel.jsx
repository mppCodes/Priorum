import { useState, useRef, useEffect } from "react";
import { Brain, Send, Trash2, User, Loader } from "lucide-react";
import { COLORS } from "../../constants/colors.js";
import { s } from "../../constants/styles.js";
import { useAgent } from "../../hooks/useAgent.js";

export default function AgentPanel({ tasks = [], events = [] }) {
  const { messages, loading, sendMessage, clearHistory, loadHistory } = useAgent();
  const [input, setInput] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    await sendMessage(text, { tasks, events, date: new Date().toISOString() });
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 16,
        }}
      >
        <div>
          <div
            style={{ fontSize: 18, fontWeight: 700, letterSpacing: "-0.01em" }}
          >
            Agente IA
          </div>
          <div style={{ fontSize: 11, color: COLORS.textSecondary, marginTop: 2 }}>
            Pregunta sobre tus tareas, reuniones o pide ayuda para organizar tu día
          </div>
        </div>
        <button
          style={{ ...s.btn("secondary"), padding: "5px 10px" }}
          onClick={clearHistory}
          title="Limpiar conversación"
        >
          <Trash2 size={12} />
        </button>
      </div>

      {/* Sugerencias rápidas */}
      {messages.length === 0 && (
        <div style={{ marginBottom: 16 }}>
          <div
            style={{
              fontSize: 10,
              color: COLORS.textMuted,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              marginBottom: 8,
            }}
          >
            Sugerencias
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {[
              "¿Cuál es mi tarea más urgente hoy?",
              "¿Tengo tiempo libre esta tarde?",
              "Resume mis reuniones de hoy",
              "¿Qué debería hacer primero?",
            ].map((q) => (
              <button
                key={q}
                style={{
                  ...s.btn("secondary"),
                  fontSize: 11,
                  padding: "5px 10px",
                }}
                onClick={() => {
                  setInput(q);
                }}
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Historial de mensajes */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 10,
          marginBottom: 12,
          minHeight: 200,
          maxHeight: "calc(100vh - 340px)",
        }}
      >
        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              gap: 10,
              alignItems: "flex-start",
              flexDirection: msg.role === "user" ? "row-reverse" : "row",
            }}
          >
            {/* Avatar */}
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: "50%",
                background:
                  msg.role === "user" ? COLORS.accentDim : COLORS.border,
                border: `1px solid ${msg.role === "user" ? COLORS.accent : COLORS.border}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              {msg.role === "user" ? (
                <User size={12} style={{ color: COLORS.accent }} />
              ) : (
                <Brain size={12} style={{ color: COLORS.textSecondary }} />
              )}
            </div>

            {/* Burbuja */}
            <div
              style={{
                maxWidth: "75%",
                background:
                  msg.role === "user" ? COLORS.accentDim : COLORS.surface,
                border: `1px solid ${msg.role === "user" ? COLORS.accent + "40" : COLORS.border}`,
                borderRadius: 8,
                padding: "10px 14px",
                fontSize: 12,
                color: COLORS.textPrimary,
                lineHeight: 1.6,
              }}
            >
              {msg.content}
              <div
                style={{
                  fontSize: 9,
                  color: COLORS.textMuted,
                  marginTop: 4,
                  textAlign: msg.role === "user" ? "right" : "left",
                }}
              >
                {msg.timestamp
                  ? new Date(msg.timestamp).toLocaleTimeString("es-ES", {
                      hour: "2-digit",
                      minute: "2-digit",
                    })
                  : ""}
              </div>
            </div>
          </div>
        ))}

        {/* Indicador de escritura */}
        {loading && (
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: "50%",
                background: COLORS.border,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Brain size={12} style={{ color: COLORS.textSecondary }} />
            </div>
            <div
              style={{
                background: COLORS.surface,
                border: `1px solid ${COLORS.border}`,
                borderRadius: 8,
                padding: "10px 14px",
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontSize: 12,
                color: COLORS.textMuted,
              }}
            >
              <Loader size={12} style={{ animation: "spin 1s linear infinite" }} />
              El agente está pensando…
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div
        style={{
          display: "flex",
          gap: 8,
          borderTop: `1px solid ${COLORS.border}`,
          paddingTop: 12,
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
          placeholder="Escribe tu pregunta al agente…"
          style={{ ...s.input, flex: 1 }}
          disabled={loading}
        />
        <button
          style={{
            ...s.btn(),
            padding: "8px 14px",
            opacity: loading || !input.trim() ? 0.5 : 1,
          }}
          onClick={handleSend}
          disabled={loading || !input.trim()}
        >
          <Send size={13} />
        </button>
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}