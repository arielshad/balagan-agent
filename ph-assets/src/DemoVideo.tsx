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
      {/* Background music – first 30s with fade-out over last 3s */}
      <Audio
        src={staticFile('soundtrack.mp3')}
        trimAfter={30 * fps}
        volume={(f) =>
          interpolate(f, [(30 - 3) * fps, 30 * fps], [1, 0], {
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

      {/* Results card */}
      <Sequence from={300} durationInFrames={150}>
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
