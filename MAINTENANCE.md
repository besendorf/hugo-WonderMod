# Maintenance and hardening

This fork starts from Wonderfall/hugo-WonderMod `3b0ee00eb05135a162fdb83de65576b968bab4f0`.
PaperMod was reviewed through `118119693d8b5ac211b939775678310973bcb232` on
28 October 2026. This is a selective port, not a full upstream merge.

## Adapted upstream changes

- Hugo's current template paths (`_partials`, `_shortcodes`, `_markup`, root page
  templates), following PaperMod `87de3fb024` / PR #1858.
- Current language properties and a minimum Hugo version of 0.158.0, following
  `a5d59c7d44` / PR #1884. Removed obsolete site.Author / site.Social fallbacks.
- Local page/global image resolution and image render hooks; WebP support and
  avoiding redundant global image lookup (`72615b6d49`, `f163fb1dc0`,
  `8919e487b5`, `5f157eba7a`). Cover links retain WonderMod's same-tab behavior.
- Current OpenGraph / Twitter metadata and page-image helper, including proper
  locale, escaping and optional `social.fediverse_creator`.
- Text-node search rendering, debouncing, error handling and configurable result
  limits, based on upstream's current fastsearch.js. SVG icons also use DOM APIs.
- Keyboard focus outlines (`730ab0de35`), accessible theme-toggle labeling,
  ancestor-based breadcrumb navigation, ISO date tooltips (`969bebdc56`) and
  natural post-metadata wrapping (`b8cdf95eb2`).
- ToC parsing for multiline headings (`17bf01d323`) and local template variables
  instead of Scratch state. The side ToC and automatic wide-screen opening remain.
- `rssExclude` feed filtering (`50745e5e2f`), adapted to the Atom feed.
- Scroll updates are passive and limited to one animation frame, following
  `6be1e9170c`, while retaining external JavaScript.

Additional hardening: serialize complete JSON-LD objects with Hugo's default
HTML escaping; render code-copy labels as text, keep their buttons keyboard/touch accessible and exclude Chroma line numbers; tolerate unavailable localStorage;
check optional DOM elements; retain feed XML escaping; remove the obsolete analytics
hook. Footer scripts are rendered per page so language-specific copy labels cannot
be cached from a different language.

## Deliberately retained

- External executable JavaScript and external no-JavaScript stylesheets.
- Local, fingerprinted scripts/styles with integrity attributes by default.
- Build-time Chroma highlighting; no Highlight.js or runtime highlighting.
- Usable navigation and readable content without JavaScript, CSS mobile menu,
  side ToC, reading progress bar and Atom output.
- No automatic third-party analytics or theme asset requests. The optional
  `youtube` shortcode still uses youtube-nocookie.com and requires explicit
  permission in a site's CSP; it is not a no-request or click-to-load embed.

PaperMod's inline head/footer scripts, inline fallback styles, `data-theme`/CSS
redesign and optional llms.txt/audio/video features were not imported. Native
fragment navigation remains; the upstream focus fix for its custom JavaScript
scroll handler is unnecessary because WonderMod does not use that handler.

## Updating a site

Move site overrides from `layouts/partials` to `layouts/_partials`, from
`layouts/shortcodes` to `layouts/_shortcodes`, and from `layouts/_default` to
`layouts`. Replace `template "partials/..."` calls with `partial "..."` calls.
Site overrides still need their own review; updating a submodule does not replace them.

The theme does not impose a universal CSP. Configure a policy appropriate to the
site, and enforce it at the host where possible. A meta policy is an option on
GitHub Pages, but cannot enforce frame-ancestors, sandbox or reporting directives.
A policy must precede every resource. Do not add unsafe-inline or unsafe-eval.

## Validation

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tests/check_fixture.py
python3 scripts/check_security.py /path/to/built/site --origin https://example.org
```

`HUGO_BIN` can select the Hugo executable for `check_fixture.py`. CI checks both
0.158.0 and 0.167.0. The fixture exercises the theme without any besendorf.org
overrides, including malicious title text, JSON-LD, local PNG/WebP images,
relative image query/fragment handling, code highlighting, search, archive,
taxonomies, side ToC and escaped full-content Atom entries. The resource audit
intentionally rejects third-party embeds; sites choosing to add one need an
explicit, reviewed exception rather than loosening all asset sources.
