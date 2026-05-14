import { useState } from "react";
import { Plus, Clock, User, RefreshCw } from "lucide-react";
import { COLORS, eventTypeConfig } from "../../constants/colors.js";
import { s } from "../../constants/styles.js";
import { useCalendar } from "../../hooks/useCalendar.js";
import PeriodFilter from "../common/PeriodFilter.jsx";
import LoadingSpinner from "../common/LoadingSpinner.jsx";
import AddEventModal from "./AddEventModal.jsx";

// ── Configuración del grid ────────────────────────────────────────────────────
const FIRST_HOUR  = 7;   // 07:00
const LAST_HOUR   = 20;  // hasta las 20:00
const HOUR_HEIGHT = 64;  // px por hora
const LABEL_WIDTH = 56;  // px para la columna de horas
const HOURS = Array.from({ length: LAST_HOUR - FIRST_HOUR }, (_, i) => FIRST_HOUR + i);

/** Extrae "HH:MM" de un ISO datetime string */
const getTime = (isoStr) => {
  if (!isoStr) return "";
  const d = new Date(isoStr);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
};

/** Calcula duración en minutos entre dos ISO datetime strings */
const getDuration = (startStr, endStr) => {
  if (!startStr || !endStr) return 30;
  return Math.round((new Date(endStr) - new Date(startStr)) / 60000);
};

/** Convierte "HH:MM" a minutos desde medianoche */
const toMinutes = (time) => {
  if (!time) return 0;
  const [h, m] = time.split(":").map(Number);
  return h * 60 + m;
};

/** Posición top en px de un evento dentro del grid */
const eventTop = (ev) => {
  const mins = toMinutes(getTime(ev.start)) - FIRST_HOUR * 60;
  return Math.max(0, (mins / 60) * HOUR_HEIGHT);
};

/** Altura en px de un evento según su duración */
const eventHeight = (ev) => {
  const dur = getDuration(ev.start, ev.end);
  const h = (dur / 60) * HOUR_HEIGHT;
  return Math.max(h, 24); // mínimo 24px para que sea legible
};

// ── Componente ────────────────────────────────────────────────────────────────

export default function CalendarView() {
  const { events, filters, loading, error, syncing, addEvent, sync, updateFilters } =
    useCalendar({ period: "day" });

  const [showAdd, setShowAdd] = useState(false);

  const today = new Date().toLocaleDateString("es-ES", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });

  const totalHeight = HOURS.length * HOUR_HEIGHT;

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
          <div style={{ fontSize: 18, fontWeight: 700, letterSpacing: "-0.01em" }}>
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
            style={{ ...s.btn("secondary"), padding: "5px 10px", opacity: syncing ? 0.6 : 1 }}
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
              style={{ width: 8, height: 8, borderRadius: 2, background: cfg.color }}
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
          {/* Grid: horas + eventos */}
          <div style={{ display: "flex" }}>

            {/* Columna de horas */}
            <div
              style={{
                width: LABEL_WIDTH,
                flexShrink: 0,
                borderRight: `1px solid ${COLORS.border}`,
                position: "relative",
                height: totalHeight,
              }}
            >
              {HOURS.map((h) => (
                <div
                  key={h}
                  style={{
                    position: "absolute",
                    top: (h - FIRST_HOUR) * HOUR_HEIGHT,
                    left: 0,
                    right: 0,
                    height: HOUR_HEIGHT,
                    display: "flex",
                    alignItems: "flex-start",
                    justifyContent: "flex-end",
                    paddingRight: 10,
                    paddingTop: 6,
                    fontSize: 10,
                    color: COLORS.textMuted,
                    borderBottom: `1px solid ${COLORS.border}`,
                    boxSizing: "border-box",
                  }}
                >
                  {String(h).padStart(2, "0")}:00
                </div>
              ))}
            </div>

            {/* Área de eventos */}
            <div style={{ flex: 1, position: "relative", height: totalHeight }}>

              {/* Líneas horizontales de hora */}
              {HOURS.map((h) => (
                <div
                  key={h}
                  style={{
                    position: "absolute",
                    top: (h - FIRST_HOUR) * HOUR_HEIGHT,
                    left: 0,
                    right: 0,
                    height: HOUR_HEIGHT,
                    borderBottom: `1px solid ${COLORS.border}`,
                    boxSizing: "border-box",
                  }}
                />
              ))}

              {/* Eventos posicionados absolutamente */}
              {events
                .filter((ev) => {
                  const time = getTime(ev.start);
                  if (!time) return false;
                  const h = parseInt(time.split(":")[0]);
                  return h >= FIRST_HOUR && h < LAST_HOUR;
                })
                .map((ev) => {
                  const evType = ev.type || "other";
                  const color = eventTypeConfig[evType]?.color || COLORS.accent;
                  const top    = eventTop(ev);
                  const height = eventHeight(ev);
                  const startTime = getTime(ev.start);
                  const endTimeStr = getTime(ev.end);
                  const duration = getDuration(ev.start, ev.end);
                  const durationLabel = duration >= 60
                    ? `${Math.floor(duration / 60)}h${duration % 60 ? ` ${duration % 60}min` : ""}`
                    : `${duration}min`;

                  return (
                    <div
                      key={ev.id}
                      style={{
                        position: "absolute",
                        top: top + 2,
                        left: 6,
                        right: 6,
                        height: height - 4,
                        background: color + "18",
                        border: `1px solid ${color}50`,
                        borderLeft: `3px solid ${color}`,
                        borderRadius: 5,
                        padding: "5px 8px",
                        overflow: "hidden",
                        boxSizing: "border-box",
                        display: "flex",
                        flexDirection: "column",
                        justifyContent: "space-between",
                      }}
                    >
                      {/* Título + tag */}
                      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 6 }}>
                        <div
                          style={{
                            fontSize: 12,
                            fontWeight: 600,
                            color: COLORS.textPrimary,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                            flex: 1,
                          }}
                        >
                          {ev.title}
                        </div>
                        <span style={{ ...s.tag(color), flexShrink: 0 }}>
                          {eventTypeConfig[evType]?.label || evType}
                        </span>
                      </div>

                      {/* Hora + duración + asistentes (solo si hay espacio) */}
                      {height >= 40 && (
                        <div
                          style={{
                            fontSize: 10,
                            color: COLORS.textSecondary,
                            display: "flex",
                            gap: 10,
                            flexWrap: "wrap",
                          }}
                        >
                          <span>
                            <Clock size={9} style={{ verticalAlign: "middle" }} />{" "}
                            {startTime} → {endTimeStr} · {durationLabel}
                          </span>
                          {ev.attendees?.length > 0 && (
                            <span>
                              <User size={9} style={{ verticalAlign: "middle" }} />{" "}
                              {ev.attendees.map(a => typeof a === "string" ? a : (a.name || a.email)).join(", ")}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}