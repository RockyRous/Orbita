# Use App Server as the integration and execution boundary

Orbita will be a thin client of the public Codex App Server contract, which remains the source of truth for execution and orchestration. We rejected forking the proprietary Codex Desktop UI, whose source is not published, and rejected maintaining full forks of the Codex or third-party client codebases because either approach would create an unnecessary, fast-moving runtime and product surface inside Orbita; selective reuse of compatible open-source code remains possible with license review and attribution.
