import React from 'react';
import {AbsoluteFill} from 'remotion';
import {theme} from './theme';

const Badge: React.FC<{text: string; color: string}> = ({text, color}) => (
  <div
    style={{
      display: 'inline-block',
      padding: '4px 12px',
      borderRadius: 6,
      backgroundColor: color + '22',
      color,
      fontSize: 14,
      fontWeight: 600,
      marginRight: 8,
    }}
  >
    {text}
  </div>
);

/* ── Slide 1: Problem ── */
export const SlideProblem: React.FC = () => (
  <AbsoluteFill
    style={{
      background: theme.bg,
      fontFamily: 'system-ui, -apple-system, sans-serif',
      padding: 80,
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
    }}
  >
    <div style={{fontSize: 18, color: theme.accent, fontWeight: 700, marginBottom: 16, textTransform: 'uppercase', letterSpacing: '0.1em'}}>
      The Problem
    </div>
    <div style={{fontSize: 48, fontWeight: 800, color: theme.text, lineHeight: 1.2, marginBottom: 40}}>
      AI agents fail silently<br />in production
    </div>
    <div style={{display: 'flex', gap: 24}}>
      {[
        {icon: '🔌', title: 'Tool Timeouts', desc: 'APIs go down, agents hang'},
        {icon: '🧠', title: 'Context Corruption', desc: 'Garbage in, hallucination out'},
        {icon: '💸', title: 'Budget Exhaustion', desc: 'Runaway token spending'},
      ].map((item) => (
        <div
          key={item.title}
          style={{
            flex: 1,
            background: theme.bgCard,
            border: `1px solid ${theme.border}`,
            borderRadius: 12,
            padding: 28,
          }}
        >
          <div style={{fontSize: 36, marginBottom: 12}}>{item.icon}</div>
          <div style={{fontSize: 20, fontWeight: 700, color: theme.text, marginBottom: 8}}>{item.title}</div>
          <div style={{fontSize: 16, color: theme.textMuted, lineHeight: 1.5}}>{item.desc}</div>
        </div>
      ))}
    </div>
  </AbsoluteFill>
);

/* ── Slide 2: Solution ── */
export const SlideSolution: React.FC = () => (
  <AbsoluteFill
    style={{
      background: theme.bg,
      fontFamily: 'system-ui, -apple-system, sans-serif',
      padding: 80,
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
    }}
  >
    <div style={{fontSize: 18, color: theme.green, fontWeight: 700, marginBottom: 16, textTransform: 'uppercase', letterSpacing: '0.1em'}}>
      The Solution
    </div>
    <div style={{fontSize: 48, fontWeight: 800, color: theme.text, lineHeight: 1.2, marginBottom: 48}}>
      Inject faults in dev.<br />Fix before production.
    </div>
    <div style={{display: 'flex', alignItems: 'center', gap: 20}}>
      {[
        {step: '1', label: 'Inject Faults', sub: 'Tool errors, delays, hallucinations', color: theme.accent},
        {step: '2', label: 'Measure Recovery', sub: 'MTTR & reliability scores', color: theme.blue},
        {step: '3', label: 'Fix & Harden', sub: 'Before users ever see a failure', color: theme.green},
      ].map((item, i) => (
        <React.Fragment key={item.step}>
          <div
            style={{
              flex: 1,
              background: theme.bgCard,
              border: `1px solid ${item.color}44`,
              borderRadius: 12,
              padding: 28,
              textAlign: 'center',
            }}
          >
            <div style={{fontSize: 36, fontWeight: 800, color: item.color, marginBottom: 8}}>{item.step}</div>
            <div style={{fontSize: 20, fontWeight: 700, color: theme.text, marginBottom: 8}}>{item.label}</div>
            <div style={{fontSize: 15, color: theme.textMuted}}>{item.sub}</div>
          </div>
          {i < 2 && <div style={{fontSize: 28, color: theme.textMuted}}>→</div>}
        </React.Fragment>
      ))}
    </div>
  </AbsoluteFill>
);

