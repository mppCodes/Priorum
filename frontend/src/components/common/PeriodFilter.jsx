import { s } from "../../constants/styles.js";

const PERIODS = [
  { id: "day",   label: "Hoy" },
  { id: "week",  label: "Semana" },
  { id: "month", label: "Mes" },
  { id: "year",  label: "Año" },
];

/**
 * Barra de filtro de período reutilizable (día / semana / mes / año).
 */
export default function PeriodFilter({ value, onChange }) {
  return (
    <div style={s.filterBar}>
      {PERIODS.map((p) => (
        <button
          key={p.id}
          onClick={() => onChange(p.id)}
          style={s.btn(value === p.id ? "primary" : "secondary")}
        >
          {p.label}
        </button>
      ))}
    </div>
  );
}