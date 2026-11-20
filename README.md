# Orbita

**Orbita** is a local-first visual control plane for Codex on Windows. Its first implementation is a source-driven root-task observer: activity, outcomes, follow-up, interrupt, provenance, and explicit gaps for one local root task.

> Status: M1 root-task observer interface is in implementation. Hierarchy, approvals, and recovery remain evidence-gated.

## Product direction

- Start a root task through the public Codex App Server integration surface.
- Make observable agent work understandable without reconstructing it from a full transcript.
- Show only source-backed agent executions, relationships, statuses, outcomes, and attention.
- Handle supported approvals, interruption, and root-task follow-up without adding a custom orchestrator.
- Recover a coherent local task workspace after restart and show missing evidence as gaps.

The initial platform is Windows 11. The product is currently gated on an App Server protocol spike; no runtime version is supported yet.

## Project status

The repository is in specification and protocol-validation planning. Production implementation starts only after the M0 go/no-go gate.

Canonical documentation:

- [Product vision](docs/product/vision.md)
- [Bounded MVP](docs/product/mvp.md)
- [Gated roadmap](docs/product/roadmap.md)
- [Core flows](docs/ux/core-flows.md) and [state model](docs/ux/state-model.md)
- [Architecture boundary](docs/architecture/overview.md)
- [Compatibility status](docs/protocol/compatibility.md) and [M0 spike plan](docs/protocol/spike-plan.md)
- [Threat model](docs/security/threat-model.md) and [data policy](docs/security/diagnostics-and-data.md)
- [Draft M0 ticket breakdown](docs/planning/m0-tickets.md)

## Run the observer preview

The current UI is a native Windows fixture-backed preview; it does not start Codex work.
On Windows, run:

```powershell
.\scripts\start-observer.ps1
```

It opens the native desktop app. Close its window to stop it. To use the old
loopback browser preview explicitly, run `./scripts/start-observer.ps1 -BrowserPreview`.

## Contributing

Contributions are welcome once implementation begins. Please read [CONTRIBUTING.md](CONTRIBUTING.md), follow the [Code of Conduct](CODE_OF_CONDUCT.md), and use GitHub Issues to discuss substantial changes before opening a pull request. The draft M0 tickets have not been published yet.

## Security

Please report vulnerabilities privately according to [SECURITY.md](SECURITY.md), rather than opening a public issue.

## License

Orbita is licensed under the [MIT License](LICENSE).
