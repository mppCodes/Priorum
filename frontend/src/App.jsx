import { useState } from "react";
import { s } from "./constants/styles.js";
import Sidebar from "./components/layout/Sidebar.jsx";
import Topbar from "./components/layout/Topbar.jsx";
import PriorityView from "./components/priority/PriorityView.jsx";
import TasksView from "./components/tasks/TasksView.jsx";
import CalendarView from "./components/calendar/CalendarView.jsx";
import AgentPanel from "./components/agent/AgentPanel.jsx";
import { useTasks } from "./hooks/useTasks.js";
import { useCalendar } from "./hooks/useCalendar.js";

export default function App() {
  const [view, setView] = useState("priority");

  // Datos compartidos entre vistas (prioridades y agente los necesitan)
  const { tasks } = useTasks({ period: "day" });
  const { events } = useCalendar({ period: "day" });

  return (
    <div style={s.app}>
      <Sidebar view={view} onNavigate={setView} />

      <div style={s.main}>
        <Topbar view={view} />

        <div style={s.content}>
          {view === "priority" && <PriorityView tasks={tasks} events={events} />}
          {view === "tasks"    && <TasksView />}
          {view === "calendar" && <CalendarView />}
          {view === "agent"    && <AgentPanel tasks={tasks} events={events} />}
        </div>
      </div>
    </div>
  );
}