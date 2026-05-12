export const COLORS = {
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

export const priorityConfig = {
  alta:  { color: COLORS.red,   label: "Alta" },
  media: { color: COLORS.amber, label: "Media" },
  baja:  { color: COLORS.green, label: "Baja" },
};

export const eventTypeConfig = {
  reunion:  { color: COLORS.accent, label: "Reunión" },
  personal: { color: COLORS.green,  label: "Personal" },
  bloqueo:  { color: COLORS.amber,  label: "Bloqueo" },
};