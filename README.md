# WordPress.org Plugin Review

A portable agent skill for reviewing WordPress plugins before submission, updates, reopening, or resubmission. It combines applicable WordPress.org rules with historical Plugins Team review cases and produces an evidence-backed Markdown report.

The review is read-only. The agent inspects plugin code and release artifacts, traces findings to reachable behavior, and recommends fixes without modifying the plugin.

## What it reviews

- **Free/Pro boundaries:** locally implemented features restricted by licenses, trials, quotas, support guards, or renderer limits; distinguish separate add-ons and genuine external services.
- **Privacy and external services:** PHP/browser requests, telemetry consent, transmitted data, remote assets, readme disclosures, and applicable terms/privacy links.
- **Security:** REST, Abilities and AJAX permissions, object-specific capabilities, guest-order access, nonce logic, nested input validation, returned block markup, filtered HTML, and arbitrary code insertion.
- **Feature claims:** compare readme, FAQ, screenshots, and compiled marketing copy with working free-plugin behavior.
- **Runtime and packaging:** activation issues, private document exposure, output buffers, database setup, plugin paths, naming, translations, dependencies, and shipped assets.

SVN administration, tagging, commit frequency, version-bump requirements, release correspondence, and reviewer etiquette are outside this skill's scope. Block Directory restrictions apply only to actual Block Directory submissions.

## Install

Clone this repository:

```bash
git clone https://github.com/SaminYaser-work/wordpress-plugin-review.git
```

Place the complete `wordpress-plugin-review` folder in your agent's supported skills directory. Keep `SKILL.md`, `references/`, and `scripts/` together so relative paths resolve. Follow your agent's instructions for discovering or loading skills.

The optional scanner requires Python 3.10 or newer and uses only the standard library. A full review also requires an agent with access to the plugin files. Internet access allows current policy verification; an isolated WordPress environment allows runtime checks.

## Ask an agent to review a plugin

```text
Use wordpress-plugin-review to review /path/to/plugin.zip for WordPress.org
compliance and write WORDPRESS_PLUGIN_REVIEW.md.
```

A plugin directory also works. Supply the distribution ZIP when possible, since reviewers inspect what ships. You can provide a separate source tree and the WordPress.org slug as additional context.

The completed report includes:

- Exact artifact, scope, date, and tooling/runtime coverage.
- Stable finding IDs with severity, confidence, current file/line evidence, reachable behavior, applicable policy, suggested fixes, and retests.
- External-service and free-feature claim inventories when applicable.
- Unverified concerns, checks that could not run, and prioritized remediation.

See the [report template](references/report-template.md) and [hypothetical example report](examples/EXAMPLE_REPORT.md).

## Run the standalone triage scanner

From this repository's root, scan a ZIP:

```bash
python3 scripts/scan_plugin.py /path/to/plugin.zip \
  --slug your-plugin-slug \
  --out WORDPRESS_PLUGIN_REVIEW.md \
  --json review-inventory.json
```

Or scan a directory:

```bash
python3 scripts/scan_plugin.py /path/to/plugin-directory \
  --out WORDPRESS_PLUGIN_REVIEW.md
```

The scanner reads files without extracting or executing plugin code. Its output is a candidate checklist, not a completed compliance audit. An agent or reviewer must inspect surrounding code, registration paths, consent, service disclosures, feature reachability, and relevant runtime behavior. The scanner cannot establish those facts from regex matches.

## Evidence and limitations

Official policy takes precedence over historical email examples. A public endpoint, Pro UI, remote URL, PHPCS suppression, or generated stylesheet is not automatically a violation. Each finding needs evidence from the plugin currently under review.

The skill does not guarantee WordPress.org approval. Tooling and runtime checks must be reported accurately; unavailable checks remain explicitly untested. Do not execute an untrusted plugin on the host to perform a review.

## Included guidance

| File | Purpose |
|---|---|
| [SKILL.md](SKILL.md) | Agent workflow, scope, evidence requirements, and deliverables |
| [Rulebook](references/rulebook.md) | Applicability gates and detailed review checks |
| [Reviewer cases](references/reviewer-cases.md) | Historical Plugins Team examples with source provenance |
| [Report template](references/report-template.md) | Required Markdown report structure |
| [Validation guide](references/validation.md) | Official references, commands, and runtime retests |
| [Scanner](scripts/scan_plugin.py) | Read-only ZIP/directory triage with Markdown and optional JSON output |
| [Tests](tests/test_scan_plugin.py) | Scanner regression checks |

## Validation

Run the scanner tests:

```bash
python3 -m unittest discover -s tests -v
```

## Policy and reviewer-source dates

The initial official-source review was completed on 2026-10-11. On 2026-10-27, the [Detailed Plugin Guidelines](https://developer.wordpress.org/plugins/wordpress-org/detailed-plugin-guidelines/), [Common Issues](https://developer.wordpress.org/plugins/wordpress-org/common-issues/), [escaping guidance](https://developer.wordpress.org/apis/security/escaping/), and [Abilities registration documentation](https://developer.wordpress.org/reference/functions/wp_register_ability/) were rechecked. Recheck applicable policy during each new audit.

The case bank incorporates reviewer-only examples from the supplied historical document and three follow-up emails dated 2026-10-26 for PostX, WowStore, and WowOptin. These add checks for arbitrary code insertion, guest-order authorization, public analytics integrity, block/filter output, multi-step feature restrictions, and global action prefixes. Sources and review IDs appear in the [case bank](references/reviewer-cases.md); historical file locations are not findings about current plugin versions.
