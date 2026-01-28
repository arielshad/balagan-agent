# Security Policy

## Supported Versions

We release patches for security vulnerabilities in the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take the security of BalaganAgent seriously. If you discover a security vulnerability, please follow these steps:

### Private Disclosure Process

**DO NOT** create a public GitHub issue for security vulnerabilities.

Instead, please report security vulnerabilities by:

1. **Email**: Send details to ariel.shadkhan@gmail.com with the subject line "SECURITY: [Brief Description]"
2. **GitHub Security Advisory**: Use the [private vulnerability reporting feature](https://github.com/arielshad/balagan-agent/security/advisories/new)

### What to Include

Please provide as much information as possible:

- Type of vulnerability (e.g., code injection, privilege escalation, data exposure)
- Full path to the source file(s) related to the vulnerability
- Location of the affected source code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the vulnerability, including how an attacker might exploit it

### Response Timeline

- **24-48 hours**: Initial acknowledgment of your report
- **7 days**: Detailed response including assessment and remediation timeline
- **30-90 days**: Fix development, testing, and coordinated disclosure

We aim to release security patches as quickly as possible, depending on complexity.

### Disclosure Policy

- We will coordinate disclosure timing with you
- We request that you do not publicly disclose the vulnerability until we've released a fix
- Once a fix is released, we will publicly acknowledge your responsible disclosure (unless you prefer to remain anonymous)

### Security Updates

Security updates will be:

1. Released through normal package channels (PyPI)
2. Documented in the [CHANGELOG.md](CHANGELOG.md) with a `[SECURITY]` tag
3. Announced via GitHub Security Advisories
4. Posted to GitHub Releases with severity level

## Security Best Practices

When using BalaganAgent in production:

1. **API Keys**: Never commit API keys or credentials to version control
2. **Dependency Updates**: Regularly update dependencies to get security patches
3. **Test in Isolation**: Run chaos tests in isolated environments, not production
4. **Rate Limiting**: Apply appropriate rate limits when testing external APIs
5. **Audit Logs**: Enable logging to track chaos experiment execution
6. **Access Control**: Restrict who can run chaos experiments in your organization

## Known Security Considerations

### Chaos Injection Risks

BalaganAgent is designed to inject failures. Please be aware:

- **Production Use**: Never run chaos experiments directly in production without proper safeguards
- **API Abuse**: Tool failure injection could trigger rate limits or abuse detection on external APIs
- **Data Corruption**: Context corruption could potentially lead to unexpected agent behavior
- **Cost Implications**: Budget exhaustion testing may incur costs with LLM providers

### Safe Testing Practices

1. **Isolated Environments**: Always test in development/staging environments first
2. **Gradual Rollout**: Start with low chaos levels (0.1-0.25) and increase gradually
3. **Monitoring**: Monitor your agents and external services during chaos testing
4. **Circuit Breakers**: Implement circuit breakers to stop experiments if issues arise
5. **Backup Plans**: Have rollback procedures ready

## Security Vulnerability History

All security vulnerabilities will be documented in [CHANGELOG.md](CHANGELOG.md) with the `[SECURITY]` tag.

Currently, no security vulnerabilities have been reported or fixed.

## Questions?

For general security questions or concerns, feel free to open a public discussion in [GitHub Discussions](https://github.com/arielshad/balagan-agent/discussions) or reach out via email.

Thank you for helping keep BalaganAgent and its users safe!
