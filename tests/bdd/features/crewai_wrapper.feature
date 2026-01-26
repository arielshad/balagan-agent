Feature: CrewAI Chaos Engineering Wrapper
  As a developer testing AI agent reliability
  I want to inject chaos into CrewAI crews
  So that I can verify agent resilience under failure conditions

  Background:
    Given a mock CrewAI environment

  Scenario: Wrap a simple CrewAI crew
    Given a CrewAI crew with 1 agent and 1 tool
    When I create a wrapper for the crew
    Then the wrapper should contain the crew
    And the tool should be wrapped for chaos injection

  Scenario: Configure chaos level
    Given a CrewAI crew with 1 agent and 1 tool
    And a wrapper for the crew
    When I configure chaos level to 0.5
    Then the chaos level should be 0.5
    And tool failures should be enabled
    And delays should be enabled

  Scenario: Execute crew with no chaos
    Given a CrewAI crew with 1 agent and 1 tool
    And a wrapper with chaos level 0.0
    When I execute the crew
    Then the execution should succeed
    And the kickoff count should be 1

  Scenario: Track metrics during execution
    Given a CrewAI crew with 1 agent and 1 tool
    And a wrapper with chaos level 0.0
    When I execute the crew 3 times
    Then the kickoff count should be 3

  Scenario: Run experiment with tracking
    Given a CrewAI crew with 1 agent and 1 tool
    And a wrapper with chaos level 0.0
    When I run an experiment named "reliability-test"
    And execute the crew within the experiment
    Then the experiment results should contain "reliability-test"

  Scenario: Reset wrapper state
    Given a CrewAI crew with 1 agent and 1 tool
    And a wrapper with chaos level 0.0
    When I execute the crew
    And reset the wrapper
    Then the kickoff count should be 0

  Scenario: Multiple agents with different tools
    Given a CrewAI crew with 2 agents each having different tools
    When I create a wrapper for the crew
    Then all tools from all agents should be wrapped
    And the wrapper should have 2 wrapped tools

  Scenario: Add custom injector to specific tools
    Given a CrewAI crew with 2 agents each having different tools
    And a wrapper for the crew
    When I add a failure injector to the "search" tool only
    Then only the "search" tool should have the injector

  Scenario: Tool proxy retries on failure
    Given a tool that fails twice then succeeds
    And a CrewAI tool proxy with max_retries 3
    When I call the tool proxy
    Then the result should be "success"
    And the tool should have been called 3 times
