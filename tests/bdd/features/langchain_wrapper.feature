Feature: LangChain Chaos Engineering Wrapper
  As a developer testing AI agent reliability
  I want to inject chaos into LangChain agents
  So that I can verify agent resilience under failure conditions

  Background:
    Given a mock LangChain environment

  Scenario: Wrap a simple LangChain agent
    Given a LangChain agent with 2 tools
    When I create a wrapper for the agent
    Then the wrapper should contain the agent executor
    And the tools should be wrapped for chaos injection

  Scenario: Configure chaos level
    Given a LangChain agent with 1 tools
    And a wrapper for the agent
    When I configure chaos level to 0.5
    Then the chaos level should be 0.5
    And tool failures should be enabled
    And delays should be enabled

  Scenario: Invoke agent with no chaos
    Given a LangChain agent with 1 tools
    And a wrapper with chaos level 0.0
    When I invoke the agent with input "Hello"
    Then the invocation should succeed
    And the invoke count should be 1

  Scenario: Track metrics during execution
    Given a LangChain agent with 1 tools
    And a wrapper with chaos level 0.0
    When I invoke the agent 3 times
    Then the invoke count should be 3

  Scenario: Run experiment with tracking
    Given a LangChain agent with 1 tools
    And a wrapper with chaos level 0.0
    When I run an experiment named "langchain-reliability-test"
    And invoke the agent within the experiment
    Then the experiment results should contain "langchain-reliability-test"

  Scenario: Reset wrapper state
    Given a LangChain agent with 1 tools
    And a wrapper with chaos level 0.0
    When I invoke the agent with input "test"
    And reset the wrapper
    Then the invoke count should be 0

  Scenario: Multiple tools wrapped
    Given a LangChain agent with 3 tools
    When I create a wrapper for the agent
    Then all tools should be wrapped
    And the wrapper should have 3 wrapped tools

  Scenario: Add custom injector to specific tools
    Given a LangChain agent with 2 tools
    And a wrapper for the agent
    When I add a failure injector to the "search" tool only
    Then only the "search" tool should have the injector

  Scenario: Tool proxy retries on failure
    Given a tool that fails twice then succeeds
    And a LangChain tool proxy with max_retries 3
    When I call the tool proxy
    Then the result should be "success"
    And the tool should have been called 3 times

  Scenario: Stream responses
    Given a LangChain agent with 1 tools
    And a wrapper with chaos level 0.0
    When I stream from the agent with input "test"
    Then I should receive multiple chunks

  Scenario: Batch invocation
    Given a LangChain agent with 1 tools
    And a wrapper with chaos level 0.0
    When I batch invoke with 3 inputs
    Then I should receive 3 results
    And the invoke count should be 3

  Scenario: Chain wrapper invocation
    Given a LangChain chain
    And a chain wrapper with chaos level 0.0
    When I invoke the chain with input "test"
    Then the chain invocation should succeed
