import { useEffect } from "react";
import { Brain, Clock, ArrowRight } from "lucide-react";
import { COLORS, priorityConfig } from "../../constants/colors.js";
import { s } from "../../constants/styles.js";
import { useAgent } from "../../hooks/useAgent.js";
import LoadingSpinner from "../common/LoadingSpinner.jsx";

export default function PriorityView({ tasks = [], events = [] }) {
  const { priorities, scheduleSuggestion, loading, fetchPriorities, fetchScheduleSuggestion } =
    useAgent();

  const today = new Date().toLocaleDateString("es-ES", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });

  const pendingTasks = tasks.filter((t) => !t.done);
  const todayEvents = events.length;
  const freeTime = "—"; // calculado por el agente

  const regenerate = () => {
    fetchPriorities({ tasks: pendingTasks, events, date: new Date().toISOString() });
    fetchScheduleSuggestion({ tasks: pendingTasks, events, date: new Date().toISOString() });
  };

  useEffect(() => {
    if (pendingTasks.length > 0 || events.length > 0) {
      regenerate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 20,
        }}
      >
        <div>
          <div
            style={{
              fontSize: 18,
              fontWeight: 700,
              color: COLORS.textPrimary,
              letterSpacing: "-0.01em",
            }}
          >
            Tu día de hoy
          </div>
          <div
            style={{
              fontSize: 11,
              color: COLORS.textSecondary,
              marginTop: 2,
              textTransform: "capitalize",
            }}
          >
            {today}
          </div>
        </div>
        <button style={s.btn()} onClick={regenerate} disabled={loading}>
          <Brain size={13} />
          {loading ? "Analizando…" : "Regenerar prioridades"}
        </button>
      </div>

      {/* Métricas */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 10,
          marginBottom: 20,
        }}
      >
        {[
          { label: "Tareas pendientes", value: pendingTasks.length, color: COLORS.accent },
          { label: "Reuniones hoy",     value: todayEvents,          color: COLORS.blue },
          { label: "Tiempo libre est.", value: freeTime,             color: COLORS.green },
        ].map((m) => (
          <div
            key={m.label}
            style={{
              ...s.card,
              padding: "14px 16px",
              marginBottom: 0,
              borderTop: `2px solid ${m.color}`,
            }}
          >
            <div style={{ fontSize: 22, fontWeight: 700, color: m.color }}>
              {m.value}
            </div>
            <div style={{ fontSize: 11, color: COLORS.textSecondary, marginTop: 2 }}>
              {m.label}
            </div>
          </div>
        ))}
      </div>

      {/* Lista priorizada */}
      <div
        style={{
          marginBottom: 8,
          fontSize: 10,
          color: COLORS.textMuted,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
        }}
      >
        Orden recomendado por el agente
      </div>

      {loading ? (
        <LoadingSpinner message="El agente está analizando tu día…" />
      ) : priorities.length === 0 ? (
        <div
          style={{
            ...s.card,
            textAlign: "center",
            color: COLORS.textMuted,
            fontSize: 12,
            padding: 32,
          }}
        >
          Pulsa "Regenerar prioridades" para que el agente analice tu día
        </div>
      ) : (
        priorities.map((item) => (
          <div
            key={item.rank}
            style={{ ...s.card, display: "flex", gap: 14, alignItems: "flex-start" }}
          >
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: "50%",
                background: COLORS.accentDim,
                border: `1px solid ${COLORS.accent}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 12,
                fontWeight: 700,
                color: COLORS.accent,
                flexShrink: 0,
                marginTop: 2,
              }}
            >
              {item.rank}
            </div>
            <div style={{ flex: 1 }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  marginBottom: 4,
                }}
              >
                <span style={{ fontWeight: 600, color: COLORS.textPrimary }}>
                  {item.title}
                </span>
                {item.tag && (
                  <span style={s.tag(priorityConfig[item.tag]?.color || COLORS.textMuted)}>
                    {priorityConfig[item.tag]?.label || item.tag}
                  </span>
                )}
              </div>
              <div
                style={{
                  fontSize: 11,
                  color: COLORS.textSecondary,
                  lineHeight: 1.5,
                }}
              >
                {item.why}
              </div>
              {item.time && (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                    marginTop: 6,
                    fontSize: 11,
                    color: COLORS.textMuted,
                  }}
                >
                  <Clock size={11} /> {item.time} estimados
                </div>
              )}
            </div>
            <ArrowRight
              size={14}
              style={{ color: COLORS.textMuted, flexShrink: 0, marginTop: 4 }}
            />
          </div>
        ))
      )}

      {/* Razonamiento del agente */}
      {scheduleSuggestion?.reasoning && (
        <div
          style={{
            ...s.card,
            borderColor: COLORS.accent + "40",
            background: COLORS.accentDim,
            marginTop: 8,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              marginBottom: 8,
              fontSize: 10,
              color: COLORS.accent,
              fontWeight: 700,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            <Brain size={12} /> Razonamiento del agente
          </div>
          <div
            style={{
              fontSize: 12,
              color: COLORS.textSecondary,
              lineHeight: 1.7,
            }}
          >
            {scheduleSuggestion.reasoning}
          </div>
        </div>
      )}
    </div>
  );
}