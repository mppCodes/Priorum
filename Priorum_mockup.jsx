import { useState } from "react";
import {
  Calendar, CheckSquare, Brain, Plus, ChevronRight,
  Clock, Tag, MessageSquare, List, X, ChevronDown,
  AlertCircle, Layers, User, ArrowRight, Inbox
} from "lucide-react";

const COLORS = {
  bg: "#0F0F11",
  surface: "#18181C",
  surfaceHover: "#1F1F25",
  border: "#2A2A32",
  accent: "#7C6AF7",
  accentDim: "#7C6AF720",
  accentHover: "#9585FA",
  textPrimary: "#F0EFF6",
  textSecondary: "#8B8A99",
  textMuted: "#4A4A58",
  green: "#3DD68C",
  amber: "#F5A623",
  red: "#F06060",
  blue: "#4B9EF7",
};

const priorityConfig = {
  alta:   { color: COLORS.red,   label: "Alta" },
  media:  { color: COLORS.amber, label: "Media" },
  baja:   { color: COLORS.green, label: "Baja" },
};

const INITIAL_TASKS = [
  { id: 1, title: "Revisar PR del módulo de autenticación", project: "Backend API", priority: "alta", deadline: "Hoy", tags: ["code", "review"], subtasks: ["Leer diff completo", "Ejecutar tests"], comments: ["LGTM en general, revisar el middleware"], done: false },
  { id: 2, title: "Preparar demo para el cliente", project: "Producto", priority: "alta", deadline: "Mañana", tags: ["cliente"], subtasks: ["Slides resumen", "Grabar video backup"], comments: [], done: false },
  { id: 3, title: "Documentar endpoints REST", project: "Backend API", priority: "media", deadline: "Vie 16", tags: ["docs"], subtasks: [], comments: ["Usar Swagger"], done: false },
  { id: 4, title: "Refactor del componente Table", project: "Frontend", priority: "baja", deadline: "Sem próxima", tags: ["code"], subtasks: [], comments: [], done: true },
];

const CALENDAR_EVENTS = [
  { id: 1, title: "Daily standup", time: "09:00", duration: 15, type: "reunion", attendees: ["Ana", "Paco", "Marta"] },
  { id: 2, title: "Revisión sprint", time: "11:00", duration: 60, type: "reunion", attendees: ["Todo el equipo"] },
  { id: 3, title: "Cita médica", time: "13:30", duration: 30, type: "personal", attendees: [] },
  { id: 4, title: "1:1 con producto", time: "16:00", duration: 30, type: "reunion", attendees: ["Laura"] },
];

const PRIORITY_LIST = [
  { rank: 1, title: "Revisar PR del módulo de autenticación", why: "Bloquea el deploy de esta tarde. Alta urgencia, tiempo estimado 45 min.", time: "45 min", tag: "alta" },
  { rank: 2, title: "Preparar demo para el cliente", why: "Deadline mañana. Reunión de revisión a las 11:00 reduce tu ventana libre.", time: "90 min", tag: "alta" },
  { rank: 3, title: "Documentar endpoints REST", why: "Sin bloqueos activos. Puedes avanzar entre las 14:00 y 15:30.", time: "60 min", tag: "media" },
];

const NAV_ITEMS = [
  { id: "priority", icon: Brain,       label: "Prioridades" },
  { id: "tasks",    icon: CheckSquare, label: "Tareas" },
  { id: "calendar", icon: Calendar,    label: "Calendario" },
];

