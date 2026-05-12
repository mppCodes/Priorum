import { useState, useEffect, useCallback } from "react";
import { getTasks, createTask, updateTask, deleteTask, syncTasks } from "../services/tasksService.js";

/**
 * Hook para gestionar tareas.
 * @param {Object} initialFilters - { period: "day"|"week"|"month"|"year", date, priority, project }
 */
export function useTasks(initialFilters = { period: "day" }) {
  const [tasks, setTasks] = useState([]);
  const [filters, setFilters] = useState(initialFilters);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [syncing, setSyncing] = useState(false);

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getTasks(filters);
      setTasks(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const addTask = async (taskData) => {
    try {
      const newTask = await createTask(taskData);
      setTasks((prev) => [newTask, ...prev]);
      return newTask;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const editTask = async (taskId, data) => {
    try {
      const updated = await updateTask(taskId, data);
      setTasks((prev) => prev.map((t) => (t.id === taskId ? updated : t)));
      return updated;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const removeTask = async (taskId) => {
    try {
      await deleteTask(taskId);
      setTasks((prev) => prev.filter((t) => t.id !== taskId));
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const sync = async () => {
    setSyncing(true);
    try {
      await syncTasks();
      await fetchTasks();
    } catch (err) {
      setError(err.message);
    } finally {
      setSyncing(false);
    }
  };

  const updateFilters = (newFilters) => {
    setFilters((prev) => ({ ...prev, ...newFilters }));
  };

  return {
    tasks,
    filters,
    loading,
    error,
    syncing,
    addTask,
    editTask,
    removeTask,
    sync,
    refresh: fetchTasks,
    updateFilters,
  };
}