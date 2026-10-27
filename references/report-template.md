# Required Markdown report template

Save the completed report as `WORDPRESS_PLUGIN_REVIEW.md` using the output-location rule in `SKILL.md`, step 5 (existing `docs/`, otherwise the reviewed root; an explicit user path takes precedence). Remove conditional sections not applicable. Use exact paths/line numbers from the **current** inspected plugin, never historical sample paths as if current.

````markdown
# WordPress.org Plugin Compliance Review — [Plugin name]

**Reviewed:** YYYY-MM-DD  
**Plugin:** [name] / [exact WordPress.org slug]  
**Input:** [source path / ZIP + SHA-256 if available]  
**Release artifact verified:** Yes / No  
**WordPress/PHP/WooCommerce test versions:** [actual values or Not tested]  
**Sources:** [official policies checked on DATE; reviewer-case bank consulted]

## Executive summary

**Assessment:** Blocked / Changes recommended / No material findings in assessed scope / Incomplete review

| Severity | Confirmed | Probable | Needs verification |
|---|---:|---:|---:|
| Blocker | N | N | N |
| High | N | N | N |
| Medium | N | N | N |
| Low | N | N | N |

**Top blockers:** [2–5 concise findings, or None verified]
**Caveats:** [what was not supplied/tested; no approval guarantee]

## Detailed findings

### WPR-001 — [Clear, specific issue title]

- **Severity:** Blocker / High / Medium / Low
- **Status:** Confirmed / Probable / Needs manual verification
- **Confidence:** High / Medium / Low
- **Applicable policy:** [Guideline # and direct URL, or "Technical review concern" + relevant WordPress reference]
- **Current evidence:** `path/to/file.php:123`, `other/file.js:10`
- **Trigger / reachability:** [hook/REST route/user action/role/configuration and how code is reached]
- **Observed behavior:** [what the code actually does, not a regex suspicion]
- **Why a reviewer may flag it:** [specific rule/technical expectation]
- **Suggested fix:** [concrete change and alternative when appropriate]
- **Verification:** [targeted positive and negative test, or explicit inspection command]
- **Related historical reviewer example:** [optional matching case; label as historical, not evidence]

Short evidence excerpt if needed:

```php
// Redacted safe excerpt from current code; no secrets
```

[Repeat WPR-002, etc. for EVERY distinct actionable issue; list all relevant occurrences]

## External services and privacy inventory

*Include only when the plugin actually calls an external service.*

| Service / host | Where called | Trigger | Data categories sent | Explicit consent / default | readme disclosure | TOS / privacy URLs verified | Outcome |
|---|---|---|---|---|---|---|---|
| [service] | `file:line` | [onboarding] | [nonsecret summary] | [off/yes/no/unknown] | [complete/missing] | [actual checked links or unverified] | [Issue WPR-### / acceptable / unresolved] |

## Feature-claim consistency matrix

*Include only when readme/FAQ/screenshots/marketing make material functionality claims or free/Pro split exists.*

| Free plugin claim | Source of claim | Actual code path | Included and usable for free? | Outcome |
|---|---|---|---|---|
| [feature] | `readme.txt:xx` | `class-engine.php:yy` or not located after scoped search | yes/no/not tested | WPR-### or okay |

## Remediation plan

1. [ ] [Blocker or high-priority issue and fix]
2. [ ] [Next fix]
3. [ ] [Retest requirements]

## Validation and test evidence

| Check | Command / test | Result | Evidence / reason if not run |
|---|---|---|---|
| PCP | `wp plugin check <slug> --format=json` | Pass / Fail / Not run | [output or location] |
| PHPCS/WPCS | [actual command] | Pass / Fail / Not run | [...] |
| Direct CSS/JS output | trace template/printed style and script tags, including suppressed code | Pass / Fail / Not run | [locations, reachability and asset-loading findings] |
| Late output escaping | trace dynamic output at final sinks, including suppressed code | Pass / Fail / Not run | [output contexts, upstream-only escaping and findings] |
| PHP lint | [actual command] | Pass / Fail / Not run | [...] |
| Activation | clean WP + WP_DEBUG=true | Pass / Fail / Not run | [...] |
| Network/consent | no-consent and user-consent paths | Pass / Fail / Not run | [...] |
| Permissions | visitor/subscriber/admin REST and AJAX tests | Pass / Fail / Not run | [...] |
| Feature parity | free/no-license and add-on absent | Pass / Fail / Not run | [...] |
| Public files | direct HTTP request for cached documents | Pass / Fail / Not run | [...] |

## Manual review / uncertainties

- [Unresolved suspicious pattern: why not confirmed; exact next step]
- [Missing PHP/WordPress environment or absent distribution artifact]

## Not applicable and expressly excluded

- [Example: Block Directory-only guidelines — plugin is not a single-block Block Directory submission]
- SVN commits, trunk/tags, version bumps, release administration — excluded by review scope.

## References

- WordPress.org [Detailed Plugin Guidelines](https://developer.wordpress.org/plugins/wordpress-org/detailed-plugin-guidelines/)
- WordPress.org [Common Issues](https://developer.wordpress.org/plugins/wordpress-org/common-issues/)
- [Other precise docs directly applicable to detected issue]
````

**Report quality gate:** All finding IDs unique; no contradictory counts; each claimed issue has evidence + policy/technical source + specific fix + test; repeated occurrences not silently discarded; privacy payloads redacted; no guessed runtime assertions; no unrelated policy padding; no SVN workflow observations.