const s = {
  app: {
    display: "flex", minHeight: "100vh", background: COLORS.bg,
    fontFamily: "'DM Mono', 'Courier New', monospace", color: COLORS.textPrimary,
    fontSize: 13,
  },
  sidebar: {
    width: 200, minHeight: "100vh", background: COLORS.surface,
    borderRight: `1px solid ${COLORS.border}`, padding: "24px 0",
    display: "flex", flexDirection: "column", flexShrink: 0,
  },
  logo: {
    padding: "0 20px 24px", fontSize: 13, fontWeight: 700,
    letterSpacing: "0.12em", color: COLORS.accent, textTransform: "uppercase",
    borderBottom: `1px solid ${COLORS.border}`, marginBottom: 8,
  },
  navItem: (active) => ({
    display: "flex", alignItems: "center", gap: 10, padding: "10px 20px",
    cursor: "pointer", color: active ? COLORS.textPrimary : COLORS.textSecondary,
    background: active ? COLORS.accentDim : "transparent",
    borderLeft: `2px solid ${active ? COLORS.accent : "transparent"}`,
    transition: "all 0.15s", fontSize: 12, letterSpacing: "0.04em",
  }),
  main: { flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" },
  topbar: {
    background: COLORS.surface, borderBottom: `1px solid ${COLORS.border}`,
    padding: "14px 28px", display: "flex", alignItems: "center",
    justifyContent: "space-between",
  },
  topbarTitle: { fontSize: 14, fontWeight: 600, letterSpacing: "0.06em", color: COLORS.textPrimary },
  topbarSub: { fontSize: 11, color: COLORS.textSecondary, marginTop: 2 },
  content: { flex: 1, padding: 24, overflow: "auto" },
  card: {
    background: COLORS.surface, border: `1px solid ${COLORS.border}`,
    borderRadius: 8, padding: 16, marginBottom: 12,
  },
  btn: (variant = "primary") => ({
    display: "inline-flex", alignItems: "center", gap: 6, padding: "7px 14px",
    borderRadius: 6, border: "none", cursor: "pointer", fontSize: 12,
    fontFamily: "inherit", fontWeight: 600, letterSpacing: "0.04em",
    background: variant === "primary" ? COLORS.accent : COLORS.border,
    color: variant === "primary" ? "#fff" : COLORS.textSecondary,
    transition: "all 0.15s",
  }),
  tag: (color) => ({
    display: "inline-block", padding: "2px 8px", borderRadius: 4,
    fontSize: 10, fontWeight: 700, letterSpacing: "0.08em",
    background: color + "20", color: color, textTransform: "uppercase",
  }),
  input: {
    width: "100%", background: COLORS.bg, border: `1px solid ${COLORS.border}`,
    borderRadius: 6, padding: "8px 12px", color: COLORS.textPrimary,
    fontFamily: "inherit", fontSize: 12, outline: "none", boxSizing: "border-box",
  },
  label: { fontSize: 10, color: COLORS.textSecondary, marginBottom: 4, display: "block", letterSpacing: "0.08em", textTransform: "uppercase" },
};

// ── PRIORITY VIEW ──────────────────────────────────────────────
function PriorityView() {
  const today = new Date().toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long" });
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <div>
          <div style={{ fontSize: 18, fontWeight: 700, color: COLORS.textPrimary, letterSpacing: "-0.01em" }}>Tu día de hoy</div>
          <div style={{ fontSize: 11, color: COLORS.textSecondary, marginTop: 2, textTransform: "capitalize" }}>{today}</div>
        </div>
        <button style={s.btn()}>
          <Brain size={13} /> Regenerar prioridades
        </button>
      </div>

      {/* resumen métricas */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10, marginBottom: 20 }}>
        {[
          { label: "Tareas pendientes", value: "4", color: COLORS.accent },
          { label: "Reuniones hoy", value: "4", color: COLORS.blue },
          { label: "Tiempo libre est.", value: "3h 30m", color: COLORS.green },
        ].map(m => (
          <div key={m.label} style={{ ...s.card, padding: "14px 16px", marginBottom: 0, borderTop: `2px solid ${m.color}` }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: m.color }}>{m.value}</div>
            <div style={{ fontSize: 11, color: COLORS.textSecondary, marginTop: 2 }}>{m.label}</div>
          </div>
        ))}
      </div>

      {/* lista priorizada */}
      <div style={{ marginBottom: 8, fontSize: 10, color: COLORS.textMuted, letterSpacing: "0.1em", textTransform: "uppercase" }}>Orden recomendado por el agente</div>
      {PRIORITY_LIST.map((item, i) => (
        <div key={item.rank} style={{ ...s.card, display: "flex", gap: 14, alignItems: "flex-start" }}>
          <div style={{ width: 28, height: 28, borderRadius: "50%", background: COLORS.accentDim, border: `1px solid ${COLORS.accent}`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 700, color: COLORS.accent, flexShrink: 0, marginTop: 2 }}>{item.rank}</div>
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
              <span style={{ fontWeight: 600, color: COLORS.textPrimary }}>{item.title}</span>
              <span style={s.tag(priorityConfig[item.tag].color)}>{priorityConfig[item.tag].label}</span>
            </div>
            <div style={{ fontSize: 11, color: COLORS.textSecondary, lineHeight: 1.5 }}>{item.why}</div>
            <div style={{ display: "flex", alignItems: "center", gap: 4, marginTop: 6, fontSize: 11, color: COLORS.textMuted }}>
              <Clock size={11} /> {item.time} estimados
            </div>
          </div>
          <ArrowRight size={14} style={{ color: COLORS.textMuted, flexShrink: 0, marginTop: 4 }} />
        </div>
      ))}

      {/* razonamiento del agente */}
      <div style={{ ...s.card, borderColor: COLORS.accent + "40", background: COLORS.accentDim, marginTop: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8, fontSize: 10, color: COLORS.accent, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" }}>
          <Brain size={12} /> Razonamiento del agente
        </div>
        <div style={{ fontSize: 12, color: COLORS.textSecondary, lineHeight: 1.7 }}>
          Tienes una ventana libre de 09:15–11:00 antes de la revisión de sprint. He priorizado el PR porque bloquea el deploy y se puede cerrar en esa ventana. La demo tiene deadline mañana pero requiere tiempo continuo — mejor después de las 14:00 una vez termine tu cita médica.
        </div>
      </div>
    </div>
  );
}

