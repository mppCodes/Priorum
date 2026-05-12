import { useState } from "react";
import { Plus, CheckSquare, List, MessageSquare, RefreshCw } from "lucide-react";
import { COLORS, priorityConfig } from "../../constants/colors.js";
import { s } from "../../constants/styles.js";
import { useTasks } from "../../hooks/useTasks.js";
import PeriodFilter from "../common/PeriodFilter.jsx";
import LoadingSpinner from "../common/LoadingSpinner.jsx";
import TaskDetail from "./TaskDetail.jsx";
import AddTaskModal from "./AddTaskModal.jsx";

const PRIORITY_FILTERS = ["todas", "alta", "media", "baja"];

export default function TasksView() {
  const { tasks, filters, loading, error, syncing, addTask, editTask, sync, updateFilters } =
    useTasks({ period: "day" });

  const [selected, setSelected] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [priorityFilter, setPriorityFilter] = useState("todas");

  const visible = tasks.filter((t) => {
    if (t.done) return false;
    if (priorityFilter === "todas") return true;
    return t.priority === priorityFilter;
  });

  const doneTasks = tasks.filter((t) => t.done);

  return (
    <div>
      {selected && (
        <TaskDetail
          task={selected}
          onClose={() => setSelected(null)}
          onUpdate={editTask}
        />
      )}
      {showAdd && (
        <AddTaskModal
          onClose={() => setShowAdd(false)}
          onSubmit={addTask}
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
        <div style={{ fontSize: 18, fontWeight: 700, letterSpacing: "-0.01em" }}>
          Tareas de Notion
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            style={{ ...s.btn("secondary"), padding: "5px 10px", opacity: syncing ? 0.6 : 1 }}
            onClick={sync}
            disabled={syncing}
            title="Sincronizar con Notion"
          >
            <RefreshCw size={12} style={{ animation: syncing ? "spin 1s linear infinite" : "none" }} />
          </button>
          <button style={s.btn()} onClick={() => setShowAdd(true)}>
            <Plus size={13} /> Nueva tarea
          </button>
        </div>
      </div>

      {/* Filtro de período */}
      <PeriodFilter
        value={filters.period}
        onChange={(period) => updateFilters({ period })}
      />

      {/* Filtro de prioridad */}
      <div style={{ display: "flex", gap: 6, marginBottom: 16 }}>
        {PRIORITY_FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setPriorityFilter(f)}
            style={{
              ...s.btn(priorityFilter === f ? "primary" : "secondary"),
              textTransform: "capitalize",
            }}
          >
            {f !== "todas" && (
              <span style={{ color: priorityFilter === f ? "#fff" : priorityConfig[f]?.color }}>●</span>
            )}
            {f}
          </button>
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

      {/* Lista de tareas */}
      {loading ? (
        <LoadingSpinner message="Cargando tareas de Notion…" />
      ) : visible.length === 0 ? (
        <div
          style={{
            textAlign: "center",
            padding: 48,
            color: COLORS.textMuted,
            fontSize: 12,
          }}
        >
          No hay tareas para este período
        </div>
      ) : (
        visible.map((task) => (
          <div
            key={task.id}
            style={{
              ...s.card,
              cursor: "pointer",
              borderLeft: `3px solid ${priorityConfig[task.priority]?.color || COLORS.border}`,
            }}
            onClick={() => setSelected(task)}
          >
            <div
              style={{
                display: "flex",
                alignItems: "flex-start",
                justifyContent: "space-between",
                gap: 12,
              }}
            >
              <div style={{ flex: 1 }}>
                <div
                  style={{
                    fontWeight: 600,
                    color: COLORS.textPrimary,
                    fontSize: 13,
                    marginBottom: 4,
                  }}
                >
                  {task.title}
                </div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  <span style={s.tag(COLORS.blue)}>{task.project}</span>
                  {(task.tags || []).map((t) => (
                    <span key={t} style={s.tag(COLORS.textMuted)}>
                      #{t}
                    </span>
                  ))}
                </div>
              </div>
              <div style={{ textAlign: "right", flexShrink: 0 }}>
                <div style={{ fontSize: 10, color: COLORS.textSecondary }}>
                  {task.deadline}
                </div>
                <div
                  style={{
                    display: "flex",
                    gap: 8,
                    justifyContent: "flex-end",
                    marginTop: 6,
                  }}
                >
                  {task.subtasks?.length > 0 && (
                    <span
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 3,
                        fontSize: 10,
                        color: COLORS.textMuted,
                      }}
                    >
                      <List size={10} />
                      {task.subtasks.length}
                    </span>
                  )}
                  {task.comments?.length > 0 && (
                    <span
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 3,
                        fontSize: 10,
                        color: COLORS.textMuted,
                      }}
                    >
                      <MessageSquare size={10} />
                      {task.comments.length}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))
      )}

      {/* Tareas completadas */}
      {doneTasks.length > 0 && (
        <div
          style={{
            marginTop: 8,
            padding: "10px 14px",
            background: COLORS.surfaceHover,
            borderRadius: 6,
            fontSize: 11,
            color: COLORS.textMuted,
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          <CheckSquare size={12} />
          {doneTasks.length} tarea{doneTasks.length > 1 ? "s" : ""} completada
          {doneTasks.length > 1 ? "s" : ""} hoy
        </div>
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}