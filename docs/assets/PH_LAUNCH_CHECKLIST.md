# Product Hunt Launch Checklist — BalaganAgent

## Product Hunt Listing

- [ ] **URL**: `https://arielshad.github.io/balagan-agent/`
- [ ] **Tagline** (60 chars max): "Chaos engineering for AI agents"
- [ ] **One-liner**: "BalaganAgent injects failures into tool calls, latency, context, and budgets — then scores recovery (MTTR, reliability) and generates reports."
- [ ] **Topics**: Developer Tools, Artificial Intelligence, Open Source, Testing

## Assets to Create

### Thumbnail (square, 240x240)
- Logo + text "Chaos Engineering for AI Agents"

### Gallery Images (1270x760, 4–6 images)
1. **Problem** — "Agents fail silently: tool timeouts, corrupted context, budget exhaustion"
2. **Solution** — "Inject faults in dev → measure MTTR & reliability → fix before production"
3. **How it works** — Architecture diagram: Injectors → Metrics → Reports
4. **Example report** — Screenshot of HTML report dashboard
5. **3-line integration** — CrewAI wrapper code snippet
6. **Stress test results** — CLI output showing pass rates at different chaos levels

### Demo Video (optional, <60s)
- Install → `balaganagent demo --chaos-level 0.5` → show report output
- Or: 3-line CrewAI integration → run → show metrics

## Maker Comment (post immediately on launch)

```
Hey PH! I'm Ariel, the creator of BalaganAgent.

I built this because I kept seeing AI agents demo perfectly but break in production — tool calls timeout, APIs return garbage, context gets corrupted, and nobody knows until users complain.

BalaganAgent brings chaos engineering (think Chaos Monkey, but for agents) to the AI world:

• 5 fault injectors: tool failures, delays, hallucinations, context corruption, budget exhaustion
• Metrics: MTTR + SRE-grade reliability scoring
• Reports: terminal, JSON, Markdown, HTML
• Works with CrewAI, AutoGen, LangChain, Claude Agent SDK

It's free, open source (Apache 2.0), and you can try it right now:

    pip install balagan-agent
    balaganagent demo --chaos-level 0.5

Would love your feedback — what failure modes matter most to you?
```

## FAQ (for PH comments)

**Q: Is this for production chaos testing?**
A: No — it's for dev/CI. You inject failures during development to find agent weaknesses before they reach production.

**Q: Does it cost money?**
A: BalaganAgent is free and open source. Your LLM API costs still apply during experiments.

**Q: Which frameworks does it support?**
A: CrewAI, AutoGen, LangChain, Claude Agent SDK, plus any custom Python agent.

**Q: How is this different from Chaos Monkey/Gremlin?**
A: Those are infrastructure-focused. BalaganAgent understands AI agents — it injects semantic failures (hallucinations, context corruption) and measures agent-specific metrics (MTTR, recovery quality).

## Launch Timeline

### T-7 to T-3
- [ ] Ship GitHub Pages site (push to main triggers deploy)
- [ ] Enable GitHub Pages in repo Settings → Pages → Source: GitHub Actions
- [ ] Record 45-60s demo video
- [ ] Create PH listing draft with assets
- [ ] Create 3 "good first issues" on GitHub

### T-2 to T-1
- [ ] Schedule PH post
- [ ] Prepare maker comment (above)
- [ ] Line up 10-20 people for genuine feedback

### Launch Day
- [ ] Post early (PH day is Pacific time)
- [ ] Pin maker comment immediately
- [ ] Respond to every comment for first 2-3 hours
- [ ] Check in hourly after that

### T+1 to T+7
- [ ] Turn best comments into FAQ updates
- [ ] Write 1-2 follow-up posts (blog, social)
- [ ] Update docs based on feedback

## GitHub Pages Setup (one-time)

1. Go to repo Settings → Pages
2. Under "Build and deployment", select **Source: GitHub Actions**
3. Push to `main` — the workflow at `.github/workflows/pages.yml` handles the rest
4. Site will be live at `https://arielshad.github.io/balagan-agent/`
