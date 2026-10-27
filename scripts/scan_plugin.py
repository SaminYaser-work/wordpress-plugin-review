#!/usr/bin/env python3
"""Read-only, stdlib WordPress.org pre-review TRIAGE scanner.

NOT an authoritative vulnerability/policy detector. Works on a WordPress plugin ZIP or
folder; never extracts/executes plugin files. Emits Markdown and optional JSON.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date
import html
import json
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile

MAX_FILES = 60000
MAX_TEXT_BYTES = 6_000_000
MAX_TOTAL_UNCOMPRESSED = 500_000_000
TEXT_EXT = {".php", ".js", ".jsx", ".ts", ".tsx", ".css", ".scss", ".html", ".htm", ".json", ".txt", ".md", ".xml", ".map", ".mjs", ".cjs"}
SKIP_DIRS = {".git", ".svn", ".hg", ".idea", ".vscode", "__pycache__"}  # SVN is skipped, not reviewed.
NETWORK_SCHEMES = re.compile(r"(?<![A-Za-z0-9])(?:https?:)?//([A-Za-z0-9.-]+)(?::\d+)?(?:[/\?#][^\s\"'<>]*)?", re.I)
WEB_HOST_IGNORES = {"wordpress.org", "developer.wordpress.org", "make.wordpress.org", "www.w3.org", "schema.org", "example.com", "localhost", "127.0.0.1", "getcomposer.org", "www.php.net"}

# IDs are stable in reports. These are REVIEW CANDIDATES; policy applicability is contextual.
CHECKS = {
    "TRIALWARE_GATE": ("Potential local Pro/license/trial/usage gate", "#5 / #6", "High", "Trace what local feature is restricted. If gated locally, make the included feature fully available or remove that premium implementation into a separately distributed add-on; document genuine SaaS truthfully."),
    "OUTBOUND_TELEMETRY": ("Possible telemetry/data transmission without proven consent", "#7; reviewer-observed external-service disclosure", "High", "Trace each outbound call and its payload, default consent, UI, and all triggers. Remove optional tracking or make it separately opt-in and off by default. Disclose actual services and data."),
    "REMOTE_ASSET": ("Remotely loaded non-service JS/CSS/image asset", "#7 / #8", "High", "Use WordPress core libraries or bundle licensed, non-service assets locally; only retain documented service/compatible-font exceptions where justified."),
    "UNDISCLOSED_SERVICE": ("External API call without evident service readme section", "#6 / #7; reviewer-observed external-service disclosure", "High", "Verify this is a real reachable service request, not a documentation string. Add a clear External services section with purpose, timing, transmitted data, account requirement, and direct Terms/Privacy URLs."),
    "REMOTE_INSTALL": ("Remote executable/add-on installation or updater path", "#8; Technical review concern", "High", "Inspect the code source and installation flow. Do not install code from a third-party server inside the wp-admin plugin workflow unless a permitted management-service exception is established."),
    "PLUGIN_ACTIVATION": ("Plugin installation/activation/deactivation action", "Technical review concern: changing active plugins", "High", "Require a separate, explicit user-initiated action and operation-specific capabilities (install_plugins/activate_plugins/deactivate_plugins). Prefer Requires Plugins for dependencies."),
    "REST_PUBLIC": ("REST route may expose data/actions publicly", "Technical review concern: REST API permissions", "High", "Read the entire route handler. Keep __return_true only for intentionally public safe content; protect non-public data/actions with appropriate capabilities."),
    "REST_MISSING_PERMISSION": ("REST route may lack permission_callback", "Technical review concern: REST API permissions", "High", "Declare a permission_callback appropriate to the operation; public routes should explicitly use __return_true."),
    "REST_VALIDATION_KEY": ("Unrecognized REST argument 'validation_callback'", "Technical review concern: validation/sanitization", "High", "Change the argument to validate_callback (or sanitize_callback as appropriate), validate/sanitize nested values and test malformed inputs."),
    "INPUT_TO_SINK": ("Possible unsanitized request/REST data written or rendered", "Technical review concern: input security", "High", "Trace data from source to sink, unslash and validate exact type/shape, sanitize each field before persistence and escape appropriately at final output."),
    "ECHO_UNESCAPED": ("Dynamic echo may lack context-appropriate escaping", "Technical review concern: escaping late", "Medium", "Inspect output context and all upstream code; use esc_html/esc_attr/esc_url or a wp_kses allowlist for expected HTML. Avoid escaping too early."),
    "CORE_BOOTSTRAP": ("Direct WordPress bootstrap/core loading", "Technical review concern: calling core loading files directly", "High", "Do not include wp-load/wp-config/wp-blog-header from the plugin. Use WordPress hooks, REST/AJAX or rewrite endpoints."),
    "CORE_INCLUDE": ("Non-once include of WordPress core admin helper file", "Technical review concern: calling core loading files directly", "Medium", "Confirm the helper is necessary, load once with require_once in an authorized WordPress context and call the relevant API immediately."),
    "PATH_FIXED": ("Fixed plugin-folder or admin URL path", "Technical review concern: portable plugin paths", "Medium", "Use plugins_url(relative, main_plugin_file), plugin_dir_url/path or admin_url/rest_url; verify under a renamed plugin directory."),
    "I18N_MISMATCH": ("Plugin translation text domain differs from directory slug", "Technical review concern: i18n text domain", "Medium", "Use the exact WordPress.org plugin slug as the text domain in plugin-owned strings and header; regenerate build files/catalogs."),
    "BUFFER_UNPAIRED": ("Potentially unclosed PHP output buffer", "Technical review concern: ob_start balancing", "Medium", "Trace every success/failure/early return and pair each ob_start with ob_get_clean/ob_end_clean/ob_end_flush in the same logical flow."),
    "DBDELTA_INVALID": ("Potentially invalid CREATE TABLE IF NOT EXISTS for dbDelta", "Technical review concern: clean activation/database schema", "Medium", "Use dbDelta-compatible CREATE TABLE syntax, proper $wpdb->prefix and charset/collation; verify clean install and schema upgrade."),
    "DEPRECATED_API": ("Deprecated / removed PHP function", "Technical review concern: PHP compatibility", "Medium", "Replace deprecated functionality with supported equivalents and test declared PHP versions."),
    "PDF_PUBLIC": ("Possible personal document/cache in public uploads", "#2 / #7; Technical review concern: private files", "High", "Verify HTTP access and contents; stream PDFs through authorized endpoints or keep them in truly inaccessible storage; protect/remove legacy cached files."),
    "CSS_GLOBAL": ("Broad selectors in potential admin stylesheet", "#11; Technical review concern: admin CSS leak", "Medium", "Check when the stylesheet is enqueued and scope selectors under a plugin container; load only on your screens unless this is a dashboard-restyling plugin."),
    "DIRECT_PHP": ("Executable template may allow direct PHP access", "Technical review concern: direct file access", "Medium", "For executable PHP include/view files, add a correct ABSPATH guard before executable statements; distinguish definition-only files."),
    "REVIEWER_COMMENT": ("Code comment addresses or instructs WordPress reviewers", "Technical review concern: reviewer-directed comments", "Medium", "Remove directions to reviewers from code; keep accurate engineering comments and explain disputed findings through normal review correspondence."),
    "RATING_BRANDING": ("External rating/testimonial branding needs verification", "#9 / #11 / #12 (only if applicable)", "Low", "Verify testimonial substantiation, location, consent and endorsement context; remove misleading or disallowed promotions, including compiled-asset leftovers."),
    "PACKAGING_FILE": ("Potentially unnecessary shell/build/test artifact shipped", "#2; Technical review concern: not permitted files", "Medium", "Remove unnecessary build scripts/caches/backups from the release ZIP using a packaging exclusion list; retain only legitimate runtime assets."),
    "FILENAME_PORTABILITY": ("Filename portability issue", "Technical review concern: filesystem compatibility", "Medium", "Rename case-colliding, trailing-space or unusual-space filenames; update references and test on case-insensitive filesystems."),
    "NO_README": ("readme.txt missing or empty in WordPress.org package", "Technical review concern: directory metadata and readme", "Medium", "Provide an accurate WordPress.org readme.txt, including free-feature descriptions and required external-service disclosures."),
}

@dataclass(frozen=True)
class Hit:
    check: str
    path: str
    line: int
    excerpt: str


def trimmed(value: str, limit: int = 240) -> str:
    return re.sub(r"\s+", " ", value).strip()[:limit]


def normalize_archive_path(path: str) -> str | None:
    raw = path.replace("\\", "/")
    p = PurePosixPath(raw)
    if p.is_absolute() or ".." in p.parts or not p.parts or raw.startswith("/"):
        return None
    return str(p)


def read_files(root: Path):
    """Return {relative_path: bytes}, skipped notes, and detected common ZIP root."""
    result = {}
    skipped = []
    paths = []
    zip_root = None
    if root.is_dir():
        for p in root.rglob("*"):
            if len(paths) > MAX_FILES:
                skipped.append(f"File count exceeds {MAX_FILES}; audit incomplete")
                break
            if p.is_symlink() or not p.is_file():
                continue
            rel = p.relative_to(root)
            if any(part in SKIP_DIRS for part in rel.parts):
                continue
            paths.append((str(PurePosixPath(*rel.parts)), p))
        for rel, p in paths:
            try:
                if p.stat().st_size > MAX_TEXT_BYTES:
                    skipped.append(f"Large file not read: {rel}")
                else:
                    result[rel] = p.read_bytes()
            except (OSError, PermissionError) as e:
                skipped.append(f"Unreadable: {rel}: {e}")
    elif root.is_file() and root.suffix.lower() == ".zip":
        with zipfile.ZipFile(root) as z:
            valid = []
            sizes = 0
            for entry in z.infolist():
                if entry.is_dir():
                    continue
                rel = normalize_archive_path(entry.filename)
                if rel is None:
                    skipped.append(f"Unsafe ZIP member name ignored: {entry.filename}")
                    continue
                parts = PurePosixPath(rel).parts
                if any(part in SKIP_DIRS for part in parts):
                    continue
                if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                    skipped.append(f"ZIP symlink ignored: {rel}")
                    continue
                sizes += entry.file_size
                if sizes > MAX_TOTAL_UNCOMPRESSED or len(valid) >= MAX_FILES:
                    skipped.append("ZIP size/file-count safety limit reached; audit incomplete")
                    break
                valid.append((rel, entry))
            if valid:
                common = {PurePosixPath(rel).parts[0] for rel, _ in valid if len(PurePosixPath(rel).parts) > 1}
                if len(common) == 1 and all(len(PurePosixPath(rel).parts) > 1 for rel, _ in valid):
                    zip_root = next(iter(common))
            for rel, entry in valid:
                key = rel[len(zip_root) + 1:] if zip_root else rel
                if entry.file_size > MAX_TEXT_BYTES:
                    skipped.append(f"Large file not read: {key}")
                else:
                    try:
                        result[key] = z.read(entry)
                    except (RuntimeError, EOFError, zipfile.BadZipFile) as e:
                        skipped.append(f"Unreadable ZIP member: {key}: {e}")
    else:
        raise ValueError("Pass a plugin directory or a .zip archive")
    return result, skipped, zip_root


def find_slug(files: dict[str, bytes], root: Path, explicit: str | None, zip_root: str | None) -> tuple[str, str]:
    if explicit:
        return explicit.strip(), "explicit --slug"
    if zip_root:
        return zip_root, "ZIP common top-level folder (verify WordPress.org slug)"
    if root.is_dir():
        return root.name, "directory name (verify WordPress.org slug)"
    return root.stem, "archive filename (verify WordPress.org slug)"


def is_plugin_owned(path: str) -> bool:
    return not re.search(r"(?:^|/)(?:vendor|vendor_prefixed|node_modules|third-party|third_party)/", path, re.I)


def add_hit(hits: set[Hit], check: str, path: str, line: int, excerpt: str):
    hits.add(Hit(check, path, max(1, line), trimmed(excerpt)))


def review(files: dict[str, bytes], slug: str):
    hits: set[Hit] = set()
    urls: dict[str, set[str]] = defaultdict(set)
    readme = next((data.decode("utf-8", errors="replace") for name, data in files.items() if name.lower() == "readme.txt" and "/" not in name), "")
    meta = {"main_plugin": "Not resolved", "plugin_name": "Unknown", "readme_present": bool(readme)}
    php_re = re.compile(r"\.php$", re.I)
    for path, binary in files.items():
        if path.lower().endswith(".php"):
            first = binary[:6000].decode("utf-8", errors="replace")
            if re.search(r"(?m)^\s*\*?\s*Plugin Name\s*:", first) and meta["main_plugin"] == "Not resolved":
                meta["main_plugin"] = path
                m = re.search(r"(?m)^\s*\*?\s*Plugin Name\s*:\s*(.+)", first)
                if m:
                    meta["plugin_name"] = m.group(1).strip()
    if not readme:
        add_hit(hits, "NO_README", "readme.txt", 1, "WordPress.org readme.txt not found at package root")
    for path, binary in sorted(files.items()):
        pure = PurePosixPath(path)
        if path.lower().endswith((".sh", ".bak", ".old", ".orig", ".patch", ".phar")) or any(x in pure.parts for x in ("node_modules", "tests", "test", "cache", "tmp")):
            if path.lower().endswith((".sh", ".bak", ".old", ".orig", ".patch", ".phar")):
                add_hit(hits, "PACKAGING_FILE", path, 1, "Potential build/test/executable artifact in distributed plugin")
        if any(c.isspace() for c in pure.name) or pure.name.endswith("."):
            add_hit(hits, "FILENAME_PORTABILITY", path, 1, "Filename contains whitespace or ends in '.'")
        if pure.suffix.lower() not in TEXT_EXT:
            continue
        text = binary.decode("utf-8", errors="replace")
        lines = text.splitlines()
        lowerpath = path.lower()
        owned = is_plugin_owned(path)
        for line_no, line in enumerate(lines, 1):
            strip = line.strip()
            # URL inventory for all reachable-or-unreachable code; analyst classifies it.
            for mm in NETWORK_SCHEMES.finditer(line):
                host = mm.group(1).lower().strip(".")
                if host not in WEB_HOST_IGNORES and not host.endswith(".wordpress.org"):
                    urls[host].add(f"{path}:{line_no}")
            if not owned and "review" not in path.lower():
                # Bundled vendors still get license/remote-url inventory + filenames;
                # first-party checks on vendored internals would create large noisy false positives.
                continue
            if re.search(r"(?:\b|_)(?:is_pro|is_pro_feature|is_premium|is_pro_or_previewing|pro_feature|license_(?:valid|active|status)|trial_(?:expired|days)|upgrade_required|feature_locked|free_(?:tier|limit)|max_(?:campaigns|rules)|quota)\b", line, re.I) or re.search(r"(?:upload rate limit|limit exceeded|per.ip upload)", line, re.I):
                add_hit(hits, "TRIALWARE_GATE", path, line_no, line)
            if re.search(r"(?:durbin|telemetry|analytics|tracking|deactivation.feedback|ipinfo\.io)", line, re.I) and any(x in text for x in ("wp_remote_", "fetch(", "axios.", "XMLHttpRequest", "sendBeacon", "curl_")):
                add_hit(hits, "OUTBOUND_TELEMETRY", path, line_no, line)
            if re.search(r"(?:cdn\.jsdelivr\.net|unpkg\.com|cdnjs\.cloudflare\.com|fonts\.cdnfonts\.com|\.(?:js|css|png|jpe?g|gif|svg|woff2?)(?:\?|['\"`]|$))", line, re.I) and re.search(r"(?:https?:)?//", line):
                if re.search(r"(?:wp_enqueue_(?:script|style)|<script|<link|@import|(?<!\w)src\s*=|url\(|\.(?:js|css|png|jpe?g|gif|svg|woff2?)|import\s*\()", line, re.I):
                    add_hit(hits, "REMOTE_ASSET", path, line_no, line)
            if re.search(r"(?:wp_remote_(?:get|post|request)|\bfetch\s*\(|axios\.(?:get|post|request)|sendBeacon|XMLHttpRequest)", line, re.I) and re.search(r"(?:https?:)?//[A-Za-z0-9.-]+", line):
                service_hosts = [m.group(1).lower() for m in NETWORK_SCHEMES.finditer(line)]
                active_external = [h for h in service_hosts if h not in WEB_HOST_IGNORES and not h.endswith('.wordpress.org')]
                if active_external and not re.search(r"(?i)(?:^|\n)\s*(?:==|##)\s*External services\s*(?:==|\n)", readme):
                    add_hit(hits, "UNDISCLOSED_SERVICE", path, line_no, line)
            if re.search(r"(?:Plugin_Upgrader|install_plugin|activate_plugin\s*\(|deactivate_plugins\s*\(|\->install\s*\()", line, re.I):
                add_hit(hits, "PLUGIN_ACTIVATION", path, line_no, line)
            if re.search(r"(?:download_url\s*\(|upgrader\->install\(|install_package\(|file_get_contents\s*\(\s*['\"]https?:)", line, re.I) and re.search(r"(?:\.zip|download|install|remote|https?:)", text[max(0, text.find(line)-100):text.find(line)+300], re.I):
                add_hit(hits, "REMOTE_INSTALL", path, line_no, line)
            if re.search(r"['\"]validation_callback['\"]\s*=>", line):
                add_hit(hits, "REST_VALIDATION_KEY", path, line_no, line)
            if re.search(r"\b(?:require|include)(?:_once)?\b.*(?:wp-load\.php|wp-config\.php|wp-blog-header\.php)", line, re.I):
                add_hit(hits, "CORE_BOOTSTRAP", path, line_no, line)
            elif re.search(r"\binclude\s*\(?\s*ABSPATH\b.*wp-admin/includes/", line, re.I):
                add_hit(hits, "CORE_INCLUDE", path, line_no, line)
            if re.search(r"plugins_url\s*\(\s*['\"][^'\"]*/assets/", line, re.I) and "__FILE__" not in line:
                add_hit(hits, "PATH_FIXED", path, line_no, line)
            if re.search(r"(?:/wp-admin/admin-ajax\.php|wp-content/plugins/[A-Za-z0-9_-]+|['\"]/?\?wc-ajax=)", line, re.I):
                add_hit(hits, "PATH_FIXED", path, line_no, line)
            if re.search(r"(?:libxml_disable_entity_loader|create_function|\beach\s*\(|\butf8_encode\s*\()", line):
                add_hit(hits, "DEPRECATED_API", path, line_no, line)
            if re.search(r"\b(?:Review note|reviewer note|do not flag|Dear WordPress reviewer|ignore (?:this )?review finding)\b", line, re.I):
                add_hit(hits, "REVIEWER_COMMENT", path, line_no, line)
            if re.search(r"Trustpilot|440\+\s*Reviews", line, re.I):
                add_hit(hits, "RATING_BRANDING", path, line_no, line)
            if php_re.search(path) and re.search(r"\becho\s+(?:\$|\(?\s*\$_(?:GET|POST|REQUEST))", line) and not re.search(r"\becho\s+(?:esc_html|esc_attr|esc_url|wp_kses|absint|intval|wp_json_encode)\s*\(", line):
                add_hit(hits, "ECHO_UNESCAPED", path, line_no, line)
            if path.endswith(".css") and ("admin" in lowerpath or "backend" in lowerpath):
                if re.match(r"\s*(?::root|body|img|input|textarea|a|button|select)\s*[{,:]", line, re.I):
                    add_hit(hits, "CSS_GLOBAL", path, line_no, line)
            if ("CREATE TABLE IF NOT EXISTS" in line.upper()) and re.search(r"\bdbDelta\s*\(", text, re.I):
                add_hit(hits, "DBDELTA_INVALID", path, line_no, line)
        # A few near-source/near-sink candidates, never treated as proven bugs.
        if owned and php_re.search(path):
            if re.search(r"(?:\$_(?:POST|GET|REQUEST|COOKIE)|\$request->get_param\s*\()", text) and re.search(r"\b(?:json_decode|update_option|update_data|update_post_meta|wp_insert_post|echo)\s*\(", text):
                # Find a relevant data source line; full trace required before claiming unsanitized input.
                for i, line in enumerate(lines, 1):
                    if "json_decode" in line and re.search(r"(?:POST|GET|REQUEST|builder|payload|param)", " ".join(lines[max(0, i-12):i+4]), re.I):
                        add_hit(hits, "INPUT_TO_SINK", path, i, line)
                    elif re.search(r"\$request->get_param\s*\(", line) and re.search(r"(?:update_data|update_option|update_post_meta)", " ".join(lines[i:min(len(lines), i+13)])):
                        add_hit(hits, "INPUT_TO_SINK", path, i, line)
            # Approximation: match within a single route configuration, never assert public exposure.
            for m in re.finditer(r"\bregister_rest_route\s*\(", text):
                excerpt = text[m.start():m.start()+1600]
                cutoff = re.search(r"\bregister_rest_route\s*\(", excerpt[20:])
                if cutoff:
                    excerpt = excerpt[:20+cutoff.start()]
                line_no = text.count("\n", 0, m.start())+1
                if "permission_callback" not in excerpt:
                    add_hit(hits, "REST_MISSING_PERMISSION", path, line_no, excerpt[:200])
                elif re.search(r"permission_callback\s*['\"]?\s*=>\s*['\"]__return_true", excerpt):
                    add_hit(hits, "REST_PUBLIC", path, line_no, excerpt[:240])
            if "ob_start(" in text or "ob_start (" in text:
                opens = list(re.finditer(r"\bob_start\s*\(", text))
                closes = list(re.finditer(r"\b(?:ob_get_clean|ob_end_clean|ob_end_flush|ob_get_flush)\s*\(", text))
                if len(opens) > len(closes):
                    for m in opens:
                        ln = text.count("\n", 0, m.start())+1
                        add_hit(hits, "BUFFER_UNPAIRED", path, ln, lines[ln-1])
            if re.search(r"\bwp_upload_dir\s*\(", text) and re.search(r"(?:\.pdf|\.zip|attachment|document|invoice|packing.slip)", text, re.I):
                for i, line in enumerate(lines, 1):
                    if re.search(r"\bwp_upload_dir\s*\(", line):
                        add_hit(hits, "PDF_PUBLIC", path, i, line)
            if re.search(r"(?:^|/)(?:views?|templates?|parts?)/", path, re.I):
                stripped = re.sub(r"/\*.*?\*/", "", text[:1000], flags=re.S)
                if re.search(r"\b(?:echo|include|require|new\s+[A-Za-z_]|\$[A-Za-z_]+\s*\(|\?>\s*<)", stripped) and not re.search(r"defined\s*\(\s*['\"]ABSPATH['\"]\s*\)", stripped):
                    add_hit(hits, "DIRECT_PHP", path, 1, trimmed(stripped[:170]))
        if owned and path.lower().endswith((".php", ".js", ".jsx", ".ts", ".tsx")):
            # Literal gettext domain approximation (first two arguments must be simple quoted strings).
            pattern = re.compile(r"(?<![A-Za-z0-9_])(?:__|_e|_x|_n|esc_html__|esc_attr__|esc_html_e|esc_attr_e)\s*\(\s*(['\"])(?:\\.|(?!\1).){0,250}?\1\s*,\s*(['\"])([A-Za-z0-9_-]+)\2", re.S)
            for m in pattern.finditer(text):
                dom = m.group(3)
                if slug and dom != slug and dom not in ("default", "woocommerce", "elementor", "wordpress", "buddypress", "easy-digital-downloads"):
                    ln = text.count("\n", 0, m.start())+1
                    add_hit(hits, "I18N_MISMATCH", path, ln, f"Translated string uses domain '{dom}' rather than '{slug}'")
        # Header mismatch is direct and independent of heuristic parsing.
        if path == meta["main_plugin"]:
            mm = re.search(r"(?m)^\s*\*?\s*Text Domain\s*:\s*(\S+)", text[:6000])
            if mm and slug and mm.group(1) != slug:
                add_hit(hits, "I18N_MISMATCH", path, text.count("\n", 0, mm.start())+1, mm.group(0))
    folded: dict[str, str] = {}
    for name in files:
        fold = name.casefold()
        if fold in folded and name != folded[fold]:
            add_hit(hits, "FILENAME_PORTABILITY", name, 1, f"Case-insensitive filename collision with {folded[fold]}")
        folded[fold] = name
    return sorted(hits, key=lambda h: (h.check, h.path, h.line)), {k: sorted(v) for k,v in sorted(urls.items())}, meta, readme


def escape_md(s: str) -> str:
    return s.replace("|", "\\|").replace("`", "'").replace("\n", " ")


def render_report(root: Path, slug: str, slug_source: str, hits: list[Hit], urls: dict[str, list[str]], meta: dict, readme: str, skipped: list[str]) -> str:
    groups: dict[str, list[Hit]] = defaultdict(list)
    for h in hits:
        groups[h.check].append(h)
    counts = defaultdict(int)
    for check in groups:
        counts[CHECKS[check][2]] += 1
    out = [
        f"# WordPress.org Plugin Review — {meta['plugin_name']}", "",
        "> **Preliminary static triage only — NOT a completed human/AI or runtime review.** All findings below are **review candidates**, not established policy violations. A reviewer must trace reachable code paths, confirm applicability, and validate fixes before submission.", "",
        "## Review metadata", "",
        f"- **Source scanned:** `{escape_md(str(root))}`",
        f"- **Directory slug used:** `{escape_md(slug)}` ({escape_md(slug_source)})",
        f"- **Main plugin file:** `{escape_md(meta['main_plugin'])}`",
        f"- **Date:** {date.today().isoformat()}",
        "- **Methods:** read-only lexical/code-pattern triage and URL inventory; no WordPress/PHP execution, no Plugin Check or PHPCS", "",
        "## Candidate summary", "",
        f"- **Distinct review categories with hits:** {len(groups)}",
        f"- **Hit locations:** {len(hits)}",
        f"- **Grouped High candidates:** {counts['High']}; **Medium:** {counts['Medium']}; **Low:** {counts['Low']}",
        "- **Confirmed blockers:** Not determined; complete an evidence-based review before assigning a verdict.", "",
        "## Candidate issues (verify before filing as confirmed)", "",
    ]
    if not groups:
        out.extend(["No candidate patterns found by this scanner. **This is not a clean bill of health**; inspect plugin features, services, security and runtime manually.", ""])
    for j, (code, locs) in enumerate(sorted(groups.items(), key=lambda k: ({"High":0,"Medium":1,"Low":2}[CHECKS[k[0]][2]], k[0])), 1):
        title, rule, sev, fix = CHECKS[code]
        out.extend([
            f"### CAND-{j:03d} — {title}", "",
            f"- **Scanner ID:** `{code}`",
            f"- **Status / confidence:** Needs manual verification / Low (lexical finding only)",
            f"- **Potential severity if confirmed:** {sev}",
            f"- **Rule / practice:** {rule}",
            f"- **Matched locations:** {len(locs)}", "",
            "**Locations and evidence:**", "",
        ])
        for hit in locs:
            out.append(f"- `{escape_md(hit.path)}:{hit.line}` — `{escape_md(hit.excerpt)}`")
        out.extend(["", f"**Suggested fix if confirmed:** {fix}", "", "**Retest:** Verify the full containing function, request entry point, permission/consent conditions, and an actual runtime path as applicable.", ""])
    out.extend(["## External host inventory (all string occurrences; NOT proof of network traffic)", "", "| Host | String locations | Readme mention |", "|---|---|---|"])
    if urls:
        for host, locations in urls.items():
            mentioned = "yes (literal only)" if host.lower() in readme.lower() else "not found (check service name)"
            loclist = ", ".join(f"`{escape_md(v)}`" for v in locations)
            out.append(f"| `{escape_md(host)}` | {loclist} | {mentioned} |")
    else:
        out.append("| No http(s) host strings detected | — | — |")
    out.extend(["", "**For actual external services only:** determine operator, purpose, trigger, request/response data, opt-in state, account requirement, accurate `== External services ==` disclosure, and verified direct Terms/Privacy links. Exclude static docs links and unused strings from real-service counts.", "", "## Required manual review before submission", "", "- [ ] Trace all Pro/license/trial/quantity gating to reachable free-code functionality; compare every free readme/FAQ/screenshot claim to working code.", "- [ ] Verify each PHP and JS network call, payload, consent and disclosure; inspect compiled assets/source maps and runtime traffic.", "- [ ] Trace REST routes, AJAX handlers and plugin installation actions for precise capabilities and nonces.", "- [ ] Check JSON/REST arg schemas, input validation, SQL, late escaping and private file outputs.", "- [ ] Check executable templates, core includes, output buffers, install/upgrade DB schemas, paths, i18n and filename portability.", "- [ ] Run Plugin Check and PHPCS/WPCS where available, review false positives, and record exact output.", "- [ ] Test in disposable WordPress with WP_DEBUG enabled, including no-license/free and opt-out states.", "- [ ] Confirm publication ZIP contains the runtime assets/source required and no unnecessary or sensitive files.", "", "## Exclusions and limitations", "", "- SVN commits, trunk/tags, version bumps and release correspondence are **out of scope**.", "- Lexical matches are not proof of reachability, intent, authorization, privacy violation or missing functionality.", "- Reviewer historical case examples are for pattern recognition only, not findings in this plugin."])
    if skipped:
        out.extend(["", "### Files not fully inspected / safety limits", ""] + [f"- {s}" for s in skipped])
    out.extend(["", "## Primary references", "", "- [Detailed Plugin Guidelines](https://developer.wordpress.org/plugins/wordpress-org/detailed-plugin-guidelines/)", "- [WordPress.org Common Issues](https://developer.wordpress.org/plugins/wordpress-org/common-issues/)", "- [Plugin Check](https://wordpress.org/plugins/plugin-check/)", "- `references/reviewer-cases.md` in this skill (historical WordPress.org emails; reviewer messages only)", ""])
    return "\n".join(out)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("plugin", type=Path, help="WordPress plugin ZIP or directory")
    p.add_argument("--slug", help="Exact WordPress.org directory slug (recommended)")
    p.add_argument("--out", type=Path, default=Path("WORDPRESS_PLUGIN_REVIEW.md"), help="Markdown report output path")
    p.add_argument("--json", type=Path, help="Optional complete machine-readable candidate inventory")
    args = p.parse_args(argv)
    try:
        files, skipped, zip_root = read_files(args.plugin)
    except (ValueError, OSError, zipfile.BadZipFile) as e:
        p.error(str(e))
    if not files:
        p.error("No readable plugin files found")
    slug, slug_source = find_slug(files, args.plugin, args.slug, zip_root)
    hits, urls, meta, readme = review(files, slug)
    report = render_report(args.plugin, slug, slug_source, hits, urls, meta, readme, skipped)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps({"plugin":str(args.plugin), "slug":slug,"slug_source":slug_source,"metadata":meta,"hits":[asdict(x) for x in hits],"hosts":urls,"skipped":skipped}, indent=2), encoding="utf-8")
    print(f"Wrote {args.out} — {len(hits)} candidate locations across {len({h.check for h in hits})} categories. NOT a full review.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
