# GitHub repository settings for the internal pilot

This document records observed settings and the desired review gate. It does not claim that a repository setting is active unless the GitHub API proved it.

## Observed on 2026-08-19

- Repository: private `itmitalles-de/essentials-freelancer`.
- Default branch: `master`; it remains unchanged for this pilot.
- Verified administrator and CODEOWNER: `@itmitalles`.
- GitHub Actions: enabled; repository workflow-token default is read-only and workflows cannot approve pull requests.
- Allowed Actions policy: all actions are currently allowed. GitHub's repository-level SHA-pinning enforcement is currently disabled, while every external action used by this repository is pinned to a reviewed 40-character commit SHA in source.
- Auto-merge: disabled.
- Server-side branch protection and repository rulesets: **externally blocked**. The GitHub API returned HTTP 403 because the current private-repository plan does not provide those features. Therefore required checks and CODEOWNER approval are not technically enforced by GitHub.
- `CODEOWNERS` is present for workflows, dependencies, migrations, invoice logic, backup/restore, SMTP, and security-sensitive code. Without branch protection it is routing evidence, not an enforcement claim.

## Desired `master` gate when the GitHub plan supports it

Configure this manually and capture a redacted settings screenshot or API response:

1. Require a pull request before merging; no direct pushes.
2. Require at least one approving review and CODEOWNER review.
3. Dismiss stale approvals when protected files change.
4. Require all current CI jobs, including `full-check` and `android-api35-smoke`.
5. Require branches to be up to date before merge.
6. Block force pushes and branch deletion.
7. Restrict bypass to the designated pilot operator; use bypass only for a documented incident.
8. Keep workflow permissions read-only and do not allow workflows to approve pull requests.
9. Keep automatic dependency PRs review-only; never auto-merge dependency updates.
10. Enable secret scanning, push protection, Dependabot alerts, and private vulnerability reporting where the account plan makes them available.

## Pilot fallback while enforcement is unavailable

- All work goes through a Draft PR; this pilot PR must not be merged as part of the preparation task.
- The operator verifies the head SHA, successful checks, CODEOWNER review, and clean deployment evidence manually before any later merge or deploy.
- Any failed or missing required check is a stop condition. A green synthetic workflow is not production evidence.
- Image digests, action SHAs, the Gradle wrapper checksum, Gradle dependency verification metadata, npm lock integrity, Python vulnerability audit, history-aware secret scan, and the generated pilot SBOM provide repository-side compensating controls.

## Recheck

Re-query repository settings before pilot exit and after any GitHub plan change. Record only non-secret settings; never export repository or organization secrets.
