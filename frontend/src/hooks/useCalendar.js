import { useState, useEffect, useCallback } from "react";
import { getEvents, createEvent, updateEvent, deleteEvent, syncCalendar } from "../services/calendarService.js";

// ── Mapeo de tipos frontend ↔ backend ─────────────────────────────────────────
const TYPE_TO_BACKEND = {
  reunion:  "meeting",
  personal: "other",
  bloqueo:  "other",
  meeting:  "meeting",
  other:    "other",
  focus:    "focus",
  call:     "call",
  out_of_office: "out_of_office",
  reminder: "reminder",
};

const TYPE_TO_FRONTEND = {
  meeting:      "reunion",
  call:         "reunion",
  focus:        "bloqueo",
  out_of_office:"bloqueo",
  reminder:     "personal",
  other:        "personal",
};

/**
 * Convierte un evento del backend (start/end datetime) al formato del frontend (date/time/duration).
 */
function toFrontendEvent(ev) {
  if (!ev) return ev;
  // Si ya tiene el formato antiguo, devolverlo tal cual
  if (ev.time && ev.duration !== undefined) return ev;

  const startDate = ev.start ? new Date(ev.start) : null;
  const endDate   = ev.end   ? new Date(ev.end)   : null;

  const date     = startDate ? startDate.toISOString().slice(0, 10) : "";
  const time     = startDate
    ? `${String(startDate.getHours()).padStart(2, "0")}:${String(startDate.getMinutes()).padStart(2, "0")}`
    : "";
  const duration = startDate && endDate
    ? Math.round((endDate - startDate) / 60000)
    : 30;

  // Asistentes: pueden ser objetos { email, name } o strings
  const attendees = (ev.attendees || []).map((a) =>
    typeof a === "string" ? a : (a.name || a.email || "")
  );

  return {
    ...ev,
    date,
    time,
    duration,
    type: TYPE_TO_FRONTEND[ev.type] || ev.type || "reunion",
    attendees,
    notes: ev.description || "",
  };
}

/**
 * Convierte un evento del frontend (date/time/duration) al formato del backend (start/end datetime).
 */
function toBackendEvent(ev) {
  const { date, time, duration, notes, type, ...rest } = ev;

  const startISO = date && time ? `${date}T${time}:00` : undefined;
  const endISO   = startISO && duration
    ? new Date(new Date(startISO).getTime() + duration * 60000).toISOString().slice(0, 19)
    : undefined;

  return {
    ...rest,
    title: ev.title,
    start: startISO,
    end:   endISO,
    description: notes || ev.description || "",
    type: TYPE_TO_BACKEND[type] || "meeting",
  };
}

/**
 * Hook para gestionar eventos del calendario.
 * @param {Object} initialFilters - { period: "day"|"week"|"month"|"year", date }
 */
export function useCalendar(initialFilters = { period: "day" }) {
  const [events, setEvents] = useState([]);
  const [filters, setFilters] = useState(initialFilters);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [syncing, setSyncing] = useState(false);

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getEvents(filters);
      // Normalizar al formato frontend
      setEvents((data || []).map(toFrontendEvent));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  const addEvent = async (eventData) => {
    try {
      const payload  = toBackendEvent(eventData);
      const newEvent = await createEvent(payload);
      const fe = toFrontendEvent(newEvent);
      setEvents((prev) =>
        [...prev, fe].sort((a, b) => (a.time || "").localeCompare(b.time || ""))
      );
      return fe;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const editEvent = async (eventId, data) => {
    try {
      const payload = toBackendEvent(data);
      const updated = await updateEvent(eventId, payload);
      const fe = toFrontendEvent(updated);
      setEvents((prev) => prev.map((e) => (e.id === eventId ? fe : e)));
      return fe;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const removeEvent = async (eventId) => {
    try {
      await deleteEvent(eventId);
      setEvents((prev) => prev.filter((e) => e.id !== eventId));
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const sync = async () => {
    setSyncing(true);
    try {
      await syncCalendar();
      await fetchEvents();
    } catch (err) {
      setError(err.message);
    } finally {
      setSyncing(false);
    }
  };

  const updateFilters = (newFilters) => {
    setFilters((prev) => ({ ...prev, ...newFilters }));
  };

  // Calcula slots libres entre eventos del día
  const getFreeSlots = () => {
    const dayEvents = events
      .filter((e) => e.time)
      .sort((a, b) => a.time.localeCompare(b.time));

    const slots = [];
    let cursor = "08:00";

    for (const ev of dayEvents) {
      if (ev.time > cursor) slots.push({ from: cursor, to: ev.time });
      const [h, m] = ev.time.split(":").map(Number);
      const endMin = h * 60 + m + (ev.duration || 30);
      cursor = `${String(Math.floor(endMin / 60)).padStart(2, "0")}:${String(endMin % 60).padStart(2, "0")}`;
    }
    if (cursor < "18:00") slots.push({ from: cursor, to: "18:00" });
    return slots;
  };

  return {
    events,
    filters,
    loading,
    error,
    syncing,
    addEvent,
    editEvent,
    removeEvent,
    sync,
    refresh: fetchEvents,
    updateFilters,
    getFreeSlots,
  };
}