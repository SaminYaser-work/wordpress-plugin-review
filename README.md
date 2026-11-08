# WordPress.org Plugin Review

An agent skill that reviews WordPress plugins for WordPress.org submission and updates. It creates a Markdown report with findings, suggested fixes, and checks to run before submission.

Reviews keep plugin code read-only. For runtime checks, the skill enables debug logging in a disposable WordPress test site's `wp-config.php`, then restores the original settings unless you ask to keep them.

## Install with npx skills

```bash
npx skills add SaminYaser-work/wordpress-plugin-review --skill wordpress-plugin-review
```

Follow the prompts to choose which coding agents should use the skill. Installation applies to the current project by default.

To make the skill available across projects, install it globally:

```bash
npx skills add SaminYaser-work/wordpress-plugin-review --skill wordpress-plugin-review -g
```

See the [official Skills installation guide](https://github.com/vercel-labs/skills#install-a-skill) for more options.

## Use the skill

Ask your agent:

```text
Use wordpress-plugin-review to review /path/to/my-plugin for WordPress.org compliance.
```

You can also provide a plugin ZIP:

```text
Use wordpress-plugin-review to review /path/to/my-plugin.zip for WordPress.org compliance.
```

Use the ZIP you plan to submit when available, so the review covers what will ship.

## What it checks

- WordPress.org requirements relevant to your plugin.
- Security, privacy, and external services.
- Directly printed CSS/JS tags and dynamic output without context-appropriate late escaping, regardless of PHPCS suppressions.
- Free and paid feature boundaries.
- Hidden feature restrictions through settings mappings and add-on hooks.
- Public search data, guest identity fallbacks, and remote-font consent defaults.
- Whether advertised features match the plugin's behavior.
- Common plugin errors and packaging issues.
- New debug-log issues during activation, normal plugin use, and deactivation, with old entries kept separate.
- Declared WordPress/PHP requirements, safe startup checks, and PHP support versus functions, syntax, and bundled dependencies.

SVN and release administration are outside the review's scope.

## Your report

The skill creates `WORDPRESS_PLUGIN_REVIEW.md` in the reviewed plugin/project's existing `docs/` folder. If no `docs/` folder exists, it saves the report in that project's root. You can request a different output path.

For ZIP-only reviews, the ZIP's parent folder is the root. If you also provide the corresponding source folder, the skill uses that source root instead.

The report explains each finding, its priority, suggested fixes, and how to verify them. It also notes checks that could not be completed. See the [example report](examples/EXAMPLE_REPORT.md).

A review does not guarantee WordPress.org approval.
