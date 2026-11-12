# Static reader theme

The website is generated from this Skill's `themes/default/`. Preserve its existing white background, colors, typography, reading width, spacing, and chapter layout. Ordinary book production does not apply a different design system or translate interface strings. Change shared templates/scripts centrally rather than modifying only one generated book.

## Reader behavior

- Keep the chapter toggle and book title in the header; the title points to the reading entry. There is no top-level Home/Browse/Search navigation menu.
- The right-hand Find button opens a search popover beneath the upper-right header area. Search stays in the reading view and never replaces the chapter sidebar.
- Search uses the full-book script index. Reopening Find restores the previous query and results. Clicking a result closes the popover, opens the target paragraph, and highlights matches without opening the chapter sidebar.
- Clicking outside the popover or pressing Escape closes it without clearing the query. Queries are stored per book in sessionStorage; query parameters support cross-page continuation when storage is unavailable.
- The chapter sidebar starts closed. Desktop chapter navigation preserves its open/closed preference in the same browser tab; mobile chapter selection closes the sidebar, including same-page anchors. Resizing does not overwrite the desktop preference.
- Branch expansion is saved independently from sidebar visibility. Navigating to a chapter or reopening the sidebar expands the path to the current chapter and highlights it, while preserving other branch states. Continued scrolling within the same chapter does not repeatedly undo a user's manual collapse.

## Routes and resources

Preserve these actual files:

```text
index.html
read.html
search.html
read/<top-level-division-id>.html
assets/css/style.css
assets/js/reader.js
assets/js/reader-search.js
data/search_index.js
```

Nested divisions and paragraphs use page anchors. `search.html` is a compatibility entry to the same reader, not a separate main search screen. The classic `search_index.js` must load before the reader search UI; do not replace it with `fetch`-dependent JSON because direct-file reading must continue to work.

`textoria_build_site.py` renders templates from the canonical archive. Standard output uses static HTML/CSS/JavaScript and requires no backend or frontend framework. Avoid adding one for ordinary book production.

Deliver `read.html` as the primary reading file/URL. `index.html` remains the book introduction. The static theme currently does not render optional EPUB front matter or an EPUB download button. Deliver any generated EPUB through its actual file link in the conversation.

Validate affected pages, relative resources, index loading, result anchors, and interaction state after relevant theme changes. Pure theme updates do not require re-cleaning the body or reopening unchanged chapter/metadata reviews.
