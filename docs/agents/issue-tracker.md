# Issue tracker: GitHub

Issues and specifications for Orbita live in this repository's GitHub Issues. Use the `gh` CLI from the repository root.

## Conventions

- Create: `gh issue create --title "..." --body "..."`.
- Read: `gh issue view <number> --json number,title,body,labels,comments`.
- List: `gh issue list --state open` with relevant `--label` filters.
- Comment: `gh issue comment <number> --body "..."`.
- Apply or remove a label: `gh issue edit <number> --add-label "..."` or `--remove-label "..."`.
- Close: explain the outcome in a comment, then run `gh issue close <number>`.

Infer the repository from `git remote -v`. Before creating an issue, verify that `gh repo view --json nameWithOwner` resolves to this repository, not an upstream project.

## Pull requests as a triage surface

**PRs as a request surface: no.** External pull requests are reviewed as contributions, not triaged as feature requests.

## When a skill refers to the issue tracker

- "Publish" means create a GitHub issue here.
- "Fetch a ticket" means read the corresponding GitHub issue.
