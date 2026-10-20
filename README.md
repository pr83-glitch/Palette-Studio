![Palette Studio - Blender ANSI themes](assets/palette%20studio%20banner.png)

# Palette Studio

**Public hotfix: `1.2.1`.** Makes iTerm2 the default main source for new preferences and removes the empty-header palette-count message. Existing saved source choices and the optional Noctalia default are preserved. Includes the validated v1.2.0 workspace and theme improvements.

1000+ easy to customize themes in 1 click!

Turn the color schemes you already use in your terminal into full Blender themes.

![Palette Studio demo](assets/palette%20studio%20demo.gif)

Palette Studio pulls palettes from a few public theme repositories and rebuilds them as complete Blender UI themes: surfaces, borders, text, accents, viewport and node colors, the whole thing. Browse, preview, tweak, apply, and keep the ones you like.

> **Palette Studio is an unofficial, independently maintained modification of the original Palette add-on.**
> I really liked [nxstynate/palette](https://github.com/nxstynate/palette) - it was an awesome idea! But there were features I wish were there, so I started adding them, and eventually it turned into this. It is not affiliated with or endorsed by the original author.


**Disclaimer:** I did not make any of the color schemes here. They come from public terminal and editor theme repos, and I only made them nicer to live in.

---

## Installation

1. Download `add-on-palette-studio-v<version>.zip` from
   [Releases](../../releases/latest).
2. In Blender, go to **Edit > Preferences > Add-ons > Install** and select the zip.
3. Enable **Palette Studio**.
4. Save preferences

## Usage

The list starts empty, so the palettes need to be downloaded first.

1. Open the **Palette Studio** sidebar tab (<kbd>N</kbd>) and choose **Settings**.
2. Click **Download Palettes** and wait while the enabled sources are fetched.

*If you have multiple sources enabled, it will take a bit more time to load all the themes.*

Once themes are there:

1. Click a theme. Blender updates instantly.
2. Search, sort, and mark **Favorites** to narrow things down.
3. Selecting a theme applies it immediately. After restarting, the browser remembers your selection and the Palette page refills with its colors, but Blender's saved appearance is left untouched; the source palette is not re-applied. **Restore Blender Theme** returns to Blender's default theme and detaches the loaded palette and remembered selection, so later browser filters do not reapply it.

By default iTerm2-Color-Schemes is the main source. Enable the others on the **Settings** page to browse the full list (NvChad base46, base24, kitty-themes, alacritty-theme and the Noctalia community palettes). Noctalia is on by default too and also lists the color schemes already on your machine. Existing saved source choices are preserved when upgrading.

**Worth remembering:** **Save Preferences** keeps the current look after restarting Blender and remains below every page. **Save Palette Preset** on the Palette page stores the edited palette as a named Blender theme preset. **Restore Blender Theme** is in Settings.

Everything lives in **Edit > Preferences > Add-ons > Palette Studio**, and in the 3D Viewport sidebar (<kbd>N</kbd>) under the **Palette Studio** tab, so you can open it while you work.

### The workspace — v1.2.1

The complete UI is available in both Preferences and the sidebar. A current-palette hero card with a slim, single-row ANSI 0–7 preview sits above four icon task pages. The preview is read-only; use Palette to edit colors.

- **Browse** — a large always-visible search, All / Dark / Light filter pills, sort, a clickable favorite star on every palette row and the collapsible **Blender Presets** section at the bottom. The shuffle button picks a **Surprise Me** random palette. Use the **Palette** page to edit.
- **Palette** — a two-column color workbench: every one of the 20 live-editable slots is a large swatch tile with its label, grouped into Base Colors, Standard ANSI and Bright ANSI. **Show Hex** adds a hex field under each tile; **Quick Adjust** sits below the colors, starts expanded in new profiles and keeps saved fold choices. Reset, reload and Save Palette Preset remain available.
- **Finetune** (formerly Appearance) — five clickable **Look Style** tiles: Default (formerly Layered), Card, Outlined, Inset and Accent. Default is selected for new profiles. **Interface**, **Fonts & Text**, **Viewport** and **Animation** are boxed disclosures that start collapsed in new profiles. Fonts & Text contains Blender's native Interface Font picker and all text/font overrides. Viewport adds Static/Gradient/Vignette backgrounds, custom Gradient A/B picks and Swap A/B.
- **Settings** — boxed **Sources** and **Blender Theme** cards. Six remote sources sit in a two-column grid. **Download Palettes** and **Unload Palettes** stay together without a section heading; progress and Cancel appear during downloads. **noctalia sync (optional)** imports the current local Noctalia theme when that source is enabled. Restore Blender Theme is inside its card; native presets stay in Browse.

The current build maps Common > Animation > Channels to bright blue, Sub-channels to blue, Active Channel Group to bright green and Channel Group to green. Selected Dope Sheet/Timeline keyframe borders use the palette foreground at full opacity. The header preview shows exact palette colors and stays read-only.

### 1.2.1 — default source and header hotfix

- iTerm2-Color-Schemes replaces NvChad as the default main source for new preferences. Existing saved source choices are unchanged; Noctalia remains enabled by default.
- Removes the "1000+ palettes, ready to explore." message from the empty header.

### 1.2.0 — public release candidate

Promotes the tested 1.2.100-beta behavior to an untagged public candidate. Removes the Channel Text controls from Finetune, the source/apply footer from Browse, and extra Download/Noctalia section headings and messages from Settings. Saved preferences and download guards remain intact. Install through Blender; this candidate has not been published.

### Development history

The versions below describe earlier development builds, not the current package version.

### 1.2.99-beta — cleaner Palette page

Removes the Color Workbench header and slot count from the Palette page, so the Base Colors / ANSI groups start at the top. Quick Adjust stays expanded by default for new profiles, and saved fold choices still win.

### 1.2.98-beta — palette restore and animation colors

Restores the last selected palette into the Palette page after a restart without re-applying the theme. Common > Animation uses bright blue for Channels, blue for Sub-channels, bright green for Active Channel Group and green for Channel Group; the 4.5 per-editor channel groups follow the same greens. Selected Dope Sheet/Timeline keyframe borders use the foreground at alpha 1.0. The eight-color header preview now renders at full palette brightness while remaining read-only.

### 1.2.97-beta — slim palette preview

Matches the reference SOL build's single thin row of eight preview colors. Removes header color editing and the click-to-tweak hint; all 20 colors remain editable on Palette. Other UI and theme behavior are unchanged. Earlier ZIPs are preserved.

### 1.2.96-deep-beta — full UI rework

A visual and interaction pass over all four shared pages. The workspace now opens with a current-palette hero card and an editable 16-swatch ANSI ribbon, followed by larger icon navigation. Browse is search-first with filter pills, an eight-row list and a **Surprise Me** random-palette button. Palette becomes a two-column color workbench with optional hex fields. Finetune uses five Look Style tiles above boxed disclosures. Settings gains a two-column source grid and a Palette Downloads card. Saved page IDs, fold defaults, property identifiers and look-style behavior are unchanged.

### 1.2.95 — release candidate

Merged the validated viewport background and font-control work into `main`, preserving all earlier UI, Settings and Look Style improvements. Runtime version, footer and package filename are untagged. This is a release candidate, not a published release.

### 1.2.95-beta — Fonts & Text

Adds a collapsible Fonts & Text section in Finetune, containing Blender's own Interface Font file picker, Font Size, Shadow, global normal/selected text colors and channel normal/selected text colors. Moves these controls out of Interface and Animation without changing their saved values or behavior. Interface Font changes Blender's global UI font, including without a loaded palette; Save Preferences keeps it. The font file path is not part of a native theme preset.

### 1.2.94-beta — viewport backgrounds and Finetune

Renames Appearance to Finetune without changing saved page IDs. Viewport offers **Static** (default), **Gradient** and **Vignette**. Gradient A defaults to the palette Background; Gradient B defaults to palette Black (ANSI 0) and appears only in non-static modes. Each has a custom-color toggle; Swap A/B swaps the visible values and enables both overrides. These are viewport-only controls, independent of Interface Background 1/2 and Look Style surface shading. Palette moves Show Hex and Quick Adjust below all swatches, with Quick Adjust expanded by default for new profiles.

### 1.2.93-beta — simpler Settings

Removes the Location selector and local-folder picker; old Local selections switch to Remote at startup without deleting local files or repainting the saved theme. Sources starts expanded, Noctalia Sync and Blender Theme start collapsed. Download and Unload stay visible outside the sections; Unload is disabled during downloads and keeps its existing deletion confirmation. Save Preferences now uses a save icon instead of a settings icon.

### 1.2.92-beta — tool and scrollbar accents

Across all five Look Styles, Tool selected fill follows Primary at alpha 0.5, Scroll Bar Item follows Tertiary, and icon border strength is 0.0 for both dark and light palettes. Accent picks still update live; source palette values and icon category colors are unchanged.

### 1.2.91-beta — Browse stars and Default polish

Default selects Background for all three outlines, hides the navigation/tabs background (alpha 0.0), and uses palette Background/Foreground for Outliner Active/Selected Objects. All five styles get invisible Dope Sheet/Timeline keyframe borders, a Primary editor outline at alpha 0.1, and Text widget Item = Secondary at alpha 0.3, Selected Text = palette Foreground, Inner Selected = palette Background. Other styles keep their surface treatments; Outlined retains Foreground borders and opaque panels. Reselect Default to adopt its outline picks without rewriting saved settings at startup.

Favorites are clickable stars on each list row and do not load that palette. The separate Favorite and Edit Palette buttons are removed. Native Blender Presets move from Settings to the bottom of Browse, including when the library is empty. Version 1.2.91 is explicitly requested.

### 1.2.9-beta — transparent regions and Outlined borders (historical)

Rebuilt with Outlined panel backgrounds at alpha 1.0; toolbar/sidebar backgrounds remain transparent. Version kept at 1.2.9-beta as requested.

All five Look Styles use alpha 0.0 for toolbar/sidebar backgrounds. Selecting Outlined sets Appearance → Interface → Outline 2 and Outline 3 to Foreground. These remain editable picks; switching to another style keeps the picks. Existing saved settings are not rewritten at startup; reselect Outlined to use its new defaults.

### 1.2.8-beta — Layered becomes Default

Removes the original Default, Soft and Accent Wash. Layered is now named **Default** and is the initial style, with 0.5 Roundness and separated background/panel/control tones. Saved Layered and other surviving styles retain their selections. Removed selections migrate to the new Default without repainting the saved appearance at startup. Default no longer means unstyled surfaces or restoration of pre-style gradients.

### 1.2.7-beta — more Look Styles (historical)

Keeps Default and Card; removes Minimal and Shaded. Adds **Soft** (gentle rounded surfaces), **Outlined** (flat surfaces and crisp control edges), **Inset** (recessed panels), **Accent** (accent-tinted headers), **Layered** (three surface tones), and **Accent Wash** (subtly tinted card surfaces). All adapt to light/dark palettes and respect custom background/text and outline picks. Existing Card selections keep their meaning; removed styles fall back to Default without repainting the saved theme at startup.

### 1.2.6-beta — Look Styles (historical)

One dropdown in Appearance changes surface treatment without editing palette swatches. Default keeps the original appearance; Minimal is flat with subtle borders; Shaded adds gentle surface depth and control gradients; Card separates rounded panel surfaces from the background. Non-default styles use opaque sidebar backgrounds. Custom background/text colors and outline color picks remain intact. Selecting a style sets Roundness, which you can then tweak; returning to Default restores the earlier roundness and widget gradients. Save Preferences keeps the style choice, and Save Palette Preset stores the resulting Blender theme. Styles apply only with a palette loaded, never automatically over a detached native preset. Card changes appearance, not Blender's panel spacing.

### 1.2.5-beta — icon colors and search

The list search stays expanded, without a duplicate top search bar. Scene and Collection icons use palette blue, Object yellow, Object Data green, Modifier bright cyan, and Shading magenta. Light palettes disable icon borders; dark palettes retain full borders.

### 1.2.4-beta — minimal UI

Reduced repeated headings, decorative boxes and icons; simplified the current-palette header and footer. Advanced controls are revealed on demand rather than removed. Theme application, download behavior, palette values and saved preference identifiers are unchanged.

### 1.2.3-beta — review fixes

This development build fixes startup so restoring the palette list does not apply a theme; native preset selection detaches the old palette and cancels pending updates; the original Blender callback is restored on unregister. Cursor and selection use ANSI 15 and ANSI 4 respectively when those optional source colors are missing, while tertiary keeps its fallback. Global text overrides take precedence consistently. Remote and local indexes are separate (`theme_index.json` and `theme_index_local.json`), and switching modes can use a cached index without downloading. Lua comments are stripped during parsing, and staging requires a parseable palette. Downloads and local scans run asynchronously in a separate Blender process, polled by a timer; cancellation is cooperative and checked before index publication. Network cancellation may wait for the socket timeout or current scan; jobs are not hard-killed, and logs are retained in the cache job directory. Offline parser/cache (22 checks), subprocess (10 checks), color math, and all eight isolated Blender suites pass on 4.5.8 and 5.2.1. Both GUI screenshot harnesses pass; representative Configure screenshots were reviewed. Manual interaction/restart testing and real upstream downloads remain to be tested.

### What's new in 1.2.2

New in `1.2.2` (added as `1.2.2-beta`): icon borders render at full intensity again (`icon_border_intensity` is forced back to 1.0), and the camera passepartout is a persistent Appearance → Viewport color pick that defaults to black and never changes when another palette is applied. Under the hood the old palette-derived camera passepartout role was removed.

Browser search, sorting, favorites and source filters now preserve in-progress palette edits. Cached-list restoration is scheduled outside UI drawing, including empty lists. Font and shadow overrides restore each native text style independently; Reset to Original restores the captured UI scale even outside the slider's 1–2 range. Preset overwrites stage and validate the new XML and back up the old user preset before replacement. Parser/cache handling and source/design alpha propagation are also corrected, and a failed refresh now rolls the cached sources back instead of leaving the index pointing at deleted files. Isolated smoke, UI-contract and 16 audit regression checks pass on Blender 4.5.8 LTS and 5.2.1 LTS. Both GUI runs captured all workspace pages and Preferences without draw errors; representative screenshots were reviewed. The 1.2.2 release ZIP passes Blender's extension validator, and a scripted ZIP install/enable/disable/re-enable cycle passes on isolated 4.5.8 and 5.2.1 profiles. The user confirmed the beta stable in Blender; real network downloads and native Windows testing remain outstanding.

## Requirements

- Blender 4.5 or newer (4.5 LTS and 5.x both work)
- An internet connection for the first download

## Documentation

Full walkthrough of the workspace lives in [palette_studio/README.md](palette_studio/README.md).

## License

GPL-3.0-or-later, which is what Blender requires of add-ons that use bpy. Full text is in [LICENSE](LICENSE).

## Credits

- Original add-on ("Palette", © 2025 NXSTYNATE, GPL-3.0-or-later): [nxstynate/palette](https://github.com/nxstynate/palette)
- Palette Studio modifications and maintenance: **Pr83-Glitch** (2025-present)

Palette Studio is an unofficial community fork. NXSTYNATE's original copyright and license notices are preserved in the source; the changes made here are maintained separately by Pr83-Glitch.

## Theme sources

- [NvChad base46](https://github.com/NvChad/base46)
- [iTerm2-Color-Schemes](https://github.com/mbadolato/iTerm2-Color-Schemes) - on by default
- [tinted-theming base24](https://github.com/tinted-theming/schemes)
- [kitty-themes](https://github.com/kovidgoyal/kitty-themes)
- [alacritty-theme](https://github.com/alacritty/alacritty-theme)
- [Noctalia community palettes](https://github.com/noctalia-dev/community-palettes) (the Noctalia source also picks up the schemes in your own `~/.config/noctalia/colorschemes`)
Nothing is bundled with the add-on; the files are fetched and cached on your machine. Credit for every scheme goes to whoever made it, so check the repositories above for their licenses. I didnt create or own these schemes.

Each source is pinned to a reviewed upstream commit, so the downloaded sets are reproducible. Updating a source is a manual, reviewed change made in the add-on code.

Found a bug or have an idea? Open an issue. Including your Blender version and what you were doing helps a lot.
