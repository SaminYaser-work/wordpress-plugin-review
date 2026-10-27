---
name: wordpress-plugin-review
description: Audit a WordPress plugin's source code, distribution ZIP, readme, assets, REST/AJAX endpoints, privacy behavior and advertised features against applicable WordPress.org Plugin Directory rules and reviewer-reported pitfalls. Produce a file-backed Markdown report with evidence, risk, suggested fixes and retest steps; ignore SVN/release workflow rules.
---

# WordPress.org Plugin Review

Use this skill when reviewing a WordPress plugin **before submission, update, reopening or resubmission**. Accept a plugin directory or a distributable ZIP, optionally a separate source tree and a WordPress.org slug. This is a read-only review, **not** a request to patch the plugin. The required deliverable after inspecting a plugin is an actual `WORDPRESS_PLUGIN_REVIEW.md` file, not merely a chat summary.

## Scope and authority

1. Consult the [official Detailed Plugin Guidelines](https://developer.wordpress.org/plugins/wordpress-org/detailed-plugin-guidelines/) and [Common Issues](https://developer.wordpress.org/plugins/wordpress-org/common-issues/) when internet access is available. Use the exact WordPress.org rule number when one applies; record other reviewer expectations as **Technical review concern**. The official policy takes precedence over old email examples. Guidelines and enforcement can change; note the check date.
2. Read `references/rulebook.md` for **applicability gates** and security checks. Examine **only rules relevant to the inspected plugin**, based on its contents, functionality, assets, dependencies and readme. Never force a finding just because a rule exists.
3. Read `references/reviewer-cases.md` for examples extracted **only from WordPress.org Plugins Team messages** in the user-provided `WordPress ORG flag.docx` and the three linked Google Docs tabs dated 2026-10-26 (PostX, WowStore and WowOptin). Ignore developer replies, Bengali repeats, summary/recommendation tables and unrelated material. Examples illustrate patterns, not proof about a newly reviewed plugin.
4. **Explicit exclusions:** do not audit or report SVN commit frequency, tagging/trunk layout, SVN upload instructions, release-process version increments, release emails, reviewer reply etiquette, or WordPress.org directory administration. In particular, exclude guideline **14**, guideline **15**, and SVN-specific portions of guideline **3**. Do not ask to inspect an SVN repository. Checking package contents, plugin code, GPL compatibility, readme claims and functionality **is** in scope.
5. Block Directory restrictions apply **only** if the plugin is a single-block plugin submitted to the Block Directory. Ordinary plugins that include blocks are not automatically subject to those extra rules.

## Mandatory sequence

### 1. Establish exactly what ships

- Prefer the **distribution ZIP** when supplied, since reviewers inspect what ships. If both ZIP and source exist, review the ZIP and compare important source/build outputs; report discrepancies. If only source exists, state that distributable ZIP contents were not verified.
- Identify plugin main file, header, text domain, directory slug (ask for explicit directory slug only if needed and unavailable), readme.txt, license, bundled vendors, compiled JS/CSS and source maps, and whether WooCommerce or other dependencies are required.
- Do not assume a string found in a file is executable. Check whether the relevant handler, import, hook, route or template is reachable in the free plugin.
- Avoid exposing secrets from code in the report: redact API keys, tokens, passwords, personal data and complete request bodies.

### 2. Perform a breadth-first static pass

Run the bundled **read-only** triage script if Python 3 is available:

```bash
python3 scripts/scan_plugin.py /path/to/plugin.zip --slug your-plugin-slug --out WORDPRESS_PLUGIN_REVIEW.md --json review-inventory.json
# or
python3 scripts/scan_plugin.py /path/to/plugin-directory --out WORDPRESS_PLUGIN_REVIEW.md
```

The script supports a ZIP or directory. Its hits are **candidates**, not determinations. Keep its report/inventory as an evidence checklist; analyze each hit against full surrounding code and the rulebook. It cannot establish permission flows, runtime consent, feature parity, disclosure sufficiency or true vulnerability on its own. Do not label every regex hit a violation.

Also search recursively, including shipped `vendor/`, PHP templates, build artifacts, `.map` files and compiled scripts, for related occurrences. Follow helper functions and call chains; a permission/sanitization check may be one function upstream, and an apparent opt-in may be ineffective because sends occur elsewhere. Group repeated instances without omitting their locations.

### 3. Audit applicable high-risk families deeply

Read `references/rulebook.md` for investigation questions, expected findings and caveats. Prioritize:

- **Locked/trial functionality (#5/#6)**: included but Pro-disabled engines, rules, templates, UI/actions, limits, local code and licensing gates; distinguish separate paid add-ons and genuine server-side SaaS.
- **Phoning home and external services (#6/#7/#8)**: activation, onboarding, deactivation, analytics, IP geolocation, admin identity, site/plugin inventory, support submissions, carrier/payment/AI APIs, dynamic JS/fetch and remote assets. Trace destinations, payloads, triggers, opt-in default, refusal behavior and `readme.txt` disclosures; check terms/privacy URLs if network is available.
- **Authorization and input/output security**: REST/Abilities `permission_callback`, public analytics mutation scope, object-specific and settings capabilities, AJAX nonces AND authorization, guest-order key/ownership checks, JSON `sanitize_callback`/`validate_callback`, superglobals, unslash/type validation, SQL preparation, block/shortcode returns, filter output and late escaping. Trace raw custom CSS/JS/PHP from editors/imports through storage to output; distinguish arbitrary code insertion from CSS generated by structured controls. Use the rulebook's dedicated checks.
- **Plugin behavior/quality**: installs or activates other plugins without an explicit user action, global dashboard CSS, activation errors, WP_DEBUG warnings, database `dbDelta()` syntax, deprecated functions, unsafe directly accessible PHP files, bad plugin paths, filename portability, code readability/source availability, i18n slug, bundled core libraries, insecure PDF/upload caching, unused test/build files.
- **Readme-versus-code parity (#16 and related)**: extract every material free-plugin capability claim from description, FAQ, screenshots and feature bullets. Trace it to working hooks, routes, settings and output. Distinguish separate Pro/SaaS functionality clearly. Verify that claimed features are **implemented and reachable**, not merely configured, stored, stubbed, or present as dead code.
- **Promotion/trust**: public-facing credits opt-in (#10), admin advertising (#11), misleading endorsements/reviews/Trustpilot-like references (#9/#12/possibly #17), trademark/third-party branding where applicable. A mere brand string is not automatically a violation.

### 4. Run tooling and runtime tests when available

- Prefer Plugin Check (PCP) and PHPCS + WordPress Coding Standards for independent coverage; capture commands, versions and findings. See `references/validation.md` for safe commands. Don't claim tools were run if unavailable. Don't silently dismiss their warnings; verify or explain false positives.
- In a **disposable** WordPress test environment, enable `WP_DEBUG` and `WP_DEBUG_LOG`; activate/deactivate and navigate representative frontend/admin/REST flows. Test an unauthenticated visitor, subscriber and authorized admin where appropriate. Use clean installs, missing dependencies, renamed plugin folder, both opt-out/opt-in states, and free/no-license state when relevant.
- Monitor network requests in PHP and the browser from activation through deactivation. Do **not** transmit real personal or site data to unknown external endpoints during testing; use mocks/interception or an isolated environment.
- Do not execute an untrusted plugin on the host. If a safe runtime is unavailable, say **Not tested**; keep runtime-dependent conclusions conditional.

### 5. Create the final Markdown report (required)

Use `references/report-template.md`. Write `WORDPRESS_PLUGIN_REVIEW.md` to the current user-accessible output folder (or explicit path). The report must include:

1. Plugin identity, exact source/ZIP reviewed, review date, scope and tool/runtime coverage.
2. Executive verdict **based on evidence**, counts by severity, blockers, and caveats. Do not promise WordPress.org approval.
3. **Every distinct actionable finding**, using stable IDs and separate locations for repeated matches. For each: `Status` (Confirmed / Probable / Needs manual verification), `Severity` (Blocker / High / Medium / Low), `Confidence` (High / Medium / Low), applicable rule **or** Technical review concern, `file:line`, excerpt, exact behavior and why it matters, suggested fix (and alternative where appropriate), retest steps, and source links.
4. Service inventory (endpoint, data, trigger, consent, readme disclosure and terms/privacy availability) **only if external calls exist**.
5. Free-feature/marketing claim matrix **only when claims or a Pro split exist**.
6. Findings requiring manual confirmation, checks that could not run, and explicitly **not applicable** categories as a short appendix (never inflate issue totals with N/A rules).
7. Prioritized remediation checklist and verification/retest plan.

Keep the diagnosis separate from suggested remediation. Do not invent line numbers, runtime observations, missing service disclosures or feature absence. State uncertainty plainly. If the plugin source was not provided, create a report **template only** and do not manufacture actual plugin issues.

## Evidentiary discipline

- **Reviewer email ≠ universal rule.** WordPress.org emails contain automated/human-reviewed hints and possible false positives. Trace every example to policy, common reviewer practice and the plugin under inspection.
- **Remote URL ≠ phoning home.** Inspect use and trigger. Service calls may be legitimate if functional, documented and consensual as required. A Terms/Privacy link's presence is not proof it is correct.
- **Pro UI ≠ trialware.** Flag only when included local functionality is purposefully locked/limited; separately distributed add-ons and clearly differentiated advertising may be fine.
- **Rate limit ≠ automatically trialware.** Determine whether a usage limit is a monetization/trial quota or a legitimate safety guard; one reviewer flagged a 20-uploads/IP/hour limit, so flag such mechanisms for investigation rather than automatically convicting them.
- **`permission_callback => __return_true` ≠ automatically unsafe.** Public routes can be intentional. Verify data/action sensitivity and the handler. Nonces alone do not confer authorization.
- **`include` ≠ blanket forbidden.** For `wp-load.php` and bootstrap files, direct loading is a serious concern; for legitimate core helper files inspect necessity, `require_once` use and the immediate call.
- **`ob_start()` ≠ automatically unclosed.** Trace all success/error/return paths and nesting; verify matching close.
- **`json_decode()` ≠ sanitizer.** Validate decoded structure and sanitize fields according to context; do not destroy structured JSON with blind pre-decoding string sanitization.
- **`esc_html()` ≠ correct for rich HTML.** For intentional markup use appropriate `wp_kses()` allowlist; escape at final output.

## Deliverables

Give the user the **Markdown report file** and a short summary with top blockers. If creating/maintaining this skill itself, provide the skill folder or ZIP plus the report template; **do not claim to have scanned a plugin unless plugin code was actually supplied and inspected**.
