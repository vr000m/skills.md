# Global Preferences

## Git
- **Never squash merge PRs.** Use regular merge (`gh pr merge --merge --delete-branch`) to preserve individual commit history.
- **Always work on feature branches** — never commit directly to main. Create branch, dev plan, update docs, then PR.

## Workflow
- Discuss and plan before implementing non-trivial features.
- Update docs (AGENTS.md, README.md, dev plan) alongside code changes, not after.
- Run reviews (`/review`, `/security-review`) before merging.
- Fix all review findings before merge.
- Update PR description to reflect final state of the work.

## Security
- Before committing, check staged files for PII, private keys, secrets, and credentials. Never commit these.
