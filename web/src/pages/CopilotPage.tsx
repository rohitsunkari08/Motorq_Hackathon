import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { CopilotMessage } from '../types';
import {
  Bot,
  User as UserIcon,
  Send,
  Sparkles,
  ShieldCheck,
  Cpu,
  Layers,
  CheckCircle2,
  Terminal,
  AlertCircle,
} from 'lucide-react';

interface CopilotPageProps {
  onSelectVehicle: (vin: string) => void;
}

const INITIAL_MESSAGES: CopilotMessage[] = [
  {
    id: 'msg-1',
    sender: 'copilot',
    timestamp: new Date(Date.now() - 10 * 60 * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    text: "Hello! I am your EV Fleet Charging & Battery-Health Copilot. I analyze real-time telematics from Redpanda, ClickHouse rollups, and our XGBoost degradation models. How can I assist your fleet operations today?",
    guardrails: {
      delegatedJwt: true,
      roleChecked: true,
      readOnlyEnforced: true,
      maskingApplied: true,
    },
  },
  {
    id: 'msg-2',
    sender: 'user',
    timestamp: new Date(Date.now() - 8 * 60 * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    text: "Which vehicles are currently at risk of stranding or have critical alerts?",
  },
  {
    id: 'msg-3',
    sender: 'copilot',
    timestamp: new Date(Date.now() - 7 * 60 * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    text: "I retrieved the active fleet alert queue and identified 1 critical RANGE_RISK vehicle:\n\n• **VIN: 3ADEV03C300000003** (AsiaDrive Express-V)\n- Current SoC: **11.4%**\n- Estimated usable range: **28.4 km**\n- Nearest charger distance: **24.1 km** (Market St Hub)\n- Safety margin buffer: **1.18x** (threshold is 1.20x)\n\nRecommendation: Dispatch an immediate charging detour alert to driver Kenji Takahashi.",
    toolCalls: [
      {
        name: 'list_at_risk_vehicles',
        args: { tenant_id: 1, limit: 10 },
        status: 'success',
      },
      {
        name: 'get_vehicle_status',
        args: { vin: '3ADEV03C300000003' },
        status: 'success',
      },
    ],
    guardrails: {
      delegatedJwt: true,
      roleChecked: true,
      readOnlyEnforced: true,
      maskingApplied: true,
    },
  },
];

export const CopilotPage: React.FC<CopilotPageProps> = ({ onSelectVehicle }) => {
  const { user } = useAuth();
  const [messages, setMessages] = useState<CopilotMessage[]>(INITIAL_MESSAGES);
  const [inputPrompt, setInputPrompt] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  const samplePrompts = [
    'Which vehicles are at risk of stranding?',
    'Explain the thermal alert on vehicle 2NMEV02B200000002',
    'Propose an optimal charging schedule for vehicle 1VXEV01A100000001',
    'How does our fleet SoH compare to industry peer benchmarks?',
  ];

  const handleSend = (textToSend?: string) => {
    const prompt = textToSend || inputPrompt;
    if (!prompt.trim()) return;

    const userMsg: CopilotMessage = {
      id: `msg-${Date.now()}`,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      text: prompt,
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInputPrompt('');
    setIsTyping(true);

    // Simulate LangGraph Agent tool call reasoning
    setTimeout(() => {
      let botResponse = '';
      let tools: CopilotMessage['toolCalls'] = [];

      if (prompt.toLowerCase().includes('thermal')) {
        botResponse =
          "Analysis of vehicle **2NMEV02B200000002** (NordMotors Polar-4):\n\n• The battery pack reached **51.4°C** during a 135 kW DC fast-charging session (sustained for 75 seconds).\n• Thermal threshold: **50.0°C**.\n• RAG Knowledge Base recommendation: Throttling charge rate to 70 kW reduces pack heating by 38% and avoids lithium plating.";
        tools = [
          { name: 'explain_alert', args: { alert_id: 103 }, status: 'success' },
          { name: 'search_kb', args: { query: 'DC fast charge thermal limit degradation' }, status: 'success' },
        ];
      } else if (prompt.toLowerCase().includes('schedule') || prompt.toLowerCase().includes('propose')) {
        botResponse =
          "Generated optimal battery-aware schedule for **1VXEV01A100000001** via Dynamic Programming:\n\n• Baseline Cost: **$14.85** (Immediate 150 kW peak arrival charge)\n• DP Optimized Cost: **$9.65** (Shifted to 00:00–04:00 ultra off-peak)\n• Net Savings: **35.0% ($5.20/charge)**\n• Battery Stress Reduction: **64.8%**\n\n*Note: Plan has been created with status PROPOSED. Per security guardrails, human approval is required in the vehicle detail portal.*";
        tools = [
          { name: 'get_vehicle_status', args: { vin: '1VXEV01A100000001' }, status: 'success' },
          { name: 'propose_charge_plan', args: { vin: '1VXEV01A100000001', target_soc: 85, hours: 8 }, status: 'success' },
        ];
      } else if (prompt.toLowerCase().includes('benchmark') || prompt.toLowerCase().includes('peer')) {
        botResponse =
          "Differential Privacy Benchmark Result (ε = 1.0, Laplace noise added):\n\n• Fleet Model: **VoltX Hyper-e** (1-2 yr bracket)\n• Your Fleet Avg SoH: **96.2%**\n• Anonymized Peer Fleet Avg: **95.8%** [95.4% – 96.2% 95% CI]\n• Sample Size: **4,210 vehicles** (k-anonymity satisfied: n ≥ 20)\n\nConclusion: Your fleet is outperforming industry peers by **+0.4% SoH retention** due to smart off-peak charging.";
        tools = [
          { name: 'get_soh_benchmark', args: { model: 'Hyper-e', age_bucket: '1-2yr', epsilon: 1.0 }, status: 'success' },
        ];
      } else {
        botResponse =
          "Fleet Operations Summary (Tenant 1: VoltFleet):\n\n• Total Monitored Vehicles: **12,480**\n• Active in transit: **9,840**\n• Charging: **1,940**\n• Average State of Charge: **68.4%**\n• Mean Battery Health (SoH): **94.6%**\n• Open Alerts: **4** (1 Critical, 1 High, 1 Warn, 1 Info)\n\nAll operations are within SLA.";
        tools = [{ name: 'get_fleet_summary', args: { tenant_id: 1 }, status: 'success' }];
      }

      const copilotMsg: CopilotMessage = {
        id: `msg-${Date.now() + 1}`,
        sender: 'copilot',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        text: botResponse,
        toolCalls: tools,
        guardrails: {
          delegatedJwt: true,
          roleChecked: true,
          readOnlyEnforced: true,
          maskingApplied: true,
        },
      };

      setMessages((prev) => [...prev, copilotMsg]);
      setIsTyping(false);
    }, 900);
  };

  return (
    <div className="page-wrapper" id="page-copilot" style={{ height: 'calc(100vh - 120px)', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 style={{ fontSize: '1.75rem' }}>AI Copilot Intelligence</h1>
            <span className="badge badge-purple">LangGraph + LiteLLM</span>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Multi-step reasoning with delegated JWT, deterministic fallbacks, and RAG over synthetic battery-care docs.
          </p>
        </div>

        {/* Guardrail Status Pill */}
        <div
          id="copilot-guardrails-badge"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'var(--accent-purple-dim)',
            border: '1px solid rgba(139, 92, 246, 0.3)',
            padding: '6px 14px',
            borderRadius: 'var(--radius-md)',
            fontSize: '0.8rem',
            color: 'var(--accent-purple)',
          }}
        >
          <ShieldCheck size={16} />
          <span>Active Guardrails: Read/Propose-Only · Delegated JWT</span>
        </div>
      </div>

      {/* Chat Messages Container */}
      <div
        className="card"
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          padding: '20px',
          marginBottom: '16px',
        }}
      >
        <div style={{ flex: 1, overflowY: 'auto', paddingRight: '8px' }}>
          {messages.map((m) => {
            const isUser = m.sender === 'user';

            return (
              <div
                key={m.id}
                style={{
                  display: 'flex',
                  justifyContent: isUser ? 'flex-end' : 'flex-start',
                  marginBottom: '20px',
                }}
              >
                <div
                  style={{
                    maxWidth: '75%',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: isUser ? 'flex-end' : 'flex-start',
                  }}
                >
                  {/* Sender label & Timestamp */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      fontSize: '0.75rem',
                      color: 'var(--text-muted)',
                      marginBottom: '4px',
                    }}
                  >
                    {isUser ? (
                      <>
                        <span>{user?.email}</span>
                        <UserIcon size={12} />
                      </>
                    ) : (
                      <>
                        <Bot size={12} color="var(--accent-cyan)" />
                        <span style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>Copilot AI</span>
                      </>
                    )}
                    <span>· {m.timestamp}</span>
                  </div>

                  {/* Message Bubble */}
                  <div
                    style={{
                      padding: '14px 18px',
                      borderRadius: 'var(--radius-lg)',
                      background: isUser
                        ? 'linear-gradient(135deg, #00A3FF 0%, #0077B6 100%)'
                        : 'rgba(255, 255, 255, 0.04)',
                      border: isUser ? 'none' : '1px solid var(--border-color)',
                      color: '#ffffff',
                      fontSize: '0.9rem',
                      lineHeight: 1.5,
                      whiteSpace: 'pre-line',
                    }}
                  >
                    {m.text}
                  </div>

                  {/* Tool Invocations Timeline */}
                  {m.toolCalls && m.toolCalls.length > 0 && (
                    <div
                      style={{
                        marginTop: '8px',
                        background: 'rgba(10, 13, 20, 0.9)',
                        border: '1px solid rgba(0, 240, 255, 0.2)',
                        borderRadius: 'var(--radius-md)',
                        padding: '10px 14px',
                        width: '100%',
                      }}
                    >
                      <div
                        style={{
                          fontSize: '0.72rem',
                          fontWeight: 700,
                          color: 'var(--accent-cyan)',
                          textTransform: 'uppercase',
                          letterSpacing: '0.06em',
                          marginBottom: '6px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                        }}
                      >
                        <Terminal size={12} />
                        <span>LangGraph Tool Execution Trace</span>
                      </div>

                      {m.toolCalls.map((t, idx) => (
                        <div
                          key={idx}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            fontSize: '0.78rem',
                            fontFamily: 'var(--font-mono)',
                            color: 'var(--text-secondary)',
                            padding: '4px 0',
                            borderBottom: idx < m.toolCalls!.length - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none',
                          }}
                        >
                          <span>{t.name}({JSON.stringify(t.args)})</span>
                          <span className="badge badge-success" style={{ fontSize: '0.65rem' }}>
                            {t.status}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Safety Guardrails Applied */}
                  {m.guardrails && (
                    <div
                      style={{
                        marginTop: '6px',
                        display: 'flex',
                        gap: '6px',
                        fontSize: '0.68rem',
                        color: 'var(--text-muted)',
                      }}
                    >
                      <span className="badge badge-secondary" style={{ fontSize: '0.65rem' }}>
                        Delegated JWT
                      </span>
                      <span className="badge badge-secondary" style={{ fontSize: '0.65rem' }}>
                        Read/Propose-Only
                      </span>
                      <span className="badge badge-secondary" style={{ fontSize: '0.65rem' }}>
                        Audit Logged
                      </span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {isTyping && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-cyan)', fontSize: '0.85rem' }}>
              <Bot size={16} />
              <span>Copilot is reasoning and querying fleet state...</span>
            </div>
          )}
        </div>

        {/* Sample Prompt Chips */}
        <div style={{ marginTop: '12px', borderTop: '1px solid var(--border-color)', paddingTop: '12px' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
            Quick Fleet Queries:
          </div>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {samplePrompts.map((p, idx) => (
              <button
                key={idx}
                id={`btn-prompt-${idx}`}
                className="btn btn-secondary btn-sm"
                style={{ fontSize: '0.75rem', padding: '6px 10px' }}
                onClick={() => handleSend(p)}
              >
                <Sparkles size={12} color="var(--accent-cyan)" />
                {p}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Input Form */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        style={{ display: 'flex', gap: '12px' }}
      >
        <input
          id="input-copilot-prompt"
          type="text"
          className="form-input"
          placeholder="Ask Copilot about vehicle battery degradation, smart charging schedules, or alerts..."
          value={inputPrompt}
          onChange={(e) => setInputPrompt(e.target.value)}
          disabled={isTyping}
          style={{ flex: 1 }}
        />
        <button
          id="btn-send-copilot"
          type="submit"
          className="btn btn-primary"
          disabled={isTyping || !inputPrompt.trim()}
          style={{ padding: '0 24px' }}
        >
          <Send size={18} />
          Send
        </button>
      </form>
    </div>
  );
};
