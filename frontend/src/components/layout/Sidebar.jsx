import { Brain, CheckSquare, Calendar, MessageSquare, Settings } from "lucide-react";
import { COLORS } from "../../constants/colors.js";
import { s } from "../../constants/styles.js";

const NAV_ITEMS = [
  { id: "priority", icon: Brain,         label: "Prioridades" },
  { id: "tasks",    icon: CheckSquare,   label: "Tareas" },
  { id: "calendar", icon: Calendar,      label: "Calendario" },
  { id: "agent",    icon: MessageSquare, label: "Agente IA" },
  { id: "settings", icon: Settings,      label: "Configuración" },
];

export default function Sidebar({ view, onNavigate, agentStatus = "active" }) {
  return (
    <div style={s.sidebar}>
      <div style={s.logo}>◈ Priorum</div>

      {NAV_ITEMS.map((item) => (
        <div
          key={item.id}
          style={s.navItem(view === item.id)}
          onClick={() => onNavigate(item.id)}
        >
          <item.icon size={14} />
          <span>{item.label}</span>
        </div>
      ))}

      {/* Conexiones */}
      <div
        style={{
          marginTop: "auto",
          padding: "16px 20px",
          borderTop: `1px solid ${COLORS.border}`,
        }}
      >
        <div
          style={{
            fontSize: 10,
            color: COLORS.textMuted,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            marginBottom: 8,
          }}
        >
          Conectado a
        </div>
        {[
          { label: "Outlook", color: COLORS.blue },
          { label: "Notion",  color: COLORS.accent },
        ].map((c) => (
          <div
            key={c.label}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              marginBottom: 4,
              fontSize: 11,
              color: COLORS.textSecondary,
            }}
          >
            <div
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: c.color,
              }}
            />
            {c.label}
          </div>
        ))}

        {/* Estado del agente */}
        <div
          style={{
            marginTop: 12,
            display: "flex",
            alignItems: "center",
            gap: 6,
            fontSize: 10,
            color: agentStatus === "active" ? COLORS.green : COLORS.textMuted,
          }}
        >
          <div
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: agentStatus === "active" ? COLORS.green : COLORS.textMuted,
            }}
          />
          Agente {agentStatus === "active" ? "activo" : "inactivo"}
        </div>
      </div>
    </div>
  );
}