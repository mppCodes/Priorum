import { useState } from "react";
import { X, List, MessageSquare, User, Plus, Clock } from "lucide-react";
import { COLORS, priorityConfig } from "../../constants/colors.js";
import { s } from "../../constants/styles.js";

export default function TaskDetail({ task, onClose, onUpdate }) {
  const [newComment, setNewComment] = useState("");
  const [newSubtask, setNewSubtask] = useState("");
  const [subtasks, setSubtasks] = useState(task.subtasks || []);
  const [comments, setComments] = useState(task.comments || []);

  const addSubtask = () => {
    if (!newSubtask.trim()) return;
    const updated = [...subtasks, newSubtask.trim()];
    setSubtasks(updated);
    setNewSubtask("");
    onUpdate?.(task.id, { subtasks: updated });
  };

  const addComment = () => {
    if (!newComment.trim()) return;
    const updated = [...comments, newComment.trim()];
    setComments(updated);
    setNewComment("");
    onUpdate?.(task.id, { comments: updated });
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
          width: 520,
          maxHeight: "80vh",
          overflow: "auto",
          padding: 24,
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            marginBottom: 16,
          }}
        >
          <div>
            <div
              style={{
                fontSize: 15,
                fontWeight: 700,
                color: COLORS.textPrimary,
                marginBottom: 6,
              }}
            >
              {task.title}
            </div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              <span style={s.tag(priorityConfig[task.priority]?.color || COLORS.textMuted)}>
                {task.priority}
              </span>
              <span style={s.tag(COLORS.blue)}>{task.project}</span>
              {(task.tags || []).map((t) => (
                <span key={t} style={s.tag(COLORS.textMuted)}>
                  #{t}
                </span>
              ))}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              color: COLORS.textSecondary,
              padding: 4,
            }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Deadline */}
        <div
          style={{
            display: "flex",
            gap: 6,
            marginBottom: 6,
            alignItems: "center",
          }}
        >
          <Clock size={12} style={{ color: COLORS.textMuted }} />
          <span style={{ fontSize: 11, color: COLORS.textSecondary }}>
            Deadline:{" "}
            <b style={{ color: COLORS.textPrimary }}>{task.deadline}</b>
          </span>
        </div>

        {/* Subtareas */}
        <div style={{ marginTop: 18, marginBottom: 10 }}>
          <div
            style={{
              fontSize: 10,
              color: COLORS.textMuted,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              marginBottom: 8,
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <List size={11} /> Subtareas
          </div>
          {subtasks.map((st, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "5px 0",
                borderBottom: `1px solid ${COLORS.border}`,
              }}
            >
              <input type="checkbox" style={{ accentColor: COLORS.accent }} />
              <span style={{ fontSize: 12, color: COLORS.textSecondary }}>
                {st}
              </span>
            </div>
          ))}
          <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
            <input
              value={newSubtask}
              onChange={(e) => setNewSubtask(e.target.value)}
              placeholder="Nueva subtarea…"
              style={{ ...s.input, flex: 1 }}
              onKeyDown={(e) => e.key === "Enter" && addSubtask()}
            />
            <button style={s.btn()} onClick={addSubtask}>
              <Plus size={12} />
            </button>
          </div>
        </div>

        {/* Comentarios */}
        <div style={{ marginTop: 18 }}>
          <div
            style={{
              fontSize: 10,
              color: COLORS.textMuted,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              marginBottom: 8,
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <MessageSquare size={11} /> Comentarios
          </div>
          {comments.map((c, i) => (
            <div
              key={i}
              style={{
                background: COLORS.bg,
                borderRadius: 6,
                padding: "8px 12px",
                marginBottom: 6,
                fontSize: 12,
                color: COLORS.textSecondary,
                lineHeight: 1.6,
                border: `1px solid ${COLORS.border}`,
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  marginBottom: 4,
                }}
              >
                <div
                  style={{
                    width: 18,
                    height: 18,
                    borderRadius: "50%",
                    background: COLORS.accentDim,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <User size={10} style={{ color: COLORS.accent }} />
                </div>
                <span style={{ fontSize: 10, color: COLORS.textMuted }}>Tú</span>
              </div>
              {c}
            </div>
          ))}
          <textarea
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            placeholder="Añadir comentario…"
            style={{ ...s.input, height: 64, resize: "none" }}
          />
          <button
            style={{ ...s.btn(), marginTop: 6 }}
            onClick={addComment}
          >
            <MessageSquare size={12} /> Añadir comentario
          </button>
        </div>
      </div>
    </div>
  );
}