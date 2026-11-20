# Codex App Server compatibility profile: 0.171.0

This profile is a Windows x64, direct-child, `stdio://` qualification. It does not qualify another platform, digest, feature profile, transport, daemon/proxy lifecycle, recovery, hierarchy, or approvals.

## Identity

| Field | Value |
| --- | --- |
| CLI version | `codex-cli 0.171.0` |
| Native executable SHA-256 | `cefea4ffee1fff04983a99c0dda99944d8b380e891e740a28b32f4b815a6e0b7` |
| Transport | `stdio://` |
| Experimental API | `false` |
| Stable schema manifest | `a5eefea3ec775653f8625f67555638a1ae02b29ec8015b845a3e4a82d7badcaa` |
| Stable schema count | 331 |
| Feature/effective configuration digest | `7cd2d3085f377426f0084b242f528d2f54a2509ef5e02d4c18e8166f378e066d` |

## Evidence

- `fixtures/contract-0.171.0.json`: contract and runtime profile; a repeat generation produced identical stable/experimental manifest and effective-configuration digests.
- `fixtures/initialize-0.171.0.json`: sanitized `initialize → initialized → thread/start` exchange.
- `fixtures/live-turn-0.171.0.json`: successful no-tools root turn with matching `turn/completed(status=completed)`.
- `fixtures/live-controls-0.171.0.json` and `live-controls-normalized-0.171.0.json`: same-thread follow-up and correlated interruption with matching `turn/completed(status=interrupted)`.

## Enabled claim

The Rust supervisor may qualify this exact tuple and proceed to direct-child App Server initialization. The application must still implement and test process ownership, queues, shutdown, rendering, and lifecycle validation before exposing a live chat control.

## Fail-closed rule

Any other version, native digest, platform, transport, generated contract, or effective feature profile is incompatible until separately qualified. EOF, timeout, process exit, and silence remain `Disconnected`/`Gap`, never terminal success.
