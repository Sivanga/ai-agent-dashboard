import { useState } from "react";
import AgentList from "./components/AgentList";
import ChatWindow from "./components/ChatWindow";
import "./App.css";

export default function App() {
  const [selectedAgent, setSelectedAgent] = useState(null);

  return (
    <div className="app">
      <header className="header">
        <h1>🤖 AI Agent Dashboard</h1>
        <p>Enterprise AI Solutions</p>
      </header>
      <div className="main">
        <aside className="sidebar">
          <AgentList
            selectedAgent={selectedAgent}
            onSelect={setSelectedAgent}
          />
        </aside>
        <section className="content">
          {selectedAgent ? (
            <ChatWindow agent={selectedAgent} />
          ) : (
            <div className="welcome">
              <h2>Welcome</h2>
              <p>Select an agent from the sidebar to start.</p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
