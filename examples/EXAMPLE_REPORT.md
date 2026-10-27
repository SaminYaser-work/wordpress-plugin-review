# EXAMPLE ONLY — WordPress.org Plugin Review — Demo Shipping Plugin

> **Fictional example.** This is not a review of any user plugin or of the plugins in the historical emails.

**Date:** 2026-10-11  
**Input:** Example-only imaginary ZIP  
**Methods:** Hypothetical code inspection; no real tests run

## Executive summary

**Assessment:** Would require changes if the imaginary evidence below were present.

## Detailed findings

### WPR-001 — Locally implemented shipping mode disabled without Pro license

- **Severity:** Blocker
- **Status:** Hypothetical example (not a real confirmed issue)
- **Confidence:** N/A — example
- **Applicable policy:** [Guideline #5](https://developer.wordpress.org/plugins/wordpress-org/detailed-plugin-guidelines/#5-trialware-is-not-permitted)
- **Current evidence:** `includes/class-shipping-mode.php:88` (imaginary path)
- **Trigger / reachability:** Free checkout calculation supposedly tests `is_pro_active()` and refuses the built-in rate logic.
- **Why it matters:** Included local functionality cannot be locked behind a purchase.
- **Suggested fix:** Ship that functionality enabled for everyone or move its code to a truly separate paid add-on. Update feature copy to match the free plugin.
- **Verification:** Run calculations without a paid license and with Pro add-on absent.

### WPR-002 — Admin analytics sent before consent

- **Severity:** High
- **Status:** Hypothetical example (not a real confirmed issue)
- **Confidence:** N/A — example
- **Applicable policy:** [Guideline #7](https://developer.wordpress.org/plugins/wordpress-org/detailed-plugin-guidelines/#7-plugins-may-not-track-users-without-their-consent)
- **Current evidence:** `includes/class-telemetry.php:40` (imaginary path)
- **Trigger / reachability:** Plugin activation supposedly posts site URL and admin email by default.
- **Suggested fix:** Remove the automatic call or obtain separate affirmative consent before every eligible tracking send; accurately document destination, payload, trigger, Terms and Privacy links.
- **Verification:** Assert zero telemetry network requests on activation and after choosing No.

## Required tests

- [ ] Plugin Check and PHPCS/WPCS
- [ ] WordPress activation with WP_DEBUG enabled
- [ ] No-license and no-consent exercise

**Remember:** Every real report must list **all actually observed issues**, precise file/line evidence and suggested fixes. Historical email examples must not be copied as fresh findings.
