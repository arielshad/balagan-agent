Feature: AutoGen Chaos Engineering Wrapper
  As a developer testing AI agent reliability
  I want to inject chaos into AutoGen agents
  So that I can verify agent resilience under failure conditions

  Background:
    Given a mock AutoGen environment

  Scenario: Wrap a simple AutoGen agent
    Given an AutoGen agent with function_map containing 2 functions
    When I create a wrapper for the agent
    Then the wrapper should contain the agent
    And the functions should be wrapped for chaos injection

  Scenario: Configure chaos level for AutoGen agent
    Given an AutoGen agent with function_map containing 1 function
    And a wrapper for the agent
    When I configure chaos level to 0.75
    Then the chaos level should be 0.75
    And function failures should be enabled
    And delays should be enabled

  Scenario: Generate reply through wrapper
    Given an AutoGen agent with function_map containing 1 function
    And a wrapper with chaos level 0.0
    When I generate a reply with a user message
    Then the reply should be generated
    And the reply count should be 1

  Scenario: Initiate chat with user proxy
    Given an AutoGen agent with function_map containing 1 function
    And a user proxy agent
    And a wrapper with both agents and chaos level 0.0
    When I initiate a chat with message "Hello"
    Then the chat should be initiated successfully

  Scenario: Track metrics during conversation
    Given an AutoGen agent with function_map containing 1 function
    And a wrapper with chaos level 0.0
    When I generate 5 replies
    Then the reply count should be 5

  Scenario: Run experiment with AutoGen agent
    Given an AutoGen agent with function_map containing 1 function
    And a wrapper with chaos level 0.0
    When I run an experiment named "autogen-reliability-test"
    And generate replies within the experiment
    Then the experiment results should contain "autogen-reliability-test"

  Scenario: Reset AutoGen wrapper state
    Given an AutoGen agent with function_map containing 1 function
    And a wrapper with chaos level 0.0
    When I generate a reply with a user message
    And reset the wrapper
    Then the reply count should be 0

  Scenario: Multi-agent wrapper creation
    Given 3 AutoGen agents each with different functions
    When I create a multi-agent wrapper
    Then all agents should be wrapped
    And the multi-agent wrapper should have 3 agents

  Scenario: Multi-agent chaos propagation
    Given 3 AutoGen agents each with different functions
    And a multi-agent wrapper
    When I configure multi-agent chaos level to 0.6
    Then all agent wrappers should have chaos level 0.6

  Scenario: Aggregate metrics from multi-agent setup
    Given 3 AutoGen agents each with different functions
    And a multi-agent wrapper with chaos level 0.0
    When each agent generates 2 replies
    Then the total replies should be 6

  Scenario: Function proxy retries on transient failure
    Given a function that fails twice then succeeds
    And an AutoGen function proxy with max_retries 3
    When I call the function proxy
    Then the result should be "success"
    And the function should have been called 3 times

  Scenario: Missing user proxy raises error
    Given an AutoGen agent with function_map containing 1 function
    And a wrapper without user proxy
    When I try to initiate chat
    Then a ValueError should be raised with message "user_proxy is required"
