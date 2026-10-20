# Palette Studio

**Public release candidate: `1.2.0`.** Not yet published. **Last published public release:** `1.1.0`.

A full workspace rework with a
current-palette hero card and a slim, read-only ANSI 0–7 preview, larger icon navigation,
search-first Browse with a **Surprise Me** random palette, a two-column color
workbench, Look Style tiles and boxed settings cards. The last selected palette
returns to the Palette page after a restart without repainting the saved theme.
Animation channels and selected Dope Sheet/Timeline keyframe borders follow the
requested palette colors. Header swatches stay read-only and render at full
palette brightness; use the Palette page to edit all 20 colors.

Turn the color schemes you already use in your terminal into full Blender themes.

Palette Studio pulls palettes from a few public theme repositories and rebuilds them as complete Blender UI themes: surfaces, borders, text, accents, viewport and node colors, the whole thing. Browse, preview, tweak, apply, and keep the ones you like.

> **This is my tweaked version of the original Palette add-on, and it is unofficial.**
>
> I really liked [nxstynate/palette](https://github.com/nxstynate/palette) - it was a great idea. But there were features I kept wanting, so I started adding them, and eventually it turned into this. If you want the original, go grab that one. This is just the version with the things I wanted. It is not affiliated with or endorsed by the original author.

I did not make any of the color schemes here. They come from public terminal and editor theme repos, and I only made them nicer to live in.

---

## Installing

1. Download `add-on-palette-studio-v<version>.zip` from the repository's **Releases** page.
2. In Blender, go to **Edit > Preferences > Add-ons > Install** and pick the zip.
3. Enable **Palette Studio**.

## Loading themes

The list starts empty, so the schemes need to be downloaded once.

1. Open the **Palette Studio** sidebar tab and choose **Settings**.
2. Click **Download Palettes** and wait while it fetches the enabled sources.

The list is remembered between sessions, and the last selected palette's colors return to the Palette page after a restart without re-applying the saved Blender appearance. **Settings** holds **Download Palettes** and **Unload Palettes**, directly below it. Unload clears the list and deletes downloaded files after confirmation. Palettes come from remote repositories; the Location selector and local-folder picker are no longer shown. Upgrading from Local mode switches to Remote without deleting your local palette files.

## Using it

1. Click a theme - it applies straight away.
2. Search, sort, and mark **Favorites** to narrow things down.
3. **Restore Blender Theme** goes back to Blender's default theme and clears the loaded palette and remembered selection, preventing an old palette from being reapplied by filtering.

**Save Preferences** below every page uses a save icon and keeps the current look after restart. **Save Palette Preset** on the Palette page saves the edited palette as a real Blender theme preset. **Restore Blender Theme** is in Settings → Blender Theme. Both the sidebar and Add-on Preferences expose the same controls.

---

## What is in it

### Browse
The main list. A large always-visible search sits above All Palettes / Dark / Light filter pills and the sort dropdown. Select a palette to apply it immediately. The shuffle button applies a random **Surprise Me** palette from the visible list. Search updates when you commit the text (Enter or defocus). Your sort mode and favorites are remembered. Each list row has a clickable favorite star and a Dark or Light tag. Clicking a star marks that row without selecting/loading its palette; Favorites First may reorder the list but preserves the active palette and edits. Use the **Palette** page to edit; there is no separate Edit Palette button. **Blender Presets** expands at the bottom of Browse, even when the library is empty, with the native selector and Add/Remove/Save actions. The current palette name and its ANSI colors stay visible in the hero card above the page buttons.

### Palette
The editor follows the palette selected in Browse. All 20 slots are large color tiles grouped into **Base Colors**, **Standard / ANSI 0-7**, and **Bright / ANSI 8-15**. Each tile has its own swatch and label; enable **Show Hex**, below the full color list, for editable hex fields. Quick Adjust is also below the colors and starts expanded in new profiles; existing saved fold choices remain respected. Every edit applies live without an Apply button. Slot numbers stay visible even when labels are shortened for narrow sidebars.

- **Quick Adjust** - expanded by default below the color list, with Hue, Saturation, Value and Alpha sliders that shift every *checked* ANSI slot at once. Background, foreground, cursor and selection are never touched. Tick a row to include it; unticked rows keep their colour. Hue works like Blender's own hue slider (0.5 = no change), Saturation and Value are multipliers (1.0 = no change), so the palette keeps its own contrasts. **Reset to Original** neutralises everything.
- **Reset to Original** restores the loaded theme's colors, re-ticks every slot, resets the sliders and restores Blender's initially captured UI scale. Other Finetune overrides are retained.
- **Reload Selected Palette** uses the existing load operator to reload the browser selection.

### Finetune (formerly Appearance)
Finetune controls are arranged into four collapsible groups: Interface, Fonts & Text, Viewport and Animation. Channel Text overrides are no longer shown; existing saved values remain compatible. New profiles start with these groups collapsed; existing saved fold states are preserved. Settings still update live and saved identifiers are unchanged.

**Look Style** is a row of clickable tiles above the groups and applies live to a loaded palette:

- **Default** — the former Layered style: distinct tones for editor background, panels and controls. Selected for new profiles, with Roundness 0.5. Selecting it sets Outline 1/2/3 to Background. Navigation/Tabs background alpha is 0.0; Outliner Active Object follows palette Background and Selected Objects follow palette Foreground.
- **Card** — distinct, opaque panel surfaces, softer corners and comparatively flat controls. This does not change Blender's panel spacing or layout.
- **Outlined** — flat surfaces, opaque panel backgrounds (alpha 1.0) and crisp control borders, with restrained corners. Selecting it sets Outline 2 and Outline 3 to Foreground; later manual picks still work and survive ordinary palette updates.
- **Inset** — darker, recessed panel surfaces and lighter controls.
- **Accent** — Card-like surfaces with restrained primary-accent tint on panel and editor headers.

All styles use flat controls without emboss, set toolbar/sidebar background alpha to 0.0 and derive restrained surface shades from the palette. Shades/tints adapt to light/dark backgrounds and are reduced if they would compromise source text contrast. Palette swatches, accents, viewport object/axis/animation colors and the viewport canvas are not recolored by surface styling. Custom Background 1/2 picks bypass generated RGB shades and tints, custom text wins, and outline picks remain editable. Selecting a style sets Roundness; manual tweaks persist until the next style selection. Default seeds all three outlines to Background; Outlined seeds Outline 2/3 to Foreground; the other styles leave picks unchanged. Default now means the Layered treatment, not restoration of the old appearance or native gradients. Save Preferences keeps the choice; Save Palette Preset captures the visible styling. Without a loaded palette, choosing a style only prepares the preference for the next palette—it does not repaint a native preset. The original Default, Soft and Accent Wash are removed in 1.2.8-beta; their saved selections migrate to the new Default without changing Blender's saved appearance at startup. Minimal and Shaded were removed earlier. Saved Layered selections keep their appearance and are now labeled Default.

**Interface**

- **Accent Colors** - pick which palette slot drives each of the three accents (Primary, Secondary, Tertiary). Defaults are Yellow, Cyan, and Selection.
- **Outline 1** - which palette slot draws the main widget outlines, borders and separators. Defaults to Background; selecting Default restores that pick.
- **Outline 2** - which palette slot draws Panel and Toolbar Item outlines at 0.3 alpha. Defaults to Background. It also covers scrollbar and radio-button outlines.
- **Outline 3** - which palette slot draws Regular, Tool, Toggle, Option, Box, List Item and Menu outlines at 0.3 alpha, plus the Value Slider outline at full source alpha. Defaults to Background; selecting Outlined sets it to Foreground.
- **Background 1** and **Background 2** - tick a row to override that surface with Blender's colour picker. Background 1 covers panels, editor backgrounds, headers and the striped list rows; Background 2 covers widget bodies, buttons and the other non-outline surfaces. Unticked stored defaults follow the palette background (Background 2 follows Background 1); Look Styles shade the applied UI surfaces while leaving these stored defaults unchanged. The viewport canvas has separate controls below.
- **Selected text** on tabs, toggles, radio buttons and list items follows Background 1 rather than the palette's foreground, so it stays readable on the accent fill behind it.
- **Text fields**, in all styles: Item follows Secondary at alpha 0.3, Selected Text follows palette Foreground, and Inner Selected follows the raw palette Background (not a shaded or custom surface). Global text overrides still win. Editor Outline follows Primary at alpha 0.1.
- **Tool selected fill** follows Primary at alpha 0.5; **Scroll Bar Item** follows Tertiary in all styles. Icon border strength is 0.0 for dark and light palettes; icon colors, opacity and saturation stay unchanged. Source ANSI alpha still multiplies the tool fill's design alpha.
- **Roundness** - one slider for every rounded corner in the UI.
- **UI Scale** - Blender's own Resolution Scale (Preferences > Interface), from 1.00 to 2.00. The slider displays the captured value clamped to 1–2 without changing Blender; **Reset to Original** restores the actual captured value, including values in Blender's wider 0.5–6 range.

**Fonts & Text**

- **Interface Font** - Blender's native file picker, exactly the same setting as Preferences → Interface → Text Rendering → Interface Font. It changes the global Blender UI font, works without a palette loaded, and is not overwritten by applying palettes. Use Save Preferences to keep it. An empty path uses Blender's default font; this path is a Blender preference, not part of a theme XML preset.
- **Text Color** and **Text Selected** - global overrides that repaint every text and selected-text color in Blender. Flip the **Custom** toggle off and the palette's colors come straight back.
- **Font Size** and **Shadow** - checkbox-enabled overrides. Unchecked groups are untouched on palette application; turning an override off restores each font style's own captured points/shadow values, rather than imposing one value on all styles. Global **Text Color** and **Selected Text** overrides sit alongside them.

**Viewport**

- **Background Type** - Static (default), Gradient (vertical) or Vignette (radial), using Blender's native theme background modes.
- **Gradient A** - always shown. With its custom toggle off, follows the palette Background. Toggle on to pick your own RGB color.
- **Gradient B** - shown only for Gradient/Vignette. With its custom toggle off, follows palette Black (ANSI 0). Custom picks survive switching back to Static and changing palettes.
- **Swap A / B** - shown with Gradient B. Swaps the current colors and enables both custom toggles so the swap is applied; untick either toggle to restore that endpoint's palette default.
- These controls update live with a palette loaded and do not edit source swatches or Interface Background 1/2. They set Themes → 3D Viewport → Theme Space → Gradient Colors, not the per-viewport World/custom background overrides. Save Preferences keeps the settings; Save Palette Preset captures the native appearance. Changes do not repaint detached native presets without a loaded palette.
- **Axis Colors** - X/Y/Z axis and gizmo colors. These reset to their defaults on every apply.
- **Selected Object** and **Active Object** - the selected and active object colors in the 3D viewport. **Theme Default** keeps the palette's own color, or pick any slot yourself.
- **Edge Width, Vertex Size, Face Dot Size, Outline Width** - viewport geometry, live.
- **Grid Color** - override the viewport grid.
- **Camera Passepartout** - a persistent color pick for the area outside the camera frame in the 3D viewport. It defaults to black (#000000) and deliberately does not follow the applied palette: what you pick stays, no matter how often you switch themes.

**Animation**

- **Playhead** and **Selected Keys** - the frame indicator and selected keyframes, in your palette's colors.
- **Keyframe borders** - Dope Sheet/Timeline normal and selected border alpha is 0.0 in every Look Style.

A couple of deliberate choices: in Edit Mode, unselected edges and vertex dots use ANSI 0, and bone fills use ANSI 7; these are the palette's own colors, not synthesized black/white. Panel and menu shadow strength is never touched, so that one is still yours.

### Settings
- **Sources** - a boxed card, expanded in new profiles, with six remote repositories in a two-column grid. Choose the sources to download. Once themes are loaded, the per-source switches act as live filters: turn one off and its themes hide, turn it back on and they return. Download again to fetch newly enabled sources.
- **Noctalia** - leave the toggle on and your own Noctalia color schemes (and the community palettes) appear in the browser, each as a Dark and a Light entry. **noctalia sync (optional)** imports and applies the colors Noctalia is showing right now. It reads the kitty theme Noctalia keeps rewriting (`~/.config/kitty/themes/noctalia.conf`), so it also works when the palette was generated from your wallpaper; if that file is missing it falls back to the scheme named in Noctalia's own settings. It is a one-time pull, so click it again after switching themes in Noctalia.

- **Download Palettes** and **Unload Palettes** - standalone buttons below Sources, even when every section is collapsed. Unload deletes downloaded files and is disabled while a download runs; cancellation and progress remain visible during downloads. There is no Cache section or separate downloads card.
- **Blender Theme** - a boxed card, initially closed. **Restore Blender Theme** returns to Blender's default theme and detaches the current palette. Native preset selection stays at the bottom of Browse.

### Save Palette Preset
On the Palette page. Load or edit a palette, click it, give it a name, and Blender saves it as a normal theme preset. If the name already exists, the dialog warns you and asks for overwrite confirmation. The native writer stages a UUID-named XML, validates it, and only then replaces the user preset. Existing presets are backed up under `~/Documents/Backup/Agent Backup/Palette Studio Presets`; a write, validation, backup or replacement failure preserves the original. Built-in and extension presets cannot be overwritten: choose a new name.

### 1.2.0 — public release candidate

Promotes the tested 1.2.100-beta behavior without changing theme application or saved preferences. Manifest, User-Agent, footer and release ZIP use untagged version 1.2.0. Not yet published.

### Development history

The versions below describe earlier development builds, not the current package version.

### 1.2.100-beta — tab cleanup

- Removed Channel Text controls from Finetune and the source/apply hint beneath Browse.
- Settings keeps unboxed Download/Unload buttons and an optional Noctalia sync button, without extra section headings or explanatory messages. Download progress and Cancel remain available.

### 1.2.99-beta — cleaner Palette page

Removes the Color Workbench header and slot count from the Palette page, so the
Base Colors / ANSI groups start at the top. Quick Adjust stays expanded by
default for new profiles, and saved fold choices still win.

### 1.2.98-beta — palette restore and animation colors

Restores the last selected palette into the Palette page after a restart without
re-applying the theme. Common > Animation maps Channels to bright blue,
Sub-channels to blue, Active Channel Group to bright green and Channel Group to
green; the Blender 4.5 per-editor channel groups use the same greens. Selected
Dope Sheet/Timeline keyframe borders use the palette foreground at full opacity.
The eight-color header preview uses a read-only color property, so it stays
non-editable but renders at full palette brightness.

### 1.2.97-beta — slim palette preview

The header now shows one thin row of eight read-only colors, matching the SOL
reference build. Header color editing and the click-to-tweak hint are removed.
All 20 colors remain editable on Palette; other UI and theme behavior stay unchanged.

### 1.2.96-deep-beta — full UI rework

A presentation-only workspace rework: current-palette hero card with an editable
ANSI color ribbon, larger icon navigation, search-first Browse with filter pills
and a **Surprise Me** random-palette button, two-column color tiles on Palette,
five Look Style tiles on Finetune, and boxed two-column Settings cards. Saved
page IDs, fold defaults, RNA identifiers, property callbacks and theme behavior
are unchanged.

### 1.2.95 — release candidate

Combines the validated 1.2.94 viewport backgrounds and 1.2.95 Fonts & Text work on `main`, with earlier UI, Settings and Look Style improvements retained. Manifest, User-Agent, UI footer and ZIP filename use untagged version 1.2.95. Not yet published.

### 1.2.95-beta — Fonts & Text

Adds Finetune → Fonts & Text, initially collapsed, with Blender's native Interface Font file selector and all existing font/text overrides. Moves Font Size, Shadow and global text colors out of Interface, and channel text colors out of Animation, without changing saved identifiers, callbacks or override precedence. The native Interface Font setting is global, works without a loaded palette, and persists through Blender's Save Preferences; it is not a per-palette override or a theme XML font path.

### 1.2.94-beta — viewport backgrounds and Finetune

Appearance becomes Finetune (saved page ID unchanged). Adds Static/Gradient/Vignette viewport background modes and independent custom A/B RGB overrides, defaulting to palette Background and Black (ANSI 0). B and Swap appear only for non-static modes; Swap enables both overrides. Unticked defaults follow palette edits, while custom colors persist across palettes/modes. Viewport colors no longer follow Interface Background 1. Moves Show Hex and Quick Adjust below all color rows, with Quick Adjust expanded by default for new profiles. Saved fold preferences remain intact.

### 1.2.93-beta — simpler Settings

Settings is split into Sources, Noctalia Sync and Blender Theme disclosures. Removes Location (Remote/Local) and the local-folder picker; old Local preferences migrate to Remote without touching local files or applying a theme at startup. Download and Unload are always visible, with Unload immediately below Download, keeping its running-job guard, deletion warning and confirmation. Removes the Cache disclosure. Save Preferences uses the save icon. Existing hidden local-mode fields/backend remain for saved-data compatibility, not as user-facing options.

### 1.2.92-beta — tool and scrollbar accents

All five styles now use Primary at alpha 0.5 for Themes → User Interface → Tool → Selected, Tertiary for Scroll Bar → Item, and Icons → Border intensity 0.0. These follow the live Primary/Tertiary picks; changing palettes keeps the same role bindings. Icon category colors and full icon opacity/saturation are unchanged.

### 1.2.91-beta — Browse stars and Default polish

Moves favorites to clickable stars on list rows, removes Browse's Favorite/Edit Palette buttons, and moves native Blender Presets from Settings to the bottom of Browse, including empty-library states. Star clicks preserve the active palette and edits even during Favorites First reordering. Default uses Background for Outline 1/2/3, transparent navigation/tabs backgrounds, and raw palette Background/Foreground for Outliner Active/Selected Objects. Reselect Default after upgrading to adopt its outline picks; startup does not overwrite saved picks or repaint the theme.

All styles now share keyframe-border alpha 0.0 in Dope Sheet/Timeline, editor-outline Primary at alpha 0.1, and Text Item = Secondary at alpha 0.3, Selected Text = palette Foreground, Inner Selected = palette Background. Outlined keeps Foreground Outline 2/3 and opaque panels; other styles keep their existing surface treatments. Global text overrides remain authoritative. Version 1.2.91 explicitly requested by the user.

### 1.2.9-beta — transparent regions and Outlined borders (historical)

Rebuilt at the user's request with Outlined panel/subpanel background alpha 1.0, while toolbar/sidebar backgrounds remain alpha 0.0. The version and ZIP filename remain 1.2.9-beta; the earlier ZIP was backed up before replacement.

Every Look Style now uses transparent toolbar/sidebar backgrounds (alpha 0.0), through unified Regions on Blender 5.2 and per-editor backgrounds on 4.5. Selecting Outlined sets Outline 2 and Outline 3 to Foreground. Manual outline picks remain editable and survive palette changes; other styles leave the picks unchanged. Saved Outlined users should reselect the style to adopt these defaults; startup does not rewrite saved picks or repaint the theme.

### 1.2.8-beta — Layered becomes Default

Removes the old Default, Soft and Accent Wash; renames Layered to Default and makes it the initial selection. Default uses separated surface tones and 0.5 Roundness. Surviving styles keep stable saved IDs. Removed selections migrate without startup theme writes; the old native-gradient/roundness restoration path is removed. Native Blender preset saving and restore remain available in Settings.

### 1.2.7-beta — more Look Styles (historical)

Keeps Default and Card and adds Soft, Outlined, Inset, Accent, Layered and Accent Wash. Minimal and Shaded are removed; saved Card values remain compatible, while removed selections fall back to Default without startup theme writes. Surface tints use the same contrast guard as shades and do not change the source palette or semantic colors.

### 1.2.6-beta — Look Styles (historical)

Default, Minimal, Shaded and Card surface treatments in Appearance. Pure UI-only shading preserves source palettes, semantic colors and custom picks. Repeated switches back to Default restore native widget gradients and earlier roundness. Native preset selection clears the old gradient baseline; style selection without a loaded palette leaves the native theme alone. Includes dark/light, contrast, overrides, preset XML and exact Default-restoration regressions.

### 1.2.5-beta — icon colors and search

The list search stays expanded, without a duplicate top search bar. Scene and Collection icons use palette blue, Object yellow, Object Data green, Modifier bright cyan, and Shading magenta. Light palettes disable icon borders; dark palettes retain full borders.

### 1.2.4-beta — minimal UI
Quieter header and navigation, fewer decorative boxes, compact Browse filters, optional hex fields and collapsible Quick Adjust. Appearance groups start collapsed in new profiles. Configure is now Settings, with expandable Cache and Blender Presets sections. Save Preset stays with palette editing; Restore Blender Theme moves to Settings. All existing features remain accessible.

### 1.2.3-beta — review fixes
Startup list restoration no longer applies a theme. Native preset reset detaches the palette, cancels pending work and restores state on unregister. Missing optional cursor/selection colors consistently fall back to ANSI 15/ANSI 4, preserving the tertiary fallback when optional data is absent; global text overrides have consistent precedence. Remote and local caches use separate `theme_index.json` and `theme_index_local.json` indexes, and switching modes can use cached data without a download. Lua comments are stripped, and only parseable palettes may be staged.

Remote downloads and local scans are asynchronous in a separate Blender process polled by a timer. Cancellation is cooperative and checked before index publication; network cancellation may wait for the socket timeout or current scan, and the process is not hard-killed. Job logs are retained in the cache job directory. Offline parser/cache (22 checks), subprocess (10 checks), color math, and all eight isolated Blender suites pass on 4.5.8 and 5.2.1. Both GUI screenshot harnesses pass; representative Configure screenshots were reviewed. Manual interaction/restart testing and real upstream downloads remain to be tested.

### 1.2.2-beta camera passepartout and icon borders

The camera passepartout (the dimmed area outside the camera frame in the 3D viewport) is no longer derived from the palette: it is a persistent Appearance → Viewport color pick that defaults to black and survives every palette apply, palette alpha tweaks and background overrides. Icon borders are forced back to full intensity (`icon_border_intensity` 1.0), where earlier builds muted them to 0. Regression coverage grew to 16 checks, including default black, a light-palette independence check, live custom picks and preference snapshots.

### 1.2.1-beta audit corrections
Browser search, sorting, favorites and source filters rebuild the list without discarding palette edits. Startup restores the cached browser list once outside UI drawing, even when filters yield an empty list; unavailable selections remain unselected. Noctalia source selection and configuration cache invalidation, YAML format detection, and rejection of files without recognized colors are corrected. Source alpha is combined with intentional per-field alpha without changing RGB. Downloads stage complete source snapshots, and validated JSON indexes are replaced atomically; the replaced copies are kept until the new index is published, so a failed refresh (including an index write failure) restores the previous cache. Isolated smoke, UI-contract and audit regression checks pass on Blender 4.5.8 and 5.2.1; the GUI harness captured all four pages, dark/light palettes and Preferences without draw errors, and representative screenshots were reviewed. Real network downloads and native Windows testing remain outstanding.

### 1.1.0 public baseline
Version **1.1.0** maps Common → Animation → Channels to the palette cyan and Sub-channels to bright cyan. It also keeps the Channels text mapping, remembered palette selection, and earlier widget-state mappings.

---

## Themes and sources

Palette Studio downloads from six places:

- [NvChad base46](https://github.com/NvChad/base46) - on by default
- [iTerm2-Color-Schemes](https://github.com/mbadolato/iTerm2-Color-Schemes)
- [tinted-theming base24](https://github.com/tinted-theming/schemes)
- [kitty-themes](https://github.com/kovidgoyal/kitty-themes)
- [alacritty-theme](https://github.com/alacritty/alacritty-theme)
- [Noctalia community palettes](https://github.com/noctalia-dev/community-palettes)

Noctalia is special: it is the only source that also reads files you already have. Every scheme in `~/.config/noctalia/colorschemes/<Name>/<Name>.json` shows up next to the downloaded ones, with a Dark and a Light entry each, and a scheme that exists in both places is listed once (from your local file).

That is plenty to get started. Nothing is bundled with the add-on; the files are fetched and cached on your machine. Credit for every scheme goes to whoever made it, so check the repositories above for their licenses. Neither the original Palette author nor I claim authorship of any of these schemes.

## Requirements

- Blender 4.5 or newer (4.5 LTS and 5.x both work)
- An internet connection for the first download

## License

GPL-3.0-or-later, which is what Blender requires of add-ons that use bpy. Use it, change it, share it, just keep derivatives under the same license. Full text is in [LICENSE](LICENSE).

## Credits

- Original add-on ("Palette", © 2025 NXSTYNATE, GPL-3.0-or-later): [nxstynate/palette](https://github.com/nxstynate/palette)
- Palette Studio modifications and maintenance: **Pr83-Glitch** (2025-present)

Palette Studio is an unofficial community fork. NXSTYNATE's original copyright and license notices are preserved in the source; the changes made here are maintained separately by Pr83-Glitch.

Found a bug or have an idea? Open an issue. Including your Blender version and what you were doing helps a lot.