/* ── Slide 3: Architecture ── */
export const SlideArchitecture: React.FC = () => {
  const boxStyle = (color: string): React.CSSProperties => ({
    background: theme.bgCard,
    border: `1px solid ${color}55`,
    borderRadius: 10,
    padding: '14px 20px',
    textAlign: 'center',
    fontSize: 15,
    fontWeight: 600,
    color: theme.text,
  });

  return (
    <AbsoluteFill
      style={{
        background: theme.bg,
        fontFamily: 'system-ui, -apple-system, sans-serif',
        padding: 80,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
      }}
    >
      <div style={{fontSize: 18, color: theme.blue, fontWeight: 700, marginBottom: 16, textTransform: 'uppercase', letterSpacing: '0.1em'}}>
        How It Works
      </div>
      <div style={{fontSize: 42, fontWeight: 800, color: theme.text, lineHeight: 1.2, marginBottom: 48}}>
        Architecture Overview
      </div>

      <div style={{display: 'flex', alignItems: 'flex-start', gap: 32}}>
        {/* Injectors column */}
        <div style={{flex: 1}}>
          <div style={{fontSize: 13, color: theme.accent, fontWeight: 700, marginBottom: 12, textTransform: 'uppercase'}}>Fault Injectors</div>
          <div style={{display: 'flex', flexDirection: 'column', gap: 8}}>
            {['Tool Failures', 'Latency Spikes', 'Hallucinations', 'Context Corruption', 'Budget Exhaustion'].map((name) => (
              <div key={name} style={boxStyle(theme.accent)}>{name}</div>
            ))}
          </div>
        </div>

        <div style={{display: 'flex', alignItems: 'center', paddingTop: 80, fontSize: 28, color: theme.textMuted}}>→</div>

        {/* Core */}
        <div style={{flex: 1.2}}>
          <div style={{fontSize: 13, color: theme.blue, fontWeight: 700, marginBottom: 12, textTransform: 'uppercase'}}>Experiment Engine</div>
          <div style={{background: theme.bgCard, border: `1px solid ${theme.blue}55`, borderRadius: 12, padding: 24}}>
            <div style={{fontSize: 16, fontWeight: 700, color: theme.text, marginBottom: 12}}>Your Agent</div>
            <div style={{fontSize: 14, color: theme.textMuted, marginBottom: 16}}>CrewAI / AutoGen / LangChain / Claude SDK</div>
            <div style={{display: 'flex', gap: 8}}>
              <Badge text="MTTR" color={theme.green} />
              <Badge text="Reliability" color={theme.green} />
              <Badge text="Recovery" color={theme.green} />
            </div>
          </div>
        </div>

        <div style={{display: 'flex', alignItems: 'center', paddingTop: 80, fontSize: 28, color: theme.textMuted}}>→</div>

        {/* Reports */}
        <div style={{flex: 1}}>
          <div style={{fontSize: 13, color: theme.green, fontWeight: 700, marginBottom: 12, textTransform: 'uppercase'}}>Reports</div>
          <div style={{display: 'flex', flexDirection: 'column', gap: 8}}>
            {['Terminal Output', 'JSON Export', 'Markdown', 'HTML Dashboard'].map((name) => (
              <div key={name} style={boxStyle(theme.green)}>{name}</div>
            ))}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ── Slide 4: Report Screenshot ── */
export const SlideReport: React.FC = () => (
  <AbsoluteFill
    style={{
      background: theme.bg,
      fontFamily: 'monospace',
      padding: 60,
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
    }}
  >
    <div style={{fontSize: 18, color: theme.purple, fontWeight: 700, marginBottom: 16, textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: 'system-ui, sans-serif'}}>
      Example Report
    </div>
    <div
      style={{
        background: theme.codeBg,
        border: `1px solid ${theme.border}`,
        borderRadius: 12,
        padding: 36,
        fontSize: 15,
        lineHeight: 1.8,
        color: theme.text,
      }}
    >
      <div style={{color: theme.textMuted, marginBottom: 12}}>$ balaganagent demo --chaos-level 0.5</div>
      <div style={{marginBottom: 8}}>
        <span style={{color: theme.accent}}>{'═══ BalaganAgent Chaos Report ═══'}</span>
      </div>
      <div><span style={{color: theme.textMuted}}>Experiment:</span> stress_test_crew</div>
      <div><span style={{color: theme.textMuted}}>Chaos Level:</span> <span style={{color: theme.yellow}}>0.50</span></div>
      <div><span style={{color: theme.textMuted}}>Duration:</span> 12.4s</div>
      <div style={{marginTop: 12, marginBottom: 12, borderTop: `1px solid ${theme.border}`, paddingTop: 12}}>
        <span style={{color: theme.blue}}>{'── Metrics ──'}</span>
      </div>
      <div><span style={{color: theme.textMuted}}>Total Runs:</span> 10</div>
      <div><span style={{color: theme.green}}>Successful:</span> <span style={{color: theme.green}}>8/10 (80%)</span></div>
      <div><span style={{color: theme.accentAlt}}>Failed:</span> <span style={{color: theme.accentAlt}}>2/10 (20%)</span></div>
      <div><span style={{color: theme.textMuted}}>Mean Time to Recovery:</span> <span style={{color: theme.yellow}}>2.3s</span></div>
      <div><span style={{color: theme.textMuted}}>Reliability Score:</span> <span style={{color: theme.green}}>0.82 / 1.00</span></div>
      <div style={{marginTop: 12, marginBottom: 12, borderTop: `1px solid ${theme.border}`, paddingTop: 12}}>
        <span style={{color: theme.blue}}>{'── Faults Injected ──'}</span>
      </div>
      <div><span style={{color: theme.accent}}>tool_failure</span> ×4 &nbsp; <span style={{color: theme.yellow}}>latency</span> ×3 &nbsp; <span style={{color: theme.purple}}>hallucination</span> ×2 &nbsp; <span style={{color: theme.accentAlt}}>budget</span> ×1</div>
      <div style={{marginTop: 16, color: theme.green}}>{'✓ Report saved → report.html'}</div>
    </div>
  </AbsoluteFill>
);

/* ── Slide 5: 3-line integration ── */
export const SlideCode: React.FC = () => (
  <AbsoluteFill
    style={{
      background: theme.bg,
      fontFamily: 'system-ui, -apple-system, sans-serif',
      padding: 80,
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
    }}
  >
    <div style={{fontSize: 18, color: theme.yellow, fontWeight: 700, marginBottom: 16, textTransform: 'uppercase', letterSpacing: '0.1em'}}>
      3-Line Integration
    </div>
    <div style={{fontSize: 42, fontWeight: 800, color: theme.text, lineHeight: 1.2, marginBottom: 48}}>
      Works with any framework
    </div>
    <div
      style={{
        background: theme.codeBg,
        border: `1px solid ${theme.border}`,
        borderRadius: 12,
        padding: 36,
        fontFamily: 'monospace',
        fontSize: 18,
        lineHeight: 2,
        color: theme.text,
      }}
    >
      <div style={{color: theme.textMuted}}>{'# pip install balagan-agent'}</div>
      <div>
        <span style={{color: theme.purple}}>from</span> balaganagent <span style={{color: theme.purple}}>import</span> ChaosExperiment
      </div>
      <div>&nbsp;</div>
      <div>
        experiment = ChaosExperiment(chaos_level=<span style={{color: theme.yellow}}>0.5</span>)
      </div>
      <div>
        experiment.wrap_crew(your_crew)
      </div>
      <div>
        results = experiment.run()
      </div>
    </div>
    <div style={{display: 'flex', gap: 12, marginTop: 32}}>
      {['CrewAI', 'AutoGen', 'LangChain', 'Claude SDK', 'Custom'].map((fw) => (
        <Badge key={fw} text={fw} color={theme.blue} />
      ))}
    </div>
  </AbsoluteFill>
);

/* ── Slide 6: Stress test results ── */
export const SlideStress: React.FC = () => {
  const levels = [
    {chaos: '0.1', pass: '100%', color: theme.green},
    {chaos: '0.3', pass: '93%', color: theme.green},
    {chaos: '0.5', pass: '80%', color: theme.yellow},
    {chaos: '0.7', pass: '62%', color: theme.accent},
    {chaos: '0.9', pass: '41%', color: theme.accentAlt},
  ];

  return (
    <AbsoluteFill
      style={{
        background: theme.bg,
        fontFamily: 'system-ui, -apple-system, sans-serif',
        padding: 80,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
      }}
    >
      <div style={{fontSize: 18, color: theme.accentAlt, fontWeight: 700, marginBottom: 16, textTransform: 'uppercase', letterSpacing: '0.1em'}}>
        Stress Test Results
      </div>
      <div style={{fontSize: 42, fontWeight: 800, color: theme.text, lineHeight: 1.2, marginBottom: 48}}>
        Find your agent's breaking point
      </div>

      <div style={{display: 'flex', flexDirection: 'column', gap: 12}}>
        {levels.map((l) => (
          <div key={l.chaos} style={{display: 'flex', alignItems: 'center', gap: 16}}>
            <div style={{width: 120, fontSize: 16, color: theme.textMuted, fontFamily: 'monospace'}}>
              chaos={l.chaos}
            </div>
            <div style={{flex: 1, background: theme.bgCard, borderRadius: 8, height: 40, overflow: 'hidden', border: `1px solid ${theme.border}`}}>
              <div
                style={{
                  width: l.pass,
                  height: '100%',
                  background: `linear-gradient(90deg, ${l.color}88, ${l.color})`,
                  borderRadius: 8,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'flex-end',
                  paddingRight: 12,
                }}
              >
                <span style={{fontSize: 14, fontWeight: 700, color: theme.text}}>{l.pass} pass</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div style={{marginTop: 32, fontSize: 16, color: theme.textMuted}}>
        10 runs per chaos level &middot; CrewAI research agent &middot; 5 fault types enabled
      </div>
    </AbsoluteFill>
  );
};
