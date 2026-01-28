# CrewAI Gemini Research Agent - Architecture Diagrams

This document provides visual diagrams of the CrewAI Gemini Research Agent architecture and flow.

## System Architecture

```mermaid
graph TD
    Start([Start: Topic Input]) --> Config[Configure Gemini LLM<br/>gemini-3-flash-preview]

    Config --> CreateCrew[Build Research Crew]

    CreateCrew --> Researcher[Agent: Senior Research Analyst<br/>Role: Find comprehensive information]
    CreateCrew --> Writer[Agent: Technical Writer<br/>Role: Write clear research report]

    Researcher --> RT[Task 1: Research Task<br/>Research the topic]
    Writer --> WRT[Task 2: Report Task<br/>Write polished report]

    RT -.context.-> WRT

    subgraph "Researcher Tools"
        T1[search_web<br/>Search for information]
        T2[summarize_text<br/>Condense findings]
    end

    subgraph "Writer Tools"
        T3[summarize_text<br/>Tighten prose]
        T4[save_report<br/>Persist final report]
    end

    Researcher --> T1
    Researcher --> T2
    Writer --> T3
    Writer --> T4

    RT --> Process{Process: Sequential}
    Process --> WRT

    WRT --> Output([Final Report Output])

    style Researcher fill:#e1f5ff
    style Writer fill:#fff4e1
    style RT fill:#e8f5e9
    style WRT fill:#fff9c4
    style Process fill:#f3e5f5
```

## Execution Sequence

```mermaid
sequenceDiagram
    participant User
    participant Crew
    participant Researcher as Researcher Agent
    participant ST1 as search_web tool
    participant ST2 as summarize_text tool
    participant Writer as Writer Agent
    participant ST3 as save_report tool

    User->>Crew: kickoff(topic)
    Crew->>Researcher: Execute Research Task
    Researcher->>ST1: search_web(topic)
    ST1-->>Researcher: Search results
    Researcher->>ST2: summarize_text(results)
    ST2-->>Researcher: Summarized findings
    Researcher-->>Crew: Research summary

    Crew->>Writer: Execute Report Task (with context)
    Writer->>ST2: summarize_text(report draft)
    ST2-->>Writer: Polished text
    Writer->>ST3: save_report(final content)
    ST3-->>Writer: Confirmation
    Writer-->>Crew: Final report

    Crew-->>User: CrewOutput with report
```

## Component Overview

```mermaid
flowchart LR
    subgraph Environment
        ENV[.env file<br/>GOOGLE_API_KEY or<br/>GEMINI_TOKEN]
    end

    subgraph LLM Configuration
        ENV --> GetLLM[get_gemini_llm]
        GetLLM --> Model[gemini/gemini-3-flash-preview]
    end

    subgraph Crew Architecture
        Model --> R[Researcher Agent]
        Model --> W[Writer Agent]

        R --> Task1[Research Task]
        W --> Task2[Report Task]

        Task1 -.provides context.-> Task2
    end

    subgraph Tools
        Tool1[search_web<br/>Deterministic mock]
        Tool2[summarize_text<br/>Extract first 3 sentences]
        Tool3[save_report<br/>Word count confirmation]
    end

    R --> Tool1
    R --> Tool2
    W --> Tool2
    W --> Tool3

    Task2 --> Output[Final Research Report]

    style R fill:#4fc3f7
    style W fill:#ffb74d
    style Model fill:#9c27b0,color:#fff
```

## Key Components

### Agents
- **Senior Research Analyst**: Finds comprehensive information on the given topic
- **Technical Writer**: Writes clear, concise research reports

### Tasks
1. **Research Task**: Search and summarize information on the topic
2. **Report Task**: Write a polished report based on research (with context from Task 1)

### Tools
- **search_web**: Returns simulated search results (deterministic)
- **summarize_text**: Extracts first 3 sentences from text
- **save_report**: Returns word count confirmation

### Process Flow
- Sequential execution: Researcher → Writer
- Task context passing: Research findings are provided to the Writer
- Deterministic tools enable reliable testing and stress testing with AgentChaos
