# Validation resources and commands

## Official sources checked (2026-10-11)

- [Detailed Plugin Guidelines](https://developer.wordpress.org/plugins/wordpress-org/detailed-plugin-guidelines/) — numbered directory rules. Re-check at runtime if online.
- [Common Issues](https://developer.wordpress.org/plugins/wordpress-org/common-issues/) — security, readme, compat, PHP, libraries, changes to other plugins, external services and packaging checks.
- [Block Directory Specific Guidelines](https://developer.wordpress.org/plugins/wordpress-org/block-specific-plugin-guidelines/) — apply **only** to dedicated block-only plugins in that directory, not plugins that merely use blocks.
- [Plugin Check](https://wordpress.org/plugins/plugin-check/) and [Plugin Check CLI documentation](https://github.com/WordPress/plugin-check/blob/trunk/docs/CLI.md).
- [Input Sanitization](https://developer.wordpress.org/apis/security/sanitizing/) and [Escaping](https://developer.wordpress.org/apis/security/escaping/).
- [REST API endpoint registration](https://developer.wordpress.org/rest-api/extending-the-rest-api/adding-custom-endpoints/) and [Roles & Capabilities](https://developer.wordpress.org/plugins/security/checking-user-capabilities/).
- [Determining plugin directories](https://developer.wordpress.org/plugins/plugin-basics/determining-plugin-and-content-directories/).
- [WordPress-Coding-Standards on GitHub](https://github.com/WordPress/WordPress-Coding-Standards).

**Targeted refresh, 2026-10-27:** rechecked Detailed Plugin Guidelines, Common Issues (including prefixing), Escaping (including safe-return exceptions), and [`wp_register_ability()`](https://developer.wordpress.org/reference/functions/wp_register_ability/). The remaining sources retain the earlier check date. Three reviewer emails dated 2026-10-26 are linked with review IDs in [reviewer-cases.md](reviewer-cases.md); their technical examples supplement current official guidance.

**Debugging/PHP tooling refresh, 2026-11-01:** checked [WordPress debugging](https://developer.wordpress.org/advanced-administration/debug/debug-wordpress/), [PHPCompatibilityWP usage](https://github.com/PHPCompatibility/PHPCompatibilityWP#how-to-use) and [PHPCompatibility testVersion](https://github.com/PHPCompatibility/PHPCompatibility#testversion-in-the-ruleset-versus-command-line). Re-check installed tool capabilities when running an audit.

**Reviewer follow-up refresh, 2026-11-08:** inspected all nine reviewer-message tabs linked in [reviewer-cases.md](reviewer-cases.md), excluding nine reply/draft tabs. Rechecked Detailed Plugin Guidelines, Common Issues, [Header Requirements](https://developer.wordpress.org/plugins/plugin-basics/header-requirements/), [`validate_plugin_requirements()`](https://developer.wordpress.org/reference/functions/validate_plugin_requirements/), [`wp_strip_all_tags()`](https://developer.wordpress.org/reference/functions/wp_strip_all_tags/), [`wp_add_inline_style()`](https://developer.wordpress.org/reference/functions/wp_add_inline_style/) and [`safecss_filter_attr()`](https://developer.wordpress.org/reference/functions/safecss_filter_attr/). Treat email examples as investigation prompts, with current official policy taking precedence.

## Static analysis (when installed)

Use actual command paths for your environment. Examples for a disposable WP installation with Plugin Check already installed:

```bash
# Listing available checks does not audit the plugin.
wp plugin list-checks

# Official checks for the installed plugin. Check --mode and flags against the local version.
wp plugin check your-plugin-slug --mode=new --format=json

# PHPCS with current WordPress Coding Standards installed and configured.
phpcs --standard=WordPress --extensions=php /path/to/plugin

# PHP syntax check of each first-party .php file (example, not a policy review).
find /path/to/plugin -name '*.php' -type f -print0 | xargs -0 -n1 php -l
```

Warnings: Plugin Check is complementary to manual review, and its defaults/CLI options may vary by version. Running PCP and PHPCS does **not** prove that WordPress.org will accept the plugin. WPCS sniffs cover static patterns but not full consent, privacy, feature reachability or business rules. Do not execute code from an unknown plugin on the host just to run tools. Prefer isolated environment.

Always perform the rulebook's **Direct CSS/JS output and late escaping** checks manually, including suppressed and excluded code. The bundled scanner is lexical triage and can miss multiline, interpolated or helper-generated output. Record separate results for direct style/script output and dynamic-output escaping; a clean PHPCS run does not satisfy these checks.

## WordPress/PHP requirements and bootstrap (mandatory)

Record main-header and readme `Requires at least` / `Requires PHP` separately. Trace core API introduction versions and plugin/extension dependencies to the first load/use, including generated/vendor code. Confirm that header requirements and compatible guards protect the bootstrap where applicable; declaration presence alone does not prove this. Use a disposable stack for supported-minimum activation and missing/unsupported-dependency refusal tests, capturing response/output and fresh logs. Record unavailable combinations as **Not tested**. Keep metadata defects separate from observed runtime failures. The PHP procedure below supplies the syntax/function/dependency checks; it does not substitute for WordPress-version requirements.

## Declared PHP compatibility (mandatory)

1. Extract `Requires PHP` from the main plugin header and `readme.txt`; record exact locations and disagreements. Inspect root Composer constraints, lockfile/platform settings, and requirements of the dependency versions actually shipped. Composer's simulated `config.platform.php` is not a runtime test. If no unambiguous minimum exists, record the metadata gap and state any provisional test target explicitly.
2. Run a dedicated compatibility scan against the declared minimum, including shipped `vendor/`, generated PHP, templates and other PHP-bearing extensions. Use an installed, suitable PHPCompatibilityWP ruleset; WPCS and the bundled Python scanner do not replace it. Inspect local exclusions/suppressions and manually account for omitted shipped code. Capture PHPCS/ruleset versions, target range, file coverage and skipped paths. If unavailable, perform targeted source review and report automated coverage as **Not run**; do not silently install dependencies into the reviewed plugin.

```bash
# Examples: use installed tooling outside the reviewed artifact if necessary.
phpcs --version
phpcs -i
# Exact minimum target catches newer features; 7.4 is an example, not a fixed default.
phpcs -p /path/to/plugin --standard=PHPCompatibilityWP --extensions=php,inc,phtml --runtime-set testVersion 7.4 --report=full
# Also check the actually supported range; replace the upper bound with audit scope.
phpcs -p /path/to/plugin --standard=PHPCompatibilityWP --extensions=php,inc,phtml --runtime-set testVersion 7.4-8.3 --report=full
```

3. Trace newer functions/classes/constants, changed signatures, removed APIs and newer syntax to reachable code. Check `function_exists()`/version guards and polyfills, including those supplied by the minimum supported WordPress version. Verify the polyfill loads before use in activation, REST, cron, CLI and standalone entry paths where applicable. For example, `str_contains()` is newer than PHP 7.4, but a correctly loaded WordPress polyfill can make its use valid. Unsupported syntax in a parsed file cannot be rescued by a runtime branch in that file. Consult the relevant [PHP migration guides](https://www.php.net/manual/en/appendices.php) for the feature's actual introduction/removal version.
4. Lint shipped PHP using the **minimum-version interpreter**, then activate, use and deactivate the plugin on that interpreter in an isolated WordPress stack supporting that PHP version. Also exercise a supported modern PHP version for deprecations/removals. Record actual CLI and web/FPM PHP versions separately; host PHP 8 lint does not establish PHP 7.4 support. If the installed WordPress or a required dependency cannot run on the declared minimum, use a compatible test stack or record the blocked matrix row rather than claiming a pass. Never execute an untrusted plugin directly on the host.
5. Report declaration mismatches, confirmed failures and unresolved static hits distinctly. Each issue needs a file/line, required versus declared version, triggering load/call path, guard/polyfill assessment and retest. A clean scan is limited to the tool's supported checks; unavailable minimum-version lint/runtime stays **Not tested**.

## Debug configuration and per-phase log evidence (mandatory)

Use a disposable/local test installation. Plugin source remains read-only; debug configuration is an explicit test-setup exception. In LocalWP, use its generated Site Shell/runtime for WP-CLI rather than assuming the host shell matches PHP or database settings.

1. Locate the active `wp-config.php` and record original debug settings without copying secrets. Change existing false values or add missing definitions **before WordPress boots**, without duplicate constants:

```php
define( 'WP_DEBUG', true );
define( 'WP_DEBUG_LOG', true );
define( 'WP_DEBUG_DISPLAY', false );
```

With WP-CLI available in that test environment, `wp config set WP_DEBUG true --raw --type=constant` and `wp config set WP_DEBUG_LOG true --raw --type=constant` can set the first two. Set `WP_DEBUG_DISPLAY` false similarly. Preserve an existing valid custom `WP_DEBUG_LOG` path instead of replacing it. Use booleans, not strings such as `'false'`. Do not blanket-enable every debug option: `SCRIPT_DEBUG` changes asset selection, and `SAVEQUERIES` is unnecessary for this check.

2. Resolve the effective log location: boolean true uses `WP_CONTENT_DIR/debug.log`, which need not be the default `wp-content` path; a string can select a custom file. Verify effective `WP_DEBUG`, PHP `log_errors`/`error_log` and writability in the **web runtime** used for testing. Send one uniquely labeled, nonsecret `error_log()` probe through a controlled request in the disposable environment and verify it reaches that file. An isolated `wp --skip-plugins --skip-themes eval 'error_log("WPR logging probe");'` can additionally verify CLI logging; it does not verify web/FPM logging. Keep probes out of plugin files and issue totals. If logging fails, fix test setup or record **Not tested**. Early startup failures may appear only in PHP/FPM/web-server logs; inspect those too when a request fails without a debug-log entry.

3. Preserve the existing log. Before each phase, record a timestamp and file boundary; after requests and triggered work finish, read **all new entries**, including multiline traces. The optional stdlib helper records file identity, size and a prefix digest without truncating the log:

```bash
# Run from the skill directory; use a private evidence directory outside webroot.
python3 scripts/debug_log.py baseline /path/to/debug.log --state /private/review/activation-state.json
# Activate the plugin through wp-admin (WP-CLI may supplement the browser test).
python3 scripts/debug_log.py delta /path/to/debug.log --state /private/review/activation-state.json --out /private/review/activation-log.json
```

Create the evidence directory first. Repeat with fresh state/output files for **normal operations** and **deactivation**, and for each PHP runtime. Exercise representative admin/frontend features, REST/AJAX, cron/background work and dependency/error paths where applicable. Capture action, role, URL/command, time window, response/output, PHP version and log evidence for each phase. Review existing historical entries separately as leads; confirm attribution with a fresh reproduction.

4. Inspect helper JSON locally; its `text` field contains the captured entries. Exit 0 means capture succeeded, not that the plugin passed. `missing` or `unchanged` alone proves neither healthy logging nor exercised code. `removed` or `replaced_or_rewritten` means the boundary was lost: inspect retained/rotated logs and repeat the phase with a fresh baseline. On replacement/rewrite the helper captures the current file from its start, which can include old entries. `truncated: true` means the default 1,000,000-byte evidence cap was reached; increase `--max-bytes` or inspect the rest before claiming full coverage. `delta` does not advance its baseline. Keep state, output and log paths distinct. Capture errors exit 2 and are coverage gaps.

5. Classify new fatals, warnings, notices, deprecations and database errors by source and reachability. A stack trace ending in core/vendor may still originate in the plugin; unrelated theme/plugin noise is not a plugin defect. Correlate fresh log lines with actions and source locations, reproduce suspicious entries and redact credentials, personal data and request payloads before reporting. Store raw artifacts privately; never include them in release packages. Restore original test-site debug settings after review unless the user asks to retain them. Record settings changed/restored and any failed cleanup; never truncate historical logs as cleanup.

## Runtime verification checklist

1. Complete the mandatory debug configuration/log procedure above; capture separate activation, operation and deactivation evidence, plus DB changes and unexpected network calls. Complete the PHP compatibility matrix or explicitly record unavailable minimum-version tests.
2. Before consent or service configuration, activate and inspect admin onboarding/deactivation. Check PHP HTTP requests and browser `fetch`/XHR/image/script requests. Mask payloads.
3. Inspect REST API routes and AJAX endpoints as visitor, subscriber, editor/shop-manager and admin only where roles apply; probe sensitive GET operations and privileged writes; require the precise capability for each operation.
4. Disable the Pro add-on and set no license. Trigger every advertised free feature; exercise limits and empty states; compare with readme and screenshots. Confirm legitimate remote SaaS actually processes offsite.
5. Try nonces/capabilities independently; verify invalid payloads and nested JSON are rejected or sanitized. Inspect all returned/echoed HTML safely in context.
6. Reinstall in a directory whose name differs from the expected slug, when practical. Check script/assets links, `admin_url` and upload paths.
7. Where documents are generated, directly request their stored URLs unauthenticated. Confirm sensitive files cannot be accessed, listed, or guessed without authorization.
8. Ensure buffered output closes on exceptions, early returns and failed API calls; verify `dbDelta()` table creation and upgrades on clean and existing installs.
9. Rebuild scripts and scan output bundles and maps, not just source. Check package ZIP for filename collisions, temporary caches/scripts and available maintained JS/CSS source.
10. Document tool command, result, WordPress/PHP version and gaps. Exclude SVN repository/tagging/version-number checks by design.

### Targeted reviewer-derived retests

- Exercise raw CSS/JS inputs through save, import and old stored data; verify structured styling still works and no alternate raw-code renderer remains.
- Test post mutation with/without object capabilities, global settings as editor/admin, and public analytics with invalid/unrelated IDs and valid visitor events.
- For order-received templates, test guest access with correct/missing/wrong/cross-order keys and logged-in access to another customer's order; inspect every rendered field.
- Probe nonce/capability combinations and alternate handler branches independently. Test block returns and final filter output with safe formatting and hostile markup, including custom helper allowlists.
- Check multi-step save/support/render paths with Pro disabled and no license. Trace global AJAX names through PHP and compiled clients; confirm valid prefixed actions still dispatch.
- With add-ons absent, compare settings choices/mappings and action/filter registrations with included renderers across layouts/types. Verify that an upgrade gate restricts a complete local feature before reporting #5; a genuinely separate implementation remains distinct.
- Test public/search responses with visitor and relevant low-privilege roles, arbitrary resource types/statuses and guest/missing identity fields. Verify coupon/private-resource protection and notification field minimization while preserving intended public data.
- Inspect fresh-install remote-font requests, refusal, consent and revocation in PHP and browser paths using interception or fixtures. Verify refusal prevents remote requests and any advertised local fallback works; licensing and legal links alone do not prove consent.
- Trace CSS from save/import, legacy storage and rendered-content extraction through the final style sink. Probe disallowed properties/URLs and boundary-breaking values safely; test valid typed controls too. `wp_strip_all_tags()` and `wp_add_inline_style()` are not stylesheet validation.
- Test custom HTML helpers before and after placeholder restoration and downstream filters, including script bodies and media markup. Trace an actual untrusted source before alleging an escaping bypass; preserve valid rich markup.
- Compare output-buffer levels before/after success, early return and error paths with a pre-existing outer buffer. Verify the plugin closes only its own buffers. Trace core helper includes through earlier loaders on supported WordPress versions; redundant `require_once` is not an observed fatal.

These are investigation/retest scenarios, not capabilities proven by the bundled regex scanner. Record runtime checks as **Not tested** when no suitable WordPress environment exists.

## Review boundaries

The auditing agent should keep plugin files read-only unless asked to fix issues. Enabling and later restoring debugging in a disposable test site's `wp-config.php` is permitted test setup. Do not change a production site's configuration for a review; use an isolated copy. The agent must not silently modify plugin files, run remote installers, send actual user analytics, or open private site content on the public internet. For ambiguous cases such as real service SDKs, planned add-ons or rate limits, use a `Needs manual verification` finding with explicit questions rather than a categorical violation.
