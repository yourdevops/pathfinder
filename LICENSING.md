# Licensing

Pathfinder DevSSP is licensed under the GNU Affero General Public License v3.0
or later (AGPL-3.0-or-later). See [LICENSE](LICENSE) for the full text.

## Plugins (Apache-2.0)

The entire `plugins/` directory is licensed under the Apache License 2.0.
This includes the plugin interface, autodiscovery, and all bundled plugin
implementations. Third-party plugin authors may use any license of their choice.

## Vendor Code

Files under `theme/static/js/vendor/` are copied from npm packages during
`npm run build` (or `npm run dev`) and are not checked into the repository.
They retain their original upstream licenses:

| File | License |
|------|---------|
| `alpine-csp.js` | MIT (Alpine.js) |
| `alpine-persist.js` | MIT (Alpine.js) |
| `htmx.js` | 0BSD (HTMX) |
| `htmx-ext-ws.js` | 0BSD (HTMX) |
