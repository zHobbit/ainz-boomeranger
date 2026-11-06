# 💀 Ainz Boomeranger

A cosmetic **Trove** mod that dresses the Boomeranger as **Ainz Ooal Gown** (Overlord): a floor-length purple and gold robe, a long cape with a spiked collar, a hood and skull mask, the Staff of Ainz Ooal Gown, skill effects in violet and spectral green, and skeleton chickens. **Looks only**: no damage or mechanics change.

Download the `.tmod` from the [Releases](../../releases) page.

## ✨ Technologies

- `Python 3` (standard library only)
- `Pillow` (previews)
- Custom codecs for Trove's `.tmod`, `.blueprint`, `.qb`, `.tfi`/`.tfa` and PopcornFX `.pkfx` formats

## 🚀 Features

- **Full outfit** - 13 body pieces and 4 skill models for the Boomeranger costume
- **Hood, mask and staff** - Swap in over the Dark Hood, Haunting Halfskull and the starter sword
- **Skeleton chickens** - 9 chicken pieces based on the game's Undead skin, with spectral green eyes
- **Recolored VFX** - 21 PopcornFX particle scripts recolored in violet and green; healing, energy, fairy and shield effects keep the original colors on purpose
- **Reproducible build** - The whole mod (52 files) is built from source with one command
- **Previews without the game** - Orthographic renders of every part

## 📍 The Process

Trove mods are packed in a binary `.tmod` container, so before changing a single color I had to be able to read and write it, including the game's FNV-1a checksum. From there I wrote codecs for the `.blueprint` model format (v5, plus reading v3/v4), the game's `index.tfi` / `archiveN.tfa` archives and Qubicle `.qb` files.

The models start from existing community mods and vanilla assets, re-fitted and recolored with an Ainz palette. The particle effects were the trickiest part: PopcornFX stores colors as curves, so `vfx.py` remaps them linearly to keep each curve's shape while changing its hue. A small renderer produces orthographic previews, so I could iterate without launching the game every time.

## 🎯 Tools

| Module | What it does |
|--------|-----|
| `tools/tmod.py` | Reads and writes the `.tmod` container, including Trove's FNV-1a checksum |
| `tools/blueprint.py` | `.blueprint` (kiwib) v5 codec, plus reading v3/v4 |
| `tools/tfa.py` | Reads the game's `index.tfi` / `archiveN.tfa` files |
| `tools/qb.py`, `tools/model.py` | Qubicle `.qb` and the game's devtool (alternative route) |
| `tools/theme.py` | Ainz palette applied over the donor models' colors |
| `tools/vfx.py` | Linearly recolors PopcornFX (`.pkfx`) color curves, preserving their shape |
| `tools/ainz_parts.py` | Robe, cape, staff and skeleton chickens |
| `tools/render.py` | Orthographic previews without opening the game |
| `tools/build.py` | Builds the mod: `py -m tools.build` writes `dist/` |

## 🚦 Installing

1. Close Trove.
2. Copy `Ainz Boomeranger.tmod` to the game's `mods` folder
   (Glyph: `C:\Program Files (x86)\Glyph\Games\Trove\Live\mods`), or add it through
   Better Trove Tools and click **Reload Mods**.
3. Disable other mods that replace the Boomeranger (for example *Elise, Queen of Spiders*): they
   overwrite the same files.

### What to equip

| Slot | Choice | What changes |
|------|---------|------------|
| Costume | **Boomeranger Level 20** (`adventurer_lvl3`) | body, robe, cape and skill models |
| Hat | **Dark Hood** | Ainz's hood |
| Face | **Haunting Halfskull** | skull mask |
| Weapon | **Chipped Sword** (starter sword) | Staff of Ainz Ooal Gown |

The skill particle effects and the skeleton chickens (including the big chicken) work with any default costume. The hood, mask and staff replace those items for every class, but only on your client: Trove mods don't change what other players see.

## 🔧 Rebuilding

Third-party files are not in the repository. To build the mod from scratch:

1. Place the original mods at `sources/death-lord/Death Lord.tmod`
   (Workshop 1520979943) and `sources/elise/Elise.tmod`, and extract the blueprints to
   `work/death-lord/blueprints` and `work/elise/blueprints` with `tools.tmod.extract_tmod`.
2. Extract the vanilla models from the game to `work/game-assets/blueprints` and the particles
   listed in `tools/vfx.py::EFFECTS` to `work/game-assets/particles`:
   `py -m tools.tfa "<Trove>/Live/blueprints" extract <names> -o work/game-assets/blueprints`.
3. `py -m tools.build`

Tests (they need the files above; some also need the game installed):

```bash
py -m unittest tests.test_tmod tests.test_tmod_hash tests.test_tmod_write tests.test_qb_read \
  tests.test_qb_write tests.test_model tests.test_tfa tests.test_blueprint_codec tests.test_theme \
  tests.test_render tests.test_build tests.test_vfx
```

## 🙌 Credits

- **NeodymiumP**, *Death Lord* mod: the robe, hands, hood, mask and Staff of Ainz Ooal Gown are their models, re-fitted and recolored here.
- *Elise, Queen of Spiders* (published by 激萌的啡色小熊): reference and models for the Boomeranger skills and legs.
- **Better Trove Tools**: reference for the `.tmod`, `.blueprint` and `.qb` formats.
- Trove belongs to Gamigo; Ainz Ooal Gown / Overlord belongs to Kugane Maruyama. Fan mod, not affiliated.

Mod author: **Xlabausaum**.

## 🎞️ Preview

<!-- TODO: add an in-game screenshot or a render from tools/render.py -->
