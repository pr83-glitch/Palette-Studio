# Palette Studio

**Version `1.2.2`.** Adds Blender 5.3 support, Restore Previous Theme and several fixes (see the 1.2.2 notes below). Builds on 1.2.1, where iTerm2 became the default main collection for new preferences; existing saved source choices and the optional Noctalia default are unchanged.

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

All styles use flat controls without emboss, set toolbar/sidebar background alpha to 0.0 and derive restrained surface shades from the palette. Shades/tints adapt to light/dark backgrounds and are reduced if they would compromise source text contrast. Palette swatches, accents, viewport object/axis/animation colors and the viewport canvas are not recolored by surface styling. Custom Background 1/2 picks bypass generated RGB shades and tints, custom text wins, and outline picks remain editable. Selecting a style sets Roundness; manual tweaks persist until the next style selection. Default seeds all three outlines to Background; Outlined seeds Outline 2/3 to Foreground; the other styles leave picks unchanged. Default now means the Layered treatment, not restoration of the old appearance or native gradients. Save Preferences keeps the choice; Save Palette Preset captures the visible styling. Without a loaded palette, choosing a style only prepares the preference for the next palette—it does not repaint a native preset. The original Default, Soft and Accent Wash are removed; their saved selections migrate to the new Default without changing Blender's saved appearance at startup. Minimal and Shaded were removed earlier. Saved Layered selections keep their appearance and are now labeled Default.

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

### 1.2.2 — Blender 5.3 support and review fixes

- Works on Blender 4.5 LTS, 5.2 LTS and 5.3. Blender 5.3 removed a few theme colors (editor header text and title colors, the File Browser selected-file color); Palette Studio skips what a version does not have and keeps everything else.
- **Restore Previous Theme** (Settings) returns to the theme Blender showed before the first palette was applied.
- Noctalia dark and light variants are starred independently; older favorites keep working.
- Turning a global Text or Text Selected override off, with no palette loaded, brings back the theme's own colors.
- A palette that fails to load now shows the reason in the header card instead of failing silently.
- Downloads: old download logs are pruned (the newest five are kept), and a refresh where every source fails is reported as an error.
- The unused Local-folder source mode and a few hidden legacy settings were removed. Your files are never touched.
- Developer option: start Blender with `PALETTE_STUDIO_DEBUG=1` to print the theme fields the running Blender version does not have.

### 1.2.1 — default source and header hotfix

- Enables iTerm2 and disables NvChad by default for new preferences, without changing saved source choices or the Noctalia default.
- Removes the "1000+ palettes, ready to explore." message from the empty header.

### 1.2.0 — workspace cleanup

Public release of the tab-cleanup workspace; theme application and saved preferences are unchanged.

### 1.1.0 public baseline
Version **1.1.0** maps Common → Animation → Channels to the palette cyan and Sub-channels to bright cyan. It also keeps the Channels text mapping, remembered palette selection, and earlier widget-state mappings.

---

## Themes and sources

Palette Studio downloads from six places:

- [NvChad base46](https://github.com/NvChad/base46)
- [iTerm2-Color-Schemes](https://github.com/mbadolato/iTerm2-Color-Schemes) - on by default
- [tinted-theming base24](https://github.com/tinted-theming/schemes)
- [kitty-themes](https://github.com/kovidgoyal/kitty-themes)
- [alacritty-theme](https://github.com/alacritty/alacritty-theme)
- [Noctalia community palettes](https://github.com/noctalia-dev/community-palettes)

Noctalia is special: it is the only source that also reads files you already have. Every scheme in `~/.config/noctalia/colorschemes/<Name>/<Name>.json` shows up next to the downloaded ones, with a Dark and a Light entry each, and a scheme that exists in both places is listed once (from your local file).

That is plenty to get started. Nothing is bundled with the add-on; the files are fetched and cached on your machine. Credit for every scheme goes to whoever made it, so check the repositories above for their licenses. Neither the original Palette author nor I claim authorship of any of these schemes.

## Requirements

- Blender 4.5 or newer (tested on 4.5 LTS, 5.2 LTS and 5.3)
- An internet connection for the first download

## License

GPL-3.0-or-later, which is what Blender requires of add-ons that use bpy. Use it, change it, share it, just keep derivatives under the same license. Full text is in [LICENSE](LICENSE).

## Credits

- Original add-on ("Palette", © 2025 NXSTYNATE, GPL-3.0-or-later): [nxstynate/palette](https://github.com/nxstynate/palette)
- Palette Studio modifications and maintenance: **Pr83-Glitch** (2025-present)

Palette Studio is an unofficial community fork. NXSTYNATE's original copyright and license notices are preserved in the source; the changes made here are maintained separately by Pr83-Glitch.

Found a bug or have an idea? Open an issue. Including your Blender version and what you were doing helps a lot.
