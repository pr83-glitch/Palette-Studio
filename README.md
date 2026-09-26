![Palette Studio - Blender ANSI themes](assets/palette%20studio%20banner.png)

# Palette Studio

900+ easy to customize themes in 1 click!

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

### Updating

Palette Studio can check for a newer build and install it without restarting Blender:

1. Open **Edit > Preferences > Add-ons > Palette Studio > Updates**.
2. Point **Update Folder** at a folder holding `add-on-palette-studio-v<version>.zip` builds.
3. Click **Check for Updates**. If a newer version is found, a confirmation dialog shows the
   current and new version; confirm to install it in place.

GitHub Releases checking is planned for when the add-on is published.

## Usage

The list starts empty, so the palettes need to be downloaded first.

1. Open **Palette Browser**
2. Click **Load Themes** and wait a few seconds while it fetches the themes from the repositories.

*If you have multiple sources enabled, it will take a bit more time to load all the themes.*

Once themes are there:

1. Click a theme. Blender updates instantly.
2. Search, sort, and star favourites to narrow things down.
3. Hit **Apply** when you are happy, or **Reset** to go back to Blender's own theme.

By default only one source is active (NvChad base46, about 100 themes). Enable the other two in the Settings tab to browse the full 900+ list. Each source is pinned to a reviewed snapshot, so the list is reproducible rather than shifting under you.

**Worth remembering:** To save the theme, navigate to the bottom, and click **Save as new theme**. Or edit a palette and use **Save as New Theme** to store it as a real theme preset.

Everything lives in **Edit > Preferences > Add-ons > Palette Studio**, and in the 3D Viewport sidebar (<kbd>N</kbd>) under the **Palette Studio** tab, so you can open it while you work.

### The sections

- **Palette Browser** - the theme list, plus search, sort, favourites and the Dark/Light filter.
- **Palette Editor** - edit any slot before applying: ANSI 0-15, background, foreground, cursor, selection. (These are just the color tags for the raw theme files. May not behave the same way in Blender. Feel free to tinker as you can always reset your changes)
- **Finetune** - accents, viewport and text colors, and UI roundness.
- **Settings** - live preview, remote sources, local folder loading.
- **Updates** - check a local folder of release zips (and later GitHub) for a newer build and install it in place, without restarting Blender.


## Requirements

- Blender 4.5 or newer (4.5 LTS and 5.x both work)
- An internet connection for the first download

## Documentation

Full walkthrough of the browser, palette editor, Finetune and settings lives in [palette_studio/README.md](palette_studio/README.md).

## License

GPL-3.0-or-later, which is what Blender requires of add-ons that use bpy. Full text is in [LICENSE](LICENSE).

## Credits

- Original add-on ("Palette", © 2025 NXSTYNATE, GPL-3.0-or-later): [nxstynate/palette](https://github.com/nxstynate/palette)
- Palette Studio modifications and maintenance: **Pr83-Glitch** (2025-present)

Palette Studio is an unofficial community fork. NXSTYNATE's original copyright and license notices are preserved in the source; the changes made here are maintained separately by Pr83-Glitch.

## Theme sources

- [NvChad base46](https://github.com/NvChad/base46) - on by default
- [iTerm2-Color-Schemes](https://github.com/mbadolato/iTerm2-Color-Schemes)
- [tinted-theming base24](https://github.com/tinted-theming/schemes)
Nothing is bundled with the add-on; the files are fetched and cached on your machine. Credit for every scheme goes to whoever made it, so check the repositories above for their licenses. I didnt create or own these schemes.

Each source is pinned to a reviewed upstream commit, so the downloaded sets are reproducible. Updating a source is a manual, reviewed change made in the add-on code.

Found a bug or have an idea? Open an issue. Including your Blender version and what you were doing helps a lot.
