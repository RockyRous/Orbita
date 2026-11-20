# Orbita

Orbita is a Windows-first desktop client for Codex. Its product direction is a functional Codex chat beside a source-driven tracker of observable agent work and related workflow context.

> Status: documentation and architecture reset in progress. The previous fixture-backed observer was deleted; there is not yet a runnable product application.

## Product direction

- Conduct supported Codex work in a desktop chat instead of returning to the terminal.
- Show real observable agent executions, their evidence-backed status, and direct relationships when available.
- Show plans, roles, and GitHub work items as explicit workflow context—not as invented agents or task rows.
- Use the public Codex App Server through a versioned adapter; never infer completion or hidden hierarchy.

## Canonical documents

- [Product vision](docs/product/vision.md), [MVP scope](docs/product/mvp.md), and [roadmap](docs/product/roadmap.md)
- [Core flows](docs/ux/core-flows.md) and [state model](docs/ux/state-model.md)
- [Architecture](docs/architecture/overview.md) and [Tauri decision](docs/adr/0003-tauri-desktop-client.md)
- [Desktop implementation plan](docs/planning/desktop-mvp-plan.md)
- [Compatibility](docs/protocol/compatibility.md), [spike plan](docs/protocol/spike-plan.md), [security model](docs/security/threat-model.md), and [data policy](docs/security/diagnostics-and-data.md)

## Contributing

Use GitHub Issues for substantial changes and read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). The source code of Happier, bb, and CodexUI is not an Orbita dependency or implementation base.

## Security and license

Report vulnerabilities privately through [SECURITY.md](SECURITY.md). Orbita is licensed under [MIT](LICENSE).
