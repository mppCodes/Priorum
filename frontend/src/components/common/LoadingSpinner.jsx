import { COLORS } from "../../constants/colors.js";

export default function LoadingSpinner({ message = "Cargando…" }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: 48,
        gap: 12,
        color: COLORS.textMuted,
        fontSize: 12,
      }}
    >
      <div
        style={{
          width: 24,
          height: 24,
          border: `2px solid ${COLORS.border}`,
          borderTop: `2px solid ${COLORS.accent}`,
          borderRadius: "50%",
          animation: "spin 0.8s linear infinite",
        }}
      />
      {message}
      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}