import React from 'react';
import {AbsoluteFill, Sequence, useCurrentFrame, interpolate, spring, useVideoConfig, staticFile} from 'remotion';
import {Audio} from '@remotion/media';
import {theme} from './theme';

const FadeIn: React.FC<{children: React.ReactNode; delay?: number}> = ({children, delay = 0}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const opacity = spring({frame: frame - delay, fps, config: {damping: 20}});
  const y = interpolate(opacity, [0, 1], [20, 0]);
  return <div style={{opacity, transform: `translateY(${y}px)`}}>{children}</div>;
};

const TerminalLine: React.FC<{text: string; color?: string; delay: number; nextDelay?: number}> = ({text, color = theme.text, delay, nextDelay}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const progress = spring({frame: frame - delay, fps, config: {damping: 30}});
  const chars = Math.floor(progress * text.length);
  const done = progress > 0.99;
  const showCursor = nextDelay === undefined || frame < nextDelay;
  return (
    <div style={{color, fontSize: 18, fontFamily: 'monospace', lineHeight: 1.8, opacity: frame > delay ? 1 : 0}}>
      {done ? text : text.slice(0, chars)}
      {showCursor && done && <span style={{opacity: frame % 15 < 8 ? 1 : 0}}> █</span>}
      {!done && <span style={{opacity: frame % 15 < 8 ? 1 : 0}}> █</span>}
    </div>
  );
};

export const DemoVideo: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  return (
    <AbsoluteFill
      style={{
        background: theme.bg,
        fontFamily: 'system-ui, -apple-system, sans-serif',
      }}
    >
      {/* Background music – first 40s with fade-out over last 3s */}
      <Audio
        src={staticFile('soundtrack.mp3')}
        trimAfter={40 * fps}
        volume={(f) =>
          interpolate(f, [(40 - 3) * fps, 40 * fps], [1, 0], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          })
        }
      />

      {/* Intro: Title card */}
      <Sequence from={0} durationInFrames={90}>
        <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
          <FadeIn>
            <div style={{fontSize: 56, marginBottom: 8}}>⚡</div>
          </FadeIn>
          <FadeIn delay={15}>
            <div style={{fontSize: 52, fontWeight: 800, color: theme.text}}>BalaganAgent</div>
          </FadeIn>
          <FadeIn delay={30}>
            <div style={{fontSize: 22, color: theme.accent, marginTop: 12}}>Chaos Engineering for AI Agents</div>
          </FadeIn>
        </AbsoluteFill>
      </Sequence>

      {/* Install + run */}
      <Sequence from={90} durationInFrames={210}>
        <AbsoluteFill style={{padding: 60, display: 'flex', flexDirection: 'column', justifyContent: 'center'}}>
          <div style={{background: theme.codeBg, border: `1px solid ${theme.border}`, borderRadius: 12, padding: 36}}>
            <div style={{display: 'flex', gap: 8, marginBottom: 20}}>
              <div style={{width: 12, height: 12, borderRadius: 6, background: '#FF5F57'}} />
              <div style={{width: 12, height: 12, borderRadius: 6, background: '#FEBC2E'}} />
              <div style={{width: 12, height: 12, borderRadius: 6, background: '#28C840'}} />
            </div>
            <TerminalLine text="$ pip install balagan-agent" color={theme.textMuted} delay={0} nextDelay={40} />
            <TerminalLine text="Successfully installed balagan-agent-0.4.0" color={theme.green} delay={40} nextDelay={70} />
            <div style={{height: 16}} />
            <TerminalLine text="$ balaganagent demo --chaos-level 0.5" color={theme.textMuted} delay={70} nextDelay={100} />
            <div style={{height: 8}} />
            <TerminalLine text="⚡ Running chaos experiment..." color={theme.accent} delay={100} nextDelay={120} />
            <TerminalLine text="  Injecting: tool_failure ×4, latency ×3" color={theme.text} delay={120} nextDelay={135} />
            <TerminalLine text="  Injecting: hallucination ×2, budget ×1" color={theme.text} delay={135} nextDelay={160} />
            <div style={{height: 8}} />
            <TerminalLine text="✓ 8/10 runs passed (80% reliability)" color={theme.green} delay={160} nextDelay={175} />
            <TerminalLine text="✓ Mean Time to Recovery: 2.3s" color={theme.green} delay={175} nextDelay={190} />
            <TerminalLine text="✓ Report saved → report.html" color={theme.green} delay={190} />
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* Dashboard demo: show the generated HTML report */}
      <Sequence from={300} durationInFrames={180}>
        <AbsoluteFill style={{padding: 40, display: 'flex', flexDirection: 'column', justifyContent: 'center'}}>
          {/* Browser chrome */}
          <div style={{background: '#1A1E24', borderRadius: 12, border: `1px solid ${theme.border}`, overflow: 'hidden'}}>
            {/* Title bar */}
            <div style={{display: 'flex', alignItems: 'center', gap: 8, padding: '10px 16px', background: '#12161C', borderBottom: `1px solid ${theme.border}`}}>
              <div style={{width: 10, height: 10, borderRadius: 5, background: '#FF5F57'}} />
              <div style={{width: 10, height: 10, borderRadius: 5, background: '#FEBC2E'}} />
              <div style={{width: 10, height: 10, borderRadius: 5, background: '#28C840'}} />
              <div style={{flex: 1, textAlign: 'center', fontSize: 13, color: theme.textMuted, fontFamily: 'system-ui'}}>
                report.html
              </div>
            </div>

            {/* Dashboard content */}
            <div style={{padding: 28}}>
              {/* Header */}
              <FadeIn>
                <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24}}>
                  <div style={{fontSize: 22, fontWeight: 700, color: theme.text}}>
                    ⚡ BalaganAgent &mdash; Chaos Report
                  </div>
                  <div style={{fontSize: 13, color: theme.textMuted}}>stress_test_crew &middot; chaos_level=0.5</div>
                </div>
              </FadeIn>

              {/* Metric cards row */}
              <div style={{display: 'flex', gap: 16, marginBottom: 24}}>
                {[
                  {label: 'Reliability', value: '80%', color: theme.green},
                  {label: 'MTTR', value: '2.3s', color: theme.yellow},
                  {label: 'Runs', value: '10', color: theme.blue},
                  {label: 'Faults', value: '10', color: theme.accent},
                ].map((m, i) => {
                  const cardProgress = spring({frame: frame - 300 - i * 8, fps, config: {damping: 20}});
                  const cardY = interpolate(cardProgress, [0, 1], [30, 0]);
                  return (
                    <div key={m.label} style={{flex: 1, background: theme.bgCard, border: `1px solid ${theme.border}`, borderRadius: 10, padding: '18px 20px', opacity: cardProgress, transform: `translateY(${cardY}px)`}}>
                      <div style={{fontSize: 12, color: theme.textMuted, marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em'}}>{m.label}</div>
                      <div style={{fontSize: 28, fontWeight: 800, color: m.color}}>{m.value}</div>
                    </div>
                  );
                })}
              </div>

              {/* Charts row */}
              <div style={{display: 'flex', gap: 16}}>
                {/* Bar chart: reliability by chaos level */}
                <div style={{flex: 1.2, background: theme.bgCard, border: `1px solid ${theme.border}`, borderRadius: 10, padding: 20}}>
                  <div style={{fontSize: 13, color: theme.textMuted, marginBottom: 16, fontWeight: 600}}>Reliability by Chaos Level</div>
                  <div style={{display: 'flex', alignItems: 'flex-end', gap: 12, height: 120}}>
                    {[
                      {level: '0.1', pct: 100, color: theme.green},
                      {level: '0.3', pct: 93, color: theme.green},
                      {level: '0.5', pct: 80, color: theme.yellow},
                      {level: '0.7', pct: 62, color: theme.accent},
                      {level: '0.9', pct: 41, color: theme.accentAlt},
                    ].map((bar, i) => {
                      const barProgress = spring({frame: frame - 320 - i * 6, fps, config: {damping: 15}});
                      const barHeight = interpolate(barProgress, [0, 1], [0, (bar.pct / 100) * 120]);
                      return (
                        <div key={bar.level} style={{flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6}}>
                          <div style={{fontSize: 11, color: theme.text, fontWeight: 600, opacity: barProgress}}>{bar.pct}%</div>
                          <div style={{width: '100%', height: barHeight, background: `linear-gradient(180deg, ${bar.color}, ${bar.color}88)`, borderRadius: 4}} />
                          <div style={{fontSize: 10, color: theme.textMuted}}>{bar.level}</div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Donut chart: pass/fail */}
                <div style={{flex: 0.8, background: theme.bgCard, border: `1px solid ${theme.border}`, borderRadius: 10, padding: 20, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
                  <div style={{fontSize: 13, color: theme.textMuted, marginBottom: 16, fontWeight: 600, alignSelf: 'flex-start'}}>Pass / Fail</div>
                  {(() => {
                    const ringProgress = spring({frame: frame - 330, fps, config: {damping: 20}});
                    const passAngle = interpolate(ringProgress, [0, 1], [0, 288]); // 80% of 360
                    const r = 44;
                    const cx = 60;
                    const cy = 60;
                    const stroke = 14;
                    // Build pass arc
                    const endRad = (passAngle - 90) * (Math.PI / 180);
                    const startRad = -90 * (Math.PI / 180);
                    const x1 = cx + r * Math.cos(startRad);
                    const y1 = cy + r * Math.sin(startRad);
                    const x2 = cx + r * Math.cos(endRad);
                    const y2 = cy + r * Math.sin(endRad);
                    const largeArc = passAngle > 180 ? 1 : 0;
                    return (
                      <div style={{position: 'relative', width: 120, height: 120}}>
                        <svg width={120} height={120} viewBox="0 0 120 120">
                          <circle cx={cx} cy={cy} r={r} fill="none" stroke={theme.accentAlt + '44'} strokeWidth={stroke} />
                          {passAngle > 0 && (
                            <path
                              d={`M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`}
                              fill="none"
                              stroke={theme.green}
                              strokeWidth={stroke}
                              strokeLinecap="round"
                            />
                          )}
                        </svg>
                        <div style={{position: 'absolute', top: 0, left: 0, width: 120, height: 120, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column'}}>
                          <div style={{fontSize: 22, fontWeight: 800, color: theme.text, opacity: ringProgress}}>80%</div>
                          <div style={{fontSize: 10, color: theme.textMuted, opacity: ringProgress}}>passed</div>
                        </div>
                      </div>
                    );
                  })()}
                  <div style={{display: 'flex', gap: 16, marginTop: 8}}>
                    <div style={{display: 'flex', alignItems: 'center', gap: 4}}>
                      <div style={{width: 8, height: 8, borderRadius: 4, background: theme.green}} />
                      <span style={{fontSize: 11, color: theme.textMuted}}>Pass (8)</span>
                    </div>
                    <div style={{display: 'flex', alignItems: 'center', gap: 4}}>
                      <div style={{width: 8, height: 8, borderRadius: 4, background: theme.accentAlt}} />
                      <span style={{fontSize: 11, color: theme.textMuted}}>Fail (2)</span>
                    </div>
                  </div>
                </div>

                {/* Fault breakdown */}
                <div style={{flex: 0.8, background: theme.bgCard, border: `1px solid ${theme.border}`, borderRadius: 10, padding: 20}}>
                  <div style={{fontSize: 13, color: theme.textMuted, marginBottom: 16, fontWeight: 600}}>Faults Injected</div>
                  {[
                    {name: 'tool_failure', count: 4, color: theme.accent},
                    {name: 'latency', count: 3, color: theme.yellow},
                    {name: 'hallucination', count: 2, color: theme.purple},
                    {name: 'budget', count: 1, color: theme.accentAlt},
                  ].map((fault, i) => {
                    const faultProgress = spring({frame: frame - 335 - i * 6, fps, config: {damping: 20}});
                    const barW = interpolate(faultProgress, [0, 1], [0, (fault.count / 4) * 100]);
                    return (
                      <div key={fault.name} style={{marginBottom: 10}}>
                        <div style={{display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4}}>
                          <span style={{color: fault.color}}>{fault.name}</span>
                          <span style={{color: theme.textMuted, opacity: faultProgress}}>×{fault.count}</span>
                        </div>
                        <div style={{height: 6, background: theme.codeBg, borderRadius: 3, overflow: 'hidden'}}>
                          <div style={{width: `${barW}%`, height: '100%', background: fault.color, borderRadius: 3}} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* Results card */}
      <Sequence from={480} durationInFrames={120}>
        <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 24}}>
          <FadeIn>
            <div style={{fontSize: 48, fontWeight: 800, color: theme.text, textAlign: 'center'}}>
              Know your agent breaks<br />
              <span style={{color: theme.accent}}>before your users do.</span>
            </div>
          </FadeIn>
          <FadeIn delay={30}>
            <div style={{display: 'flex', gap: 16, marginTop: 16}}>
              <div style={{background: theme.accent, color: '#fff', padding: '12px 28px', borderRadius: 8, fontSize: 18, fontWeight: 700}}>
                pip install balagan-agent
              </div>
            </div>
          </FadeIn>
          <FadeIn delay={45}>
            <div style={{fontSize: 16, color: theme.textMuted, marginTop: 8}}>
              Open Source &middot; Apache 2.0 &middot; github.com/arielshad/agent-chaos
            </div>
          </FadeIn>
        </AbsoluteFill>
      </Sequence>
    </AbsoluteFill>
  );
};
