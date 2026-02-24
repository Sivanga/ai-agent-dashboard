import { useState } from "react";
import AgentList from "./components/AgentList";
import ChatWindow from "./components/ChatWindow";
import "./App.css";

export default function App() {
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleAgentSelect = (agent) => {
    setSelectedAgent(agent);
    setSidebarOpen(false);
  };

  return (
    <div className="app">
      <header className="header">
        <button className="hamburger" onClick={() => setSidebarOpen(!sidebarOpen)}>
          <span></span><span></span><span></span>
        </button>
        <div>
          <h1>Agent Dashboard</h1>
          <p>Enterprise AI Solutions</p>
        </div>
      </header>
      <div className="main">
        {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />}
        <aside className={`sidebar ${sidebarOpen ? "open" : ""}`}>
          <AgentList
            selectedAgent={selectedAgent}
            onSelect={handleAgentSelect}
          />
        </aside>
        <section className="content">
          {selectedAgent ? (
            <ChatWindow agent={selectedAgent} />
          ) : (
            <div className="welcome">
              <h2>Welcome</h2>
              <p>Select an agent from the sidebar to start a conversation.</p>
              <div className="features">
                <div className="feature-card">
                  <span className="feature-icon">CS</span>
                  <h3>Customer Support</h3>
                  <p>AI-powered support with knowledge base lookup</p>
                </div>
                <div className="feature-card">
                  <span className="feature-icon">MP</span>
                  <h3>Meeting Prep</h3>
                  <p>Auto-research companies before meetings</p>
                </div>
                <div className="feature-card">
                  <span className="feature-icon">RA</span>
                  <h3>Retail Analyzer</h3>
                  <p>Sales, inventory, and customer insights</p>
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
