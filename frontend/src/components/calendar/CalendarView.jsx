import { useState } from "react";
import { Plus, Clock, User, RefreshCw } from "lucide-react";
import { COLORS, eventTypeConfig } from "../../constants/colors.js";
import { s } from "../../constants/styles.js";
import { useCalendar } from "../../hooks/useCalendar.js";
import PeriodFilter from "../common/PeriodFilter.jsx";
import LoadingSpinner from "../common/LoadingSpinner.jsx";
import AddEventModal from "./AddEventModal.jsx";

const HOURS = Array.from({ length: 12 }, (_, i) => i + 7); // 07:00 – 18:00

export default function CalendarView() {
  const { events, filters, loading, error, syncing, addEvent, sync, updateFilters } =
    useCalendar({ period: "day" });

  const [showAdd, setShowAdd] = useState(false);

  const today = new Date().toLocaleDateString("es-ES", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });

  // Agrupa eventos por hora
  const eventsByHour = (hour) =>
    events.filter((e) => e.time && parseInt(e.time.split(":")[0]) === hour);

  return (
    <div>
      {showAdd && (
        <AddEventModal
          onClose={() => setShowAdd(false)}
          onSubmit={addEvent}
        />
      )}

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
            Calendario Outlook
          </div>
          <div
            style={{
              fontSize: 11,
              color: COLORS.textSecondary,
              marginTop: 2,
              textTransform: "capitalize",
            }}
          >
            {today} · {events.length} evento{events.length !== 1 ? "s" : ""}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            style={{
              ...s.btn("secondary"),
              padding: "5px 10px",
              opacity: syncing ? 0.6 : 1,
            }}
            onClick={sync}
            disabled={syncing}
            title="Sincronizar con Outlook"
          >
            <RefreshCw
              size={12}
              style={{ animation: syncing ? "spin 1s linear infinite" : "none" }}
            />
          </button>
          <button style={s.btn()} onClick={() => setShowAdd(true)}>
            <Plus size={13} /> Nuevo evento
          </button>
        </div>
      </div>

      {/* Filtro de período */}
      <PeriodFilter
        value={filters.period}
        onChange={(period) => updateFilters({ period })}
      />

      {/* Leyenda */}
      <div style={{ display: "flex", gap: 14, marginBottom: 16 }}>
        {Object.entries(eventTypeConfig).map(([key, cfg]) => (
          <div
            key={key}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 5,
              fontSize: 11,
              color: COLORS.textSecondary,
            }}
          >
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: 2,
                background: cfg.color,
              }}
            />
            <span>{cfg.label}</span>
          </div>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div
          style={{
            background: COLORS.red + "15",
            border: `1px solid ${COLORS.red}40`,
            borderRadius: 6,
            padding: "10px 14px",
            fontSize: 12,
            color: COLORS.red,
            marginBottom: 12,
          }}
        >
          {error}
        </div>
      )}

      {/* Timeline */}
      {loading ? (
        <LoadingSpinner message="Cargando calendario de Outlook…" />
      ) : (
        <div
          style={{
            background: COLORS.surface,
            border: `1px solid ${COLORS.border}`,
            borderRadius: 8,
            overflow: "hidden",
          }}
        >
          {HOURS.map((h) => {
            const hourEvents = eventsByHour(h);
            return (
              <div
                key={h}
                style={{
                  display: "flex",
                  borderBottom: `1px solid ${COLORS.border}`,
                  minHeight: 52,
                }}
              >
                {/* Etiqueta de hora */}
                <div
                  style={{
                    width: 56,
                    padding: "8px 12px",
                    fontSize: 11,
                    color: COLORS.textMuted,
                    flexShrink: 0,
                    borderRight: `1px solid ${COLORS.border}`,
                    paddingTop: 10,
                  }}
                >
                  {String(h).padStart(2, "0")}:00
                </div>

                {/* Eventos */}
                <div
                  style={{
                    flex: 1,
                    padding: "6px 10px",
                    display: "flex",
                    flexDirection: "column",
                    gap: 4,
                  }}
                >
                  {hourEvents.map((ev) => {
                    const color =
                      eventTypeConfig[ev.type]?.color || COLORS.accent;
                    return (
                      <div
                        key={ev.id}
                        style={{
                          background: color + "18",
                          border: `1px solid ${color}50`,
                          borderLeft: `3px solid ${color}`,
                          borderRadius: 5,
                          padding: "6px 10px",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                        }}
                      >
                        <div>
                          <div
                            style={{
                              fontSize: 12,
                              fontWeight: 600,
                              color: COLORS.textPrimary,
                            }}
                          >
                            {ev.title}
                          </div>
                          <div
                            style={{
                              fontSize: 10,
                              color: COLORS.textSecondary,
                              marginTop: 2,
                              display: "flex",
                              gap: 10,
                            }}
                          >
                            <span>
                              <Clock
                                size={9}
                                style={{ verticalAlign: "middle" }}
                              />{" "}
                              {ev.time} · {ev.duration} min
                            </span>
                            {ev.attendees?.length > 0 && (
                              <span>
                                <User
                                  size={9}
                                  style={{ verticalAlign: "middle" }}
                                />{" "}
                                {ev.attendees.join(", ")}
                              </span>
                            )}
                          </div>
                        </div>
                        <span style={s.tag(color)}>
                          {eventTypeConfig[ev.type]?.label || ev.type}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}