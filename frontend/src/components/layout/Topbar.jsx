import { RefreshCw } from "lucide-react";
import { COLORS } from "../../constants/colors.js";
import { s } from "../../constants/styles.js";

const VIEW_TITLES = {
  priority: "Prioridades del día",
  tasks:    "Gestión de tareas",
  calendar: "Calendario",
  agent:    "Agente IA",
};

export default function Topbar({ view, onSync, syncing = false }) {
  return (
    <div style={s.topbar}>
      <div>
        <div style={s.topbarTitle}>{VIEW_TITLES[view] || "Priorum"}</div>
        <div style={s.topbarSub}>Sincronizado con Outlook + Notion via MCP</div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        {onSync && (
          <button
            style={{
              ...s.btn("secondary"),
              padding: "5px 10px",
              opacity: syncing ? 0.6 : 1,
            }}
            onClick={onSync}
            disabled={syncing}
            title="Sincronizar datos"
          >
            <RefreshCw
              size={12}
              style={{
                animation: syncing ? "spin 1s linear infinite" : "none",
              }}
            />
            {syncing ? "Sincronizando…" : "Sync"}
          </button>
        )}

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            fontSize: 11,
            color: COLORS.textSecondary,
          }}
        >
          <div
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: COLORS.green,
            }}
          />
          Agente activo
        </div>
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}