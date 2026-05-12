import { useState, useCallback } from "react";
import { chat, getDailyPriorities, getScheduleSuggestion, getChatHistory, clearChatHistory } from "../services/agentService.js";

/**
 * Hook para interactuar con el agente IA.
 */
export function useAgent() {
  const [messages, setMessages] = useState([]);
  const [priorities, setPriorities] = useState([]);
  const [scheduleSuggestion, setScheduleSuggestion] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const sendMessage = useCallback(async (message, context = {}) => {
    setLoading(true);
    setError(null);

    // Añade mensaje del usuario inmediatamente
    const userMsg = { role: "user", content: message, timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const response = await chat(message, context);
      const agentMsg = {
        role: "agent",
        content: response.message,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, agentMsg]);
      return response;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchPriorities = useCallback(async (context) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDailyPriorities(context);
      setPriorities(data.priorities || []);
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchScheduleSuggestion = useCallback(async (context) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getScheduleSuggestion(context);
      setScheduleSuggestion(data);
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const loadHistory = useCallback(async () => {
    try {
      const data = await getChatHistory();
      setMessages(data.messages || []);
    } catch (err) {
      setError(err.message);
    }
  }, []);

  const clearHistory = useCallback(async () => {
    try {
      await clearChatHistory();
      setMessages([]);
    } catch (err) {
      setError(err.message);
    }
  }, []);

  return {
    messages,
    priorities,
    scheduleSuggestion,
    loading,
    error,
    sendMessage,
    fetchPriorities,
    fetchScheduleSuggestion,
    loadHistory,
    clearHistory,
  };
}