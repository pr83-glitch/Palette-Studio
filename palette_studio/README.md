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

1. Open **Palette Browser** (it is open by default).
2. Click **Load Themes** and wait while it fetches the repositories.

The list is remembered between sessions, so no re-downloading. Once loaded, the button becomes **Unload**, which clears the list and deletes the cached files. To refresh, hit **Unload** then **Load Themes** again.

## Using it

1. Click a theme. With **Live Preview** on (the default), Blender updates instantly.
2. Search, sort, and star favourites to narrow things down.
3. **Apply** when you are happy, or **Reset** to go back to Blender's default.

**Worth remembering:** applying a theme only changes the current session. To keep it, go to **Edit > Preferences**, open the menu in the bottom-left, and **Save Preferences**. Or edit a palette and use **Save as New Theme** to store it as a real preset.

---

## What is in it

### Palette Browser
The main list. Search, sort (Favourites First / Popular First / A to Z / Z to A), preview live, favourite, apply. Your sort mode and favourites are remembered. A Dark/Light filter sits above the list, and each row has a Dark or Light tag so you can tell schemes apart at a glance.

### Palette Editor
Bend a theme before applying it. Every slot is editable, ANSI 0 to 15 plus background, foreground, cursor, and selection. Each row has a swatch and a hex field. **Swap Colors** exchanges two slots, **Reset to Original** undoes your edits, and **Apply Custom Palette** runs with them.

### Finetune
The stuff Blender usually hides away. Everything here updates live and is re-applied whenever you load a palette.

- **Accent Colors** - pick which palette slot drives each of the three accents (Primary, Secondary, Tertiary). Defaults are Yellow, Cyan, and Selection.
- **Playhead Color** and **Selected Keyframes** - the frame indicator and selected keyframes, in your palette's colors.
- **Axis Colors** - X/Y/Z axis and gizmo colors. These reset to their defaults on every apply.
- **Selected Object** and **Active Object** - the selected and active object colors in the 3D viewport. **Theme Default** keeps the palette's own color, or pick any slot yourself.
- **Edge Width, Vertex Size, Face Dot Size, Outline Width** - viewport geometry, live.
- **Grid Color** - override the viewport grid.
- **Border Radius** - one slider for every rounded corner in the UI.
- **Text Color** and **Text Selected** - global overrides that repaint every text and selected-text color in Blender. Flip the **Custom** toggle off and the palette's colors come straight back.
- **Font Size**, **Channel Text**, **Selected Channel**, **Text Shadow** - the Dopesheet and Timeline channel colors, font size, and shadow, each with a **Custom** toggle so you can leave the Blender setting alone if you want.

A couple of deliberate choices: in Edit Mode, unselected edges and vertex dots stay black so yellow is left for selection, and bone fills stay white with a faint tint. Panel and menu shadow strength is never touched, so that one is still yours.

### Settings
- **Live Preview** - preview on selection, no disk writes. On by default.
- **Theme Sources** - download from the remote repositories, or point at a local folder of `.itermcolors` / `.yml` / `.yaml` / `.conf` / `.lua` files. Once themes are loaded, the per-source toggles act as live filters: turn one off and its themes hide, turn it back on and they return. Each row in the list shows its source in dimmed brackets.

### Save as New Theme
Below Settings. Load or edit a palette, click it, give it a name, and Blender saves it as a normal theme preset. If the name already exists, you get a warning and the button turns into **Overwrite**.

### Updates
Check for a newer Palette Studio build and install it in place, without restarting Blender.

- **Update Source** - **Local ZIP Folder** now; **GitHub Releases** is wired up but not enabled until the add-on is published.
- **Update Folder** - a folder holding `add-on-palette-studio-v<version>.zip` release packages.
- **Check for Updates** - if a newer version is found, a confirmation dialog shows the current and new version. Confirm and the add-on swaps itself in place; Blender stays open.

---

## Themes and sources

Palette Studio downloads from three places:

- [NvChad base46](https://github.com/NvChad/base46) - on by default
- [iTerm2-Color-Schemes](https://github.com/mbadolato/iTerm2-Color-Schemes)
- [tinted-theming base24](https://github.com/tinted-theming/schemes)

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
