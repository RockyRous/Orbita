# Orbita

**Orbita** is a local-first Windows desktop workspace for working with Codex through its App Server. It brings projects and chats into a visual interface and makes the activity of Codex and its subagents observable.

> Status: specification and implementation planning. The source code has not been started yet.

## Product direction

- Start and manage a local Codex App Server for a chosen project.
- Work in persistent chats and projects instead of a terminal-only workflow.
- Stream responses, tool activity, approvals, diagnostics, and Git changes.
- Show the available lifecycle, tasks, and relationships of subagents without inventing orchestration that Codex does not expose.
- Keep user data local and preserve the semantics of Codex rather than replacing its runtime.

The initial platform is Windows 11; Windows 10 and WSL are follow-up compatibility targets.

## Project status

The complete product specification is in [PROJECT_DOC.md](PROJECT_DOC.md). It defines the MVP, technical spike for multi-agent observability, architecture boundaries, milestones, and initial backlog.

## Contributing

Contributions are welcome once implementation begins. Please read [CONTRIBUTING.md](CONTRIBUTING.md), follow the [Code of Conduct](CODE_OF_CONDUCT.md), and use GitHub Issues to discuss substantial changes before opening a pull request.

## Security

Please report vulnerabilities privately according to [SECURITY.md](SECURITY.md), rather than opening a public issue.

## License

Orbita is licensed under the [MIT License](LICENSE).
