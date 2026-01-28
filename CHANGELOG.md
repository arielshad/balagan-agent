# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive documentation for open-source release
- Security policy (SECURITY.md) with vulnerability reporting process
- Development setup guide (DEVELOPMENT.md) for contributors
- CI/CD workflows for automated testing and quality checks
- Funding configuration for project sustainability

## [0.1.1] - 2024-01-28

### Changed
- Updated project name to `balagan-agent` for better PyPI compatibility
- Improved package metadata and descriptions

### Fixed
- Package naming issues for PyPI distribution
- Project configuration cleanup

## [0.1.0] - 2024-01-15

### Added
- Initial release of BalaganAgent
- Core chaos engine with configurable chaos levels
- Agent wrapper for tool interception and fault injection
- Fault injectors:
  - Tool Failure Injector (exceptions, timeouts, rate limits, service errors)
  - Delay Injector (fixed, random, spike, degrading latency patterns)
  - Hallucination Injector (wrong values, fabricated data, contradictions)
  - Context Corruption Injector (truncation, reordering, noise, encoding issues)
  - Budget Exhaustion Injector (token limits, cost caps, rate limiting)
- Metrics collection and analysis:
  - MTTR (Mean Time To Recovery) calculator
  - Recovery quality metrics
  - Reliability scoring with SRE-grade grades
  - Error budget tracking
- Framework wrappers:
  - CrewAI integration
  - AutoGen integration
  - LangChain integration
- Experiment runner with scenario support
- Multiple report formats (terminal, JSON, markdown, HTML)
- CLI tool (`balaganagent` command)
  - Demo mode
  - Project initialization
  - Scenario execution
  - Stress testing capabilities
- Comprehensive test suite:
  - Unit tests
  - Integration tests
  - BDD tests (Gherkin scenarios)
  - End-to-end tests
- Documentation:
  - README with quick start guide
  - CrewAI integration guide
  - API documentation
  - Usage examples

### Developer Experience
- Type hints throughout codebase
- Code quality tools (black, ruff, mypy)
- pytest-based test infrastructure
- AsyncIO support for concurrent operations

## Guiding Principles

BalaganAgent follows these versioning guidelines:

- **Major version (X.0.0)**: Breaking API changes
- **Minor version (0.X.0)**: New features, backward compatible
- **Patch version (0.0.X)**: Bug fixes, backward compatible

## Categories

- **Added**: New features
- **Changed**: Changes to existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Vulnerability fixes (marked with `[SECURITY]` tag)

[unreleased]: https://github.com/arielshad/balagan-agent/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/arielshad/balagan-agent/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/arielshad/balagan-agent/releases/tag/v0.1.0
