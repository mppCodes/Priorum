import { useState } from "react";
import { X, Calendar } from "lucide-react";
import { COLORS } from "../../constants/colors.js";
import { s } from "../../constants/styles.js";

const EMPTY_FORM = {
  title: "",
  date: "",
  time: "",
  duration: "30",
  type: "personal",
  notes: "",
};

export default function AddEventModal({ onClose, onSubmit }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [loading, setLoading] = useState(false);

  const set = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = async () => {
    if (!form.title.trim()) return;
    setLoading(true);
    try {
      await onSubmit?.({ ...form, duration: parseInt(form.duration) });
      onClose();
    } catch {
      // el error se gestiona en el hook
    } finally {
      setLoading(false);
    }
  };

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

        {/* Campos */}
        {[
          { key: "title", label: "Título", placeholder: "Cita médica, revisión…" },
          { key: "date",  label: "Fecha",  placeholder: "ej: 2025-05-15" },
          { key: "time",  label: "Hora",   placeholder: "ej: 09:30" },
          { key: "notes", label: "Notas",  placeholder: "Descripción opcional" },
        ].map((f) => (
          <div key={f.key} style={{ marginBottom: 12 }}>
            <label style={s.label}>{f.label}</label>
            <input
              value={form[f.key]}
              onChange={(e) => set(f.key, e.target.value)}
              placeholder={f.placeholder}
              style={s.input}
            />
          </div>
        ))}

        {/* Duración */}
        <div style={{ marginBottom: 12 }}>
          <label style={s.label}>Duración (min)</label>
          <select
            value={form.duration}
            onChange={(e) => set("duration", e.target.value)}
            style={{ ...s.input }}
          >
            {["15", "30", "45", "60", "90", "120"].map((d) => (
              <option key={d} value={d}>
                {d} min
              </option>
            ))}
          </select>
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
          <button
            style={{ ...s.btn("secondary") }}
            onClick={onClose}
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
}