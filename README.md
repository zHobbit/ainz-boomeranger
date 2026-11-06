# Ainz Boomeranger

Mod visual de **Trove** que veste o Boomeranger como **Ainz Ooal Gown** (Overlord): manto
roxo e dourado até os pés, capa longa com gola de espinhos, capuz e máscara de caveira, o
Cajado de Ainz Ooal Gown, efeitos das skills em violeta e verde espectral e galinhas
esqueleto. **Só aparência**: nenhum dano ou mecânica muda.

Baixe o `.tmod` na página de [Releases](../../releases).

## Instalar

1. Feche o Trove.
2. Copie `Ainz Boomeranger.tmod` para a pasta `mods` do jogo
   (Glyph: `C:\Program Files (x86)\Glyph\Games\Trove\Live\mods`), ou adicione pelo
   Better Trove Tools e clique em **Reload Mods**.
3. Desative outros mods que troquem o Boomeranger (ex.: *Elise, Queen of Spiders*): eles
   substituem os mesmos arquivos.

## O que equipar

| Slot | Escolha | O que muda |
|------|---------|------------|
| Traje | **Bumeranguer Nível 20** (`adventurer_lvl3`) | corpo, manto, capa e modelos das skills |
| Chapéu | **Capuz Negro** (Dark Hood) | capuz do Ainz |
| Rosto | **Meio-Crânio Assombrado** (Haunting Halfskull) | máscara de caveira |
| Arma | **Espada Lascada** (espada inicial) | Cajado de Ainz Ooal Gown |

Os efeitos de partícula das skills e as galinhas esqueleto (inclusive a galinha grande)
valem com qualquer traje padrão. Capuz, máscara e cajado trocam esses itens para qualquer
classe — apenas no seu cliente: mods do Trove não mudam o que os outros jogadores veem.

## Conteúdo do mod (52 arquivos)

- 13 peças de corpo `c_p_adventurer_lvl3_*`, 4 modelos de skill `c_p_adventurer_basic_*`
- capuz `equipment_helm_darkhood` e máscara `equipment_face_mask_halfskull[destral]`
- cajado sobre `equipment_weapon_1h_sword_001`
- 9 peças da galinha `c_c_quchik_*` (a skin Undead do jogo, olhos em verde espectral)
- 21 scripts de partícula `particles/vfx/particles/character_pc_adventurer_*.pkfx`
  recoloridos (cura, energia, fada e escudo ficam no original de propósito)

## Ferramentas

Python 3, só biblioteca padrão + Pillow para os previews.

| Módulo | Faz |
|--------|-----|
| `tools/tmod.py` | lê e escreve o container `.tmod`, incluindo o checksum FNV-1a do Trove |
| `tools/blueprint.py` | codec de `.blueprint` (kiwib) v5, e leitura de v3/v4 |
| `tools/tfa.py` | lê os arquivos `index.tfi` / `archiveN.tfa` do jogo |
| `tools/qb.py`, `tools/model.py` | Qubicle `.qb` e o devtool do jogo (rota alternativa) |
| `tools/theme.py` | paleta do Ainz sobre as cores dos modelos doadores |
| `tools/vfx.py` | recolore curvas de cor PopcornFX (`.pkfx`) de forma linear, preservando a forma das curvas |
| `tools/ainz_parts.py` | manto, capa, cajado e galinhas esqueleto |
| `tools/render.py` | previews ortográficos sem abrir o jogo |
| `tools/build.py` | monta o mod: `py -m tools.build` escreve `dist/` |

## Rebuild

Os arquivos de terceiros não estão no repositório. Para gerar o mod do zero:

1. Coloque os mods originais em `sources/death-lord/Death Lord.tmod`
   (Workshop 1520979943) e `sources/elise/Elise.tmod`, e extraia os blueprints para
   `work/death-lord/blueprints` e `work/elise/blueprints` com `tools.tmod.extract_tmod`.
2. Extraia do jogo os modelos vanilla para `work/game-assets/blueprints` e as partículas
   listadas em `tools/vfx.py::EFFECTS` para `work/game-assets/particles`:
   `py -m tools.tfa "<Trove>/Live/blueprints" extract <nomes> -o work/game-assets/blueprints`.
3. `py -m tools.build`

Testes (precisam dos arquivos acima; alguns também do jogo instalado):

```bash
py -m unittest tests.test_tmod tests.test_tmod_hash tests.test_tmod_write tests.test_qb_read \
  tests.test_qb_write tests.test_model tests.test_tfa tests.test_blueprint_codec tests.test_theme \
  tests.test_render tests.test_build tests.test_vfx
```

## Créditos

- **NeodymiumP** — mod *Death Lord*: manto, mãos, capuz, máscara e o Cajado de Ainz Ooal
  Gown são modelos dele, re-encaixados e recoloridos aqui.
- *Elise, Queen of Spiders* (publicado por 激萌的啡色小熊) — referência e modelos das skills
  do Boomeranger e das pernas.
- **Better Trove Tools** — referência dos formatos `.tmod`, `.blueprint` e `.qb`.
- Trove é da Gamigo; Ainz Ooal Gown / Overlord é de Kugane Maruyama. Mod de fã, sem
  vínculo oficial.

Autor do mod: **Xlabausaum**.