// ── TASK DETAIL MODAL ──────────────────────────────────────────
function TaskDetail({ task, onClose, onUpdate }) {
  const [newComment, setNewComment] = useState("");
  const [newSubtask, setNewSubtask] = useState("");
  const [subtasks, setSubtasks] = useState(task.subtasks);
  const [comments, setComments] = useState(task.comments);

  return (
    <div style={{ position: "fixed", inset: 0, background: "#00000088", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }}>
      <div style={{ background: COLORS.surface, border: `1px solid ${COLORS.border}`, borderRadius: 10, width: 520, maxHeight: "80vh", overflow: "auto", padding: 24 }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 16 }}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: COLORS.textPrimary, marginBottom: 6 }}>{task.title}</div>
            <div style={{ display: "flex", gap: 6 }}>
              <span style={s.tag(priorityConfig[task.priority].color)}>{task.priority}</span>
              <span style={s.tag(COLORS.blue)}>{task.project}</span>
              {task.tags.map(t => <span key={t} style={s.tag(COLORS.textMuted)}>#{t}</span>)}
            </div>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: COLORS.textSecondary, padding: 4 }}><X size={16} /></button>
        </div>

        <div style={{ display: "flex", gap: 6, marginBottom: 6, alignItems: "center" }}>
          <Clock size={12} style={{ color: COLORS.textMuted }} />
          <span style={{ fontSize: 11, color: COLORS.textSecondary }}>Deadline: <b style={{ color: COLORS.textPrimary }}>{task.deadline}</b></span>
        </div>

        {/* Subtareas */}
        <div style={{ marginTop: 18, marginBottom: 10 }}>
          <div style={{ fontSize: 10, color: COLORS.textMuted, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
            <List size={11} /> Subtareas
          </div>
          {subtasks.map((st, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "5px 0", borderBottom: `1px solid ${COLORS.border}` }}>
              <input type="checkbox" style={{ accentColor: COLORS.accent }} />
              <span style={{ fontSize: 12, color: COLORS.textSecondary }}>{st}</span>
            </div>
          ))}
          <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
            <input value={newSubtask} onChange={e => setNewSubtask(e.target.value)} placeholder="Nueva subtarea…" style={{ ...s.input, flex: 1 }} onKeyDown={e => { if (e.key === "Enter" && newSubtask) { setSubtasks([...subtasks, newSubtask]); setNewSubtask(""); }}} />
            <button style={s.btn()} onClick={() => { if (newSubtask) { setSubtasks([...subtasks, newSubtask]); setNewSubtask(""); }}}>
              <Plus size={12} />
            </button>
          </div>
        </div>

        {/* Comentarios */}
        <div style={{ marginTop: 18 }}>
          <div style={{ fontSize: 10, color: COLORS.textMuted, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
            <MessageSquare size={11} /> Comentarios
          </div>
          {comments.map((c, i) => (
            <div key={i} style={{ background: COLORS.bg, borderRadius: 6, padding: "8px 12px", marginBottom: 6, fontSize: 12, color: COLORS.textSecondary, lineHeight: 1.6, border: `1px solid ${COLORS.border}` }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                <div style={{ width: 18, height: 18, borderRadius: "50%", background: COLORS.accentDim, display: "flex", alignItems: "center", justifyContent: "center" }}><User size={10} style={{ color: COLORS.accent }} /></div>
                <span style={{ fontSize: 10, color: COLORS.textMuted }}>Tú</span>
              </div>
              {c}
            </div>
          ))}
          <textarea value={newComment} onChange={e => setNewComment(e.target.value)} placeholder="Añadir comentario…" style={{ ...s.input, height: 64, resize: "none" }} />
          <button style={{ ...s.btn(), marginTop: 6 }} onClick={() => { if (newComment) { setComments([...comments, newComment]); setNewComment(""); }}}>
            <MessageSquare size={12} /> Añadir comentario
          </button>
        </div>
      </div>
    </div>
  );
}

// ── ADD TASK MODAL ─────────────────────────────────────────────
function AddTaskModal({ onClose }) {
  const [form, setForm] = useState({ title: "", project: "", priority: "media", deadline: "", tags: "" });
  return (
    <div style={{ position: "fixed", inset: 0, background: "#00000088", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }}>
      <div style={{ background: COLORS.surface, border: `1px solid ${COLORS.border}`, borderRadius: 10, width: 440, padding: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <span style={{ fontWeight: 700, fontSize: 14 }}>Nueva tarea en Notion</span>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: COLORS.textSecondary }}><X size={16} /></button>
        </div>
        {[
          { key: "title", label: "Título", placeholder: "¿Qué hay que hacer?" },
          { key: "project", label: "Proyecto", placeholder: "Backend API, Frontend…" },
          { key: "deadline", label: "Deadline", placeholder: "Hoy, Mañana, Vie 16…" },
          { key: "tags", label: "Etiquetas", placeholder: "code, docs, cliente…" },
        ].map(f => (
          <div key={f.key} style={{ marginBottom: 12 }}>
            <label style={s.label}>{f.label}</label>
            <input value={form[f.key]} onChange={e => setForm({ ...form, [f.key]: e.target.value })} placeholder={f.placeholder} style={s.input} />
          </div>
        ))}
        <div style={{ marginBottom: 16 }}>
          <label style={s.label}>Prioridad</label>
          <div style={{ display: "flex", gap: 8 }}>
            {["alta", "media", "baja"].map(p => (
              <button key={p} onClick={() => setForm({ ...form, priority: p })} style={{ ...s.btn(form.priority === p ? "primary" : "secondary"), flex: 1, justifyContent: "center" }}>
                <span style={{ color: form.priority === p ? "#fff" : priorityConfig[p].color }}>●</span> {p}
              </button>
            ))}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button style={{ ...s.btn(), flex: 1, justifyContent: "center" }} onClick={onClose}>
            <Plus size={13} /> Crear en Notion
          </button>
          <button style={{ ...s.btn("secondary"), justifyContent: "center" }} onClick={onClose}>Cancelar</button>
        </div>
      </div>
    </div>
  );
}

// ── TASKS VIEW ─────────────────────────────────────────────────
function TasksView() {
  const [tasks, setTasks] = useState(INITIAL_TASKS);
  const [selected, setSelected] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [filter, setFilter] = useState("todas");
  const filters = ["todas", "alta", "media", "baja"];
  const visible = tasks.filter(t => filter === "todas" ? !t.done : t.priority === filter && !t.done);

  return (
    <div>
      {selected && <TaskDetail task={selected} onClose={() => setSelected(null)} />}
      {showAdd && <AddTaskModal onClose={() => setShowAdd(false)} />}

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <div style={{ fontSize: 18, fontWeight: 700, letterSpacing: "-0.01em" }}>Tareas de Notion</div>
        <button style={s.btn()} onClick={() => setShowAdd(true)}>
          <Plus size={13} /> Nueva tarea
        </button>
      </div>

      {/* filtros */}
      <div style={{ display: "flex", gap: 6, marginBottom: 16 }}>
        {filters.map(f => (
          <button key={f} onClick={() => setFilter(f)} style={{ ...s.btn(filter === f ? "primary" : "secondary"), textTransform: "capitalize" }}>{f}</button>
        ))}
      </div>

      {visible.map(task => (
        <div key={task.id} style={{ ...s.card, cursor: "pointer", transition: "border-color 0.15s", borderLeft: `3px solid ${priorityConfig[task.priority].color}` }} onClick={() => setSelected(task)}>
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                <span style={{ fontWeight: 600, color: COLORS.textPrimary, fontSize: 13 }}>{task.title}</span>
              </div>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                <span style={s.tag(COLORS.blue)}>{task.project}</span>
                {task.tags.map(t => <span key={t} style={s.tag(COLORS.textMuted)}>#{t}</span>)}
              </div>
            </div>
            <div style={{ textAlign: "right", flexShrink: 0 }}>
              <div style={{ fontSize: 10, color: COLORS.textSecondary }}>{task.deadline}</div>
              <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 6 }}>
                {task.subtasks.length > 0 && <span style={{ display: "flex", alignItems: "center", gap: 3, fontSize: 10, color: COLORS.textMuted }}><List size={10} />{task.subtasks.length}</span>}
                {task.comments.length > 0 && <span style={{ display: "flex", alignItems: "center", gap: 3, fontSize: 10, color: COLORS.textMuted }}><MessageSquare size={10} />{task.comments.length}</span>}
              </div>
            </div>
          </div>
        </div>
      ))}

      {tasks.filter(t => t.done).length > 0 && (
        <div style={{ marginTop: 8, padding: "10px 14px", background: COLORS.surfaceHover, borderRadius: 6, fontSize: 11, color: COLORS.textMuted, display: "flex", alignItems: "center", gap: 6 }}>
          <CheckSquare size={12} /> {tasks.filter(t => t.done).length} tarea{tasks.filter(t => t.done).length > 1 ? "s" : ""} completada{tasks.filter(t => t.done).length > 1 ? "s" : ""} hoy
        </div>
      )}
    </div>
  );
}

// ── ADD EVENT MODAL ────────────────────────────────────────────
function AddEventModal({ onClose }) {
  const [form, setForm] = useState({ title: "", date: "", time: "", duration: "30", type: "personal", notes: "" });
  return (
    <div style={{ position: "fixed", inset: 0, background: "#00000088", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }}>
      <div style={{ background: COLORS.surface, border: `1px solid ${COLORS.border}`, borderRadius: 10, width: 420, padding: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <span style={{ fontWeight: 700, fontSize: 14 }}>Nuevo evento en Outlook</span>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: COLORS.textSecondary }}><X size={16} /></button>
        </div>
        {[
          { key: "title", label: "Título", placeholder: "Cita médica, revisión…" },
          { key: "date",  label: "Fecha",  placeholder: "ej: 2025-05-15" },
          { key: "time",  label: "Hora",   placeholder: "ej: 09:30" },
          { key: "notes", label: "Notas",  placeholder: "Descripción opcional" },
        ].map(f => (
          <div key={f.key} style={{ marginBottom: 12 }}>
            <label style={s.label}>{f.label}</label>
            <input value={form[f.key]} onChange={e => setForm({ ...form, [f.key]: e.target.value })} placeholder={f.placeholder} style={s.input} />
          </div>
        ))}
        <div style={{ marginBottom: 12 }}>
          <label style={s.label}>Duración (min)</label>
          <select value={form.duration} onChange={e => setForm({ ...form, duration: e.target.value })} style={{ ...s.input }}>
            {["15", "30", "45", "60", "90", "120"].map(d => <option key={d} value={d}>{d} min</option>)}
          </select>
        </div>
        <div style={{ marginBottom: 18 }}>
          <label style={s.label}>Tipo</label>
          <div style={{ display: "flex", gap: 8 }}>
            {["reunion", "personal", "bloqueo"].map(t => (
              <button key={t} onClick={() => setForm({ ...form, type: t })} style={{ ...s.btn(form.type === t ? "primary" : "secondary"), flex: 1, justifyContent: "center", textTransform: "capitalize" }}>{t}</button>
            ))}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button style={{ ...s.btn(), flex: 1, justifyContent: "center" }} onClick={onClose}><Calendar size={13} /> Crear en Outlook</button>
          <button style={{ ...s.btn("secondary") }} onClick={onClose}>Cancelar</button>
        </div>
      </div>
    </div>
  );
}

// ── CALENDAR VIEW ──────────────────────────────────────────────
function CalendarView() {
  const [showAdd, setShowAdd] = useState(false);
  const eventColor = { reunion: COLORS.accent, personal: COLORS.green, bloqueo: COLORS.amber };
  const hours = Array.from({ length: 10 }, (_, i) => i + 8);

  return (
    <div>
      {showAdd && <AddEventModal onClose={() => setShowAdd(false)} />}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <div>
          <div style={{ fontSize: 18, fontWeight: 700, letterSpacing: "-0.01em" }}>Calendario Outlook</div>
          <div style={{ fontSize: 11, color: COLORS.textSecondary, marginTop: 2 }}>Martes 13 de mayo · 4 eventos</div>
        </div>
        <button style={s.btn()} onClick={() => setShowAdd(true)}>
          <Plus size={13} /> Nuevo evento
        </button>
      </div>

      {/* leyenda */}
      <div style={{ display: "flex", gap: 14, marginBottom: 16 }}>
        {Object.entries(eventColor).map(([k, c]) => (
          <div key={k} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, color: COLORS.textSecondary }}>
            <div style={{ width: 8, height: 8, borderRadius: 2, background: c }} />
            <span style={{ textTransform: "capitalize" }}>{k}</span>
          </div>
        ))}
      </div>

      {/* timeline */}
      <div style={{ background: COLORS.surface, border: `1px solid ${COLORS.border}`, borderRadius: 8, overflow: "hidden" }}>
        {hours.map(h => {
          const eventsAtHour = CALENDAR_EVENTS.filter(e => parseInt(e.time) === h);
          return (
            <div key={h} style={{ display: "flex", borderBottom: `1px solid ${COLORS.border}`, minHeight: 52 }}>
              <div style={{ width: 56, padding: "8px 12px", fontSize: 11, color: COLORS.textMuted, flexShrink: 0, borderRight: `1px solid ${COLORS.border}`, paddingTop: 10 }}>
                {String(h).padStart(2, "0")}:00
              </div>
              <div style={{ flex: 1, padding: "6px 10px", display: "flex", flexDirection: "column", gap: 4 }}>
                {eventsAtHour.map(ev => (
                  <div key={ev.id} style={{ background: eventColor[ev.type] + "18", border: `1px solid ${eventColor[ev.type]}50`, borderLeft: `3px solid ${eventColor[ev.type]}`, borderRadius: 5, padding: "6px 10px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 600, color: COLORS.textPrimary }}>{ev.title}</div>
                      <div style={{ fontSize: 10, color: COLORS.textSecondary, marginTop: 2, display: "flex", gap: 10 }}>
                        <span><Clock size={9} style={{ verticalAlign: "middle" }} /> {ev.time} · {ev.duration} min</span>
                        {ev.attendees.length > 0 && <span><User size={9} style={{ verticalAlign: "middle" }} /> {ev.attendees.join(", ")}</span>}
                      </div>
                    </div>
                    <span style={s.tag(eventColor[ev.type])}>{ev.type}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── ROOT APP ───────────────────────────────────────────────────
export default function App() {
  const [view, setView] = useState("priority");

  return (
    <div style={s.app}>
      {/* sidebar */}
      <div style={s.sidebar}>
        <div style={s.logo}>◈ Daily OS</div>
        {NAV_ITEMS.map(item => (
          <div key={item.id} style={s.navItem(view === item.id)} onClick={() => setView(item.id)}>
            <item.icon size={14} />
            <span>{item.label}</span>
          </div>
        ))}
        <div style={{ marginTop: "auto", padding: "16px 20px", borderTop: `1px solid ${COLORS.border}` }}>
          <div style={{ fontSize: 10, color: COLORS.textMuted, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 6 }}>Conectado a</div>
          {[
            { label: "Outlook", color: COLORS.blue },
            { label: "Notion", color: COLORS.accent },
            { label: "Jira", color: COLORS.amber },
          ].map(c => (
            <div key={c.label} style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4, fontSize: 11, color: COLORS.textSecondary }}>
              <div style={{ width: 6, height: 6, borderRadius: "50%", background: c.color }} /> {c.label}
            </div>
          ))}
        </div>
      </div>

      {/* main */}
      <div style={s.main}>
        <div style={s.topbar}>
          <div>
            <div style={s.topbarTitle}>
              { view === "priority" ? "Prioridades del día" : view === "tasks" ? "Gestión de tareas" : "Calendario" }
            </div>
            <div style={s.topbarSub}>Sincronizado con Outlook + Notion via MCP</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11, color: COLORS.textSecondary }}>
            <div style={{ width: 7, height: 7, borderRadius: "50%", background: COLORS.green }} />
            Agente activo
          </div>
        </div>
        <div style={s.content}>
          {view === "priority" && <PriorityView />}
          {view === "tasks"    && <TasksView />}
          {view === "calendar" && <CalendarView />}
        </div>
      </div>
    </div>
  );
}
