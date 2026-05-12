import { useState } from "react";
import { X, Plus } from "lucide-react";
import { COLORS, priorityConfig } from "../../constants/colors.js";
import { s } from "../../constants/styles.js";

const EMPTY_FORM = {
  title: "",
  project: "",
  priority: "media",
  deadline: "",
  tags: "",
};

export default function AddTaskModal({ onClose, onSubmit }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [loading, setLoading] = useState(false);

  const set = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = async () => {
    if (!form.title.trim()) return;
    setLoading(true);
    try {
      await onSubmit?.({
        ...form,
        tags: form.tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
      });
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
          width: 440,
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
            Nueva tarea en Notion
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
          { key: "title",    label: "Título",    placeholder: "¿Qué hay que hacer?" },
          { key: "project",  label: "Proyecto",  placeholder: "Backend API, Frontend…" },
          { key: "deadline", label: "Deadline",  placeholder: "Hoy, Mañana, Vie 16…" },
          { key: "tags",     label: "Etiquetas", placeholder: "code, docs, cliente…" },
        ].map((f) => (
          <div key={f.key} style={{ marginBottom: 12 }}>
            <label style={s.label}>{f.label}</label>
            <input
              value={form[f.key]}
              onChange={(e) => set(f.key, e.target.value)}
              placeholder={f.placeholder}
              style={s.input}
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            />
          </div>
        ))}

        {/* Prioridad */}
        <div style={{ marginBottom: 16 }}>
          <label style={s.label}>Prioridad</label>
          <div style={{ display: "flex", gap: 8 }}>
            {["alta", "media", "baja"].map((p) => (
              <button
                key={p}
                onClick={() => set("priority", p)}
                style={{
                  ...s.btn(form.priority === p ? "primary" : "secondary"),
                  flex: 1,
                  justifyContent: "center",
                }}
              >
                <span
                  style={{
                    color:
                      form.priority === p ? "#fff" : priorityConfig[p].color,
                  }}
                >
                  ●
                </span>{" "}
                {p}
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
            <Plus size={13} /> {loading ? "Creando…" : "Crear en Notion"}
          </button>
          <button
            style={{ ...s.btn("secondary"), justifyContent: "center" }}
            onClick={onClose}
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
}