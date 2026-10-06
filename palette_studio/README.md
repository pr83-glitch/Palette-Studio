# Palette Studio

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

1. Open the **Palette Studio** sidebar tab and choose **Browse** (the default page).
2. Click **Download Palettes** and wait while it fetches the enabled sources.

The list is remembered between sessions. **Configure** holds the download and **Unload Palettes** actions. Unload clears the list and deletes the downloaded files. In Local Folder mode the loading button reads **Load Local Palettes**.

## Using it

1. Click a theme - it applies straight away.
2. Search, sort, and mark **Favorites** to narrow things down.
3. **Restore Blender Theme** goes back to Blender's default theme.

**Save Preferences** keeps the current look after restart. **Save Palette Preset** saves the edited palette as a real Blender theme preset. These actions are below every page, in both the sidebar and Add-on Preferences.

---

## What is in it

### Browse
The main list. Search, sort (Favorites First / Popular First / A to Z / Z to A), filter by All Palettes / Dark / Light, and select to apply immediately. Search updates when you commit the text (Enter or defocus). Your sort mode and favorites are remembered. Each list row has a Dark or Light tag; the card below the list shows the selected palette's full name and source, a Favorite/Unfavorite button and **Edit Palette**.

### Palette
The editor follows the palette selected in Browse. All 20 slots remain editable, grouped into **Base Colors**, **Standard / ANSI 0-7**, and **Bright / ANSI 8-15**. Each row has a swatch and hex field; every edit applies live without an Apply button. Slot numbers stay visible even when labels are shortened for narrow sidebars.

- **Quick Adjust** - Hue, Saturation, Value and Alpha sliders that shift every *checked* ANSI slot at once. Background, foreground, cursor and selection are never touched. Tick a row to include it; unticked rows keep their colour. Hue works like Blender's own hue slider (0.5 = no change), Saturation and Value are multipliers (1.0 = no change), so the palette keeps its own contrasts. **Reset to Original** neutralises everything.
- **Reset to Original** restores the loaded theme's colors, re-ticks every slot, resets the sliders and restores Blender's initially captured UI scale. Other Finetune overrides are retained.
- **Reload Selected Palette** uses the existing load operator to reload the browser selection.

### Appearance
Every existing Finetune control remains available, arranged into three collapsible groups. Settings still update live; saved identifiers and defaults are unchanged.

**Interface**

- **Accent Colors** - pick which palette slot drives each of the three accents (Primary, Secondary, Tertiary). Defaults are Yellow, Cyan, and Selection.
- **Outline 1** - which palette slot draws the main widget outlines, borders and separators. Defaults to Bright Black (ANSI 8).
- **Outline 2** - which palette slot draws Panel and Toolbar Item outlines at 0.3 alpha. Defaults to Background.
- **Outline 3** - which palette slot draws Regular and Option outlines at 0.3 alpha. Defaults to Bright Black (ANSI 8).
- **Background 1** and **Background 2** - tick a row to override that surface with Blender's colour picker. Background 1 covers panels, editor backgrounds, headers, the viewport gradient and the striped list rows; Background 2 covers widget bodies, buttons and the other non-outline surfaces. Unticked, they follow the palette's own background (so nothing changes until you opt in, and Background 2 follows Background 1).
- **Selected text** on tabs, toggles, radio buttons and list items follows Background 1 rather than the palette's foreground, so it stays readable on the accent fill behind it.
- **Roundness** - one slider for every rounded corner in the UI.
- **UI Scale** - Blender's own Resolution Scale (Preferences > Interface), from 1.00 to 2.00. It starts at whatever Blender already has, so nothing changes until you drag it; **Reset to Original** puts that value back.
- **Text Color** and **Text Selected** - global overrides that repaint every text and selected-text color in Blender. Flip the **Custom** toggle off and the palette's colors come straight back.
- **Font Size** and **Shadow** - checkbox-enabled overrides. Unchecked values follow Blender's own settings. Global **Text Color** and **Selected Text** overrides sit alongside them.

**Viewport**

- **Axis Colors** - X/Y/Z axis and gizmo colors. These reset to their defaults on every apply.
- **Selected Object** and **Active Object** - the selected and active object colors in the 3D viewport. **Theme Default** keeps the palette's own color, or pick any slot yourself.
- **Edge Width, Vertex Size, Face Dot Size, Outline Width** - viewport geometry, live.
- **Grid Color** - override the viewport grid.

**Animation**

- **Playhead** and **Selected Keys** - the frame indicator and selected keyframes, in your palette's colors.
- **Channel Text / Normal / Selected** - checkbox-enabled color overrides for Dopesheet and Timeline channel text, moved here from the Interface group. Normal follows the palette foreground by default; Selected follows white.

A couple of deliberate choices: in Edit Mode, unselected edges and vertex dots stay black so yellow is left for selection, and bone fills stay white with a faint tint. Panel and menu shadow strength is never touched, so that one is still yours.

### Configure
- **Palette Sources** - download from the remote repositories, or point at a local folder of `.itermcolors` / `.yml` / `.yaml` / `.conf` / `.lua` / `.toml` / `.json` files. Once themes are loaded, the per-source switches act as live filters: turn one off and its themes hide, turn it back on and they return. Download again to fetch newly enabled sources. The selected palette's source appears in Browse's detail card.
- **Noctalia** - leave the toggle on and your own Noctalia color schemes (and the community palettes) appear in the browser, each as a Dark and a Light entry. Below the toggle sits **Sync Current Theme**: click it once and the colors Noctalia is showing right now are loaded into the palette and applied. It reads the kitty theme Noctalia keeps rewriting (`~/.config/kitty/themes/noctalia.conf`), so it also works when the palette was generated from your wallpaper; if that file is missing it falls back to the scheme named in Noctalia's own settings. It is a one-time pull, so click it again after switching themes in Noctalia.

- **Blender Theme Presets** - the native preset selector, Add, Remove and Save actions, moved from the sidebar header and now available in both UI surfaces.

### Save Palette Preset
Below every page. Load or edit a palette, click it, give it a name, and Blender saves it as a normal theme preset. If the name already exists, the dialog warns you and the existing overwrite confirmation is preserved.

### 1.1.0 release
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
