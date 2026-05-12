import { useState } from "react";
import { s } from "./constants/styles.js";
import Sidebar from "./components/layout/Sidebar.jsx";
import Topbar from "./components/layout/Topbar.jsx";
import PriorityView from "./components/priority/PriorityView.jsx";
import TasksView from "./components/tasks/TasksView.jsx";
import CalendarView from "./components/calendar/CalendarView.jsx";
import AgentPanel from "./components/agent/AgentPanel.jsx";

export default function App() {
  const [view, setView] = useState("priority");

  return (
    <div style={s.app}>
      <Sidebar view={view} onNavigate={setView} />

      <div style={s.main}>
        <Topbar view={view} />

        <div style={s.content}>
          {view === "priority" && <PriorityView />}
          {view === "tasks"    && <TasksView />}
          {view === "calendar" && <CalendarView />}
          {view === "agent"    && <AgentPanel />}
        </div>
      </div>
    </div>
  );
}