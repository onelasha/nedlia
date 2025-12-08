# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security seriously at Nedlia. If you discover a security vulnerability, please report it responsibly.

### How to Report

1. **Do NOT** open a public GitHub issue for security vulnerabilities.

2. Email us at: **security@nedlia.io** (or your preferred contact)

3. Include the following information:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Any suggested fixes (optional)

### What to Expect

- **Acknowledgment**: We will acknowledge receipt within 48 hours.
- **Assessment**: We will assess the vulnerability and determine its severity within 7 days.
- **Resolution**: We aim to resolve critical vulnerabilities within 30 days.
- **Disclosure**: We will coordinate with you on public disclosure timing.

### Scope

The following are in scope:

- Nedlia backend services
- Nedlia frontend applications
- Nedlia SDKs
- Nedlia plugins
- Infrastructure configurations

### Out of Scope

- Social engineering attacks
- Physical attacks
- Denial of service attacks
- Issues in third-party dependencies (report to the respective maintainers)

## Security Best Practices

When contributing to Nedlia:

1. **Never commit secrets** – Use environment variables and secret managers.
2. **Validate all inputs** – Sanitize user inputs to prevent injection attacks.
3. **Use parameterized queries** – Prevent SQL injection.
4. **Keep dependencies updated** – Regularly update to patch known vulnerabilities.
5. **Follow least privilege** – Request only necessary permissions.
6. **Enable MFA** – Use multi-factor authentication for all accounts.

## Security Tools

We use the following tools to maintain security:

- **Gitleaks** – Detect secrets in code
- **Dependabot** – Automated dependency updates
- **CodeQL** – Static analysis (planned)
- **AWS Security Hub** – Cloud security posture (planned)

## Acknowledgments

We appreciate security researchers who help keep Nedlia secure. Contributors who report valid vulnerabilities will be acknowledged (with permission) in our security hall of fame.
