import { useState, useEffect, useCallback } from "react";
import { getEvents, createEvent, updateEvent, deleteEvent, syncCalendar } from "../services/calendarService.js";

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
      setEvents(data);
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
      const newEvent = await createEvent(eventData);
      // Refresh from backend to ensure consistent data
      await fetchEvents();
      return newEvent;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const editEvent = async (eventId, data) => {
    try {
      const updated = await updateEvent(eventId, data);
      setEvents((prev) => prev.map((e) => (e.id === eventId ? updated : e)));
      return updated;
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
    const toTime = (isoStr) => {
      if (!isoStr) return "";
      const d = new Date(isoStr);
      return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
    };
    const dayEvents = events
      .filter((e) => e.start)
      .sort((a, b) => (a.start || "").localeCompare(b.start || ""));

    const slots = [];
    let cursor = "08:00";

    for (const ev of dayEvents) {
      const evStart = toTime(ev.start);
      const evEnd = toTime(ev.end);
      if (evStart > cursor) slots.push({ from: cursor, to: evStart });
      cursor = evEnd || cursor;
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