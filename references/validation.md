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

## Runtime verification checklist

1. Isolate a fresh WordPress test install; set `WP_DEBUG` and `WP_DEBUG_LOG` true; capture PHP notices, activation output, DB changes, and unexpected network calls.
2. Before consent or service configuration, activate and inspect admin onboarding/deactivation. Check PHP HTTP requests and browser `fetch`/XHR/image/script requests. Mask payloads.
3. Inspect REST API routes and AJAX endpoints as visitor, subscriber, editor/shop-manager and admin only where roles apply; probe sensitive GET operations and privileged writes; require the precise capability for each operation.
4. Disable the Pro add-on and set no license. Trigger every advertised free feature; exercise limits and empty states; compare with readme and screenshots. Confirm legitimate remote SaaS actually processes offsite.
5. Try nonces/capabilities independently; verify invalid payloads and nested JSON are rejected or sanitized. Inspect all returned/echoed HTML safely in context.
6. Reinstall in a directory whose name differs from the expected slug, when practical. Check script/assets links, `admin_url` and upload paths.
7. Where documents are generated, directly request their stored URLs unauthenticated. Confirm sensitive files cannot be accessed, listed, or guessed without authorization.
8. Ensure buffered output closes on exceptions, early returns and failed API calls; verify `dbDelta()` table creation and upgrades on clean and existing installs.
9. Rebuild scripts and scan output bundles and maps, not just source. Check package ZIP for filename collisions, temporary caches/scripts and available maintained JS/CSS source.
10. Document tool command, result, WordPress/PHP version and gaps. Exclude SVN repository/tagging/version-number checks by design.

### Targeted retests from the 2026-10-26 follow-ups

- Exercise raw CSS/JS inputs through save, import and old stored data; verify structured styling still works and no alternate raw-code renderer remains.
- Test post mutation with/without object capabilities, global settings as editor/admin, and public analytics with invalid/unrelated IDs and valid visitor events.
- For order-received templates, test guest access with correct/missing/wrong/cross-order keys and logged-in access to another customer's order; inspect every rendered field.
- Probe nonce/capability combinations and alternate handler branches independently. Test block returns and final filter output with safe formatting and hostile markup, including custom helper allowlists.
- Check multi-step save/support/render paths with Pro disabled and no license. Trace global AJAX names through PHP and compiled clients; confirm valid prefixed actions still dispatch.

These are investigation/retest scenarios, not capabilities proven by the bundled regex scanner. Record runtime checks as **Not tested** when no suitable WordPress environment exists.

## Review boundaries

The auditing agent should perform *read-only inspection* unless asked to fix issues. It must not silently modify any plugin files, run remote installers, send actual user analytics, or open private site content on the public internet. For ambiguous cases such as real service SDKs, planned add-ons or rate limits, use a `Needs manual verification` finding with explicit questions rather than a categorical violation.
