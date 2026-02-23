const AGENTS = [
  {
    id: "customer_support",
    name: "Customer Support",
    description: "Handles customer inquiries using a knowledge base",
    icon: "🏪",
  },
  {
    id: "meeting_prep",
    name: "Meeting Prep",
    description: "Researches companies and generates briefings",
    icon: "📋",
  },
];

export default function AgentList({ selectedAgent, onSelect }) {
  return (
    <div className="agent-list">
      <h2>Agents</h2>
      {AGENTS.map((agent) => (
        <div
          key={agent.id}
          className={`agent-card ${selectedAgent?.id === agent.id ? "active" : ""}`}
          onClick={() => onSelect(agent)}
        >
          <span className="agent-icon">{agent.icon}</span>
          <div>
            <h3>{agent.name}</h3>
            <p>{agent.description}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
