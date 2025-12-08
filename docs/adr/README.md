# Architecture Decision Records (ADR)

This directory contains Architecture Decision Records for the Nedlia project.

## What is an ADR?

An ADR is a document that captures an important architectural decision made along with its context and consequences.

## ADR Template

When creating a new ADR, use this template:

```markdown
# ADR-XXXX: Title

## Status

Proposed | Accepted | Deprecated | Superseded

## Context

What is the issue that we're seeing that is motivating this decision or change?

## Decision

What is the change that we're proposing and/or doing?

## Consequences

What becomes easier or more difficult to do because of this change?
```

## Index

| ADR                                   | Title                                   | Status   | Date    |
| ------------------------------------- | --------------------------------------- | -------- | ------- |
| [001](001-clean-architecture.md)      | Clean Architecture                      | Accepted | 2024-12 |
| [002](002-aws-serverless.md)          | AWS Serverless Stack                    | Accepted | 2024-12 |
| [003](003-event-driven.md)            | Event-Driven Architecture               | Accepted | 2024-12 |
| [004](004-terraform-terragrunt.md)    | Terraform + Terragrunt for IaC          | Accepted | 2024-12 |
| [005](005-trunk-based-development.md) | Trunk-Based Development + Feature Flags | Accepted | 2024-12 |
| [006](006-cap-theorem-tradeoffs.md)   | CAP Theorem Trade-offs                  | Accepted | 2024-12 |
| [007](007-fargate-microservices.md)   | Fargate for Domain Microservices        | Accepted | 2024-12 |

## Creating a New ADR

1. Copy the template above
2. Create a new file: `docs/adr/XXX-title.md`
3. Fill in the sections
4. Add to the index above
5. Submit a PR for review
