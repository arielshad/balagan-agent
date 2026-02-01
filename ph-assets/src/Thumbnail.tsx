import React from 'react';
import {AbsoluteFill} from 'remotion';
import {theme} from './theme';

export const Thumbnail: React.FC = () => {
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at 30% 40%, ${theme.accent}22, transparent 60%), ${theme.bg}`,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif',
      }}
    >
      {/* Lightning bolt icon */}
      <div style={{fontSize: 72, marginBottom: 8}}>⚡</div>
      <div
        style={{
          fontSize: 28,
          fontWeight: 800,
          color: theme.text,
          letterSpacing: '-0.02em',
        }}
      >
        BalaganAgent
      </div>
      <div
        style={{
          fontSize: 13,
          fontWeight: 600,
          color: theme.accent,
          marginTop: 6,
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
        }}
      >
        Chaos Engineering
      </div>
      <div
        style={{
          fontSize: 13,
          fontWeight: 600,
          color: theme.accent,
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
        }}
      >
        for AI Agents
      </div>
    </AbsoluteFill>
  );
};
