import { useState } from "react";
import { X, Calendar } from "lucide-react";
import { COLORS } from "../../constants/colors.js";
import { s } from "../../constants/styles.js";

// ── Utilidades de tiempo ──────────────────────────────────────────────────────

/** Genera todos los slots HH:MM de 15 en 15 minutos (00:00 → 23:45) */
const TIME_SLOTS = Array.from({ length: 96 }, (_, i) => {
  const h = Math.floor(i / 4).toString().padStart(2, "0");
  const m = ((i % 4) * 15).toString().padStart(2, "0");
  return `${h}:${m}`;
});

/** Fecha de hoy en formato YYYY-MM-DD */
const todayISO = () => new Date().toISOString().slice(0, 10);

/** Hora actual redondeada al siguiente slot de 15 minutos */
const currentTimeSlot = () => {
  const now = new Date();
  const total = now.getHours() * 60 + now.getMinutes();
  const rounded = Math.ceil(total / 15) * 15;
  const h = Math.floor(rounded / 60) % 24;
  const m = rounded % 60;
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`;
};

/** Suma minutos a un slot HH:MM */
const addMinutes = (time, mins) => {
  const [h, m] = time.split(":").map(Number);
  const total = h * 60 + m + mins;
  const nh = Math.floor(total / 60) % 24;
  const nm = total % 60;
  return `${nh.toString().padStart(2, "0")}:${nm.toString().padStart(2, "0")}`;
};

/** Diferencia en minutos entre dos slots HH:MM */
const diffMinutes = (start, end) => {
  const [sh, sm] = start.split(":").map(Number);
  const [eh, em] = end.split(":").map(Number);
  const diff = eh * 60 + em - (sh * 60 + sm);
  return diff > 0 ? diff : diff + 24 * 60;
};

// ── Estado inicial ────────────────────────────────────────────────────────────

const makeEmptyForm = () => {
  const start = currentTimeSlot();
  return {
    title:     "",
    date:      todayISO(),
    startTime: start,
    endTime:   addMinutes(start, 30),
    type:      "personal",
    notes:     "",
  };
};

// ── Estilos compartidos ───────────────────────────────────────────────────────

/** Igual que s.input pero fuerza tema oscuro en los controles nativos */
const darkInput = { ...s.input, colorScheme: "dark" };
const darkSelect = { ...s.input, colorScheme: "dark", cursor: "pointer" };

// ── Componente ────────────────────────────────────────────────────────────────

export default function AddEventModal({ onClose, onSubmit }) {
  const [form, setForm] = useState(makeEmptyForm);
  const [loading, setLoading] = useState(false);

  const set = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));

  /** Al cambiar la hora de inicio, mantiene la duración actual */
  const handleStartChange = (newStart) => {
    const duration = diffMinutes(form.startTime, form.endTime);
    const newEnd = addMinutes(newStart, duration > 0 ? duration : 30);
    setForm((prev) => ({ ...prev, startTime: newStart, endTime: newEnd }));
  };

  const handleSubmit = async () => {
    if (!form.title.trim()) return;
    setLoading(true);
    try {
      await onSubmit?.({
        title:    form.title,
        date:     form.date,
        time:     form.startTime,
        duration: diffMinutes(form.startTime, form.endTime),
        type:     form.type,
        notes:    form.notes,
      });
      onClose();
    } catch {
      // el error se gestiona en el hook
    } finally {
      setLoading(false);
    }
  };

  // Solo mostrar horas de fin posteriores a la de inicio
  const endSlots = TIME_SLOTS.filter((t) => {
    const [sh, sm] = form.startTime.split(":").map(Number);
    const [th, tm] = t.split(":").map(Number);
    return th * 60 + tm > sh * 60 + sm;
  });

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "#00000088",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 100,
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        style={{
          background: COLORS.surface,
          border: `1px solid ${COLORS.border}`,
          borderRadius: 10,
          width: 420,
          padding: 24,
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 20,
          }}
        >
          <span style={{ fontWeight: 700, fontSize: 14 }}>
            Nuevo evento en Outlook
          </span>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              color: COLORS.textSecondary,
            }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Título */}
        <div style={{ marginBottom: 12 }}>
          <label style={s.label}>Título</label>
          <input
            value={form.title}
            onChange={(e) => set("title", e.target.value)}
            placeholder="Cita médica, revisión…"
            style={s.input}
          />
        </div>

        {/* Fecha */}
        <div style={{ marginBottom: 12 }}>
          <label style={s.label}>Fecha</label>
          <input
            type="date"
            value={form.date}
            onChange={(e) => set("date", e.target.value)}
            style={darkInput}
          />
        </div>

        {/* Hora inicio / fin */}
        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          <div style={{ flex: 1 }}>
            <label style={s.label}>Inicio</label>
            <select
              value={form.startTime}
              onChange={(e) => handleStartChange(e.target.value)}
              style={darkSelect}
            >
              {TIME_SLOTS.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
          <div style={{ flex: 1 }}>
            <label style={s.label}>Fin</label>
            <select
              value={form.endTime}
              onChange={(e) => set("endTime", e.target.value)}
              style={darkSelect}
            >
              {endSlots.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Notas */}
        <div style={{ marginBottom: 12 }}>
          <label style={s.label}>Notas</label>
          <input
            value={form.notes}
            onChange={(e) => set("notes", e.target.value)}
            placeholder="Descripción opcional"
            style={s.input}
          />
        </div>

        {/* Tipo */}
        <div style={{ marginBottom: 18 }}>
          <label style={s.label}>Tipo</label>
          <div style={{ display: "flex", gap: 8 }}>
            {["reunion", "personal", "bloqueo"].map((t) => (
              <button
                key={t}
                onClick={() => set("type", t)}
                style={{
                  ...s.btn(form.type === t ? "primary" : "secondary"),
                  flex: 1,
                  justifyContent: "center",
                  textTransform: "capitalize",
                }}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* Acciones */}
        <div style={{ display: "flex", gap: 8 }}>
          <button
            style={{
              ...s.btn(),
              flex: 1,
              justifyContent: "center",
              opacity: loading ? 0.6 : 1,
            }}
            onClick={handleSubmit}
            disabled={loading}
          >
            <Calendar size={13} />
            {loading ? "Creando…" : "Crear en Outlook"}
          </button>
          <button style={{ ...s.btn("secondary") }} onClick={onClose}>
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
}