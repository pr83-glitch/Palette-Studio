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

And the 5 other noctalia users out there like me there an option to sync blender with your noctalia theme with **1 click** in **Palette Studio > Settings > noctalia sync (optional)**

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
