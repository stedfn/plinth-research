# Provenance

This repository was created on 2026-10-10 from two existing sources. The first commit is
a byte-identical import of both; every later commit is an edit on top of it, so
`git diff <first-commit> HEAD` shows exactly what changed after import.

## Compiler

- Source repository: `github.com/stedfn/startup` (private), directory `plinth/`.
- Source commit: `1161230826ea1648d338e3c0c6155dabc2134c76`. At import time this commit
  existed only in a local checkout and had not been pushed.
- Imported paths: `.gitignore`, `README.md`, `pyproject.toml`, `inputs/`, `prompts/`,
  `src/`, `tests/`, `runs/.gitkeep`. Research runs were not imported.
- Git tree IDs at the source commit. The same directories in this repository's first
  commit have identical IDs, which proves the bytes are unchanged:

  | Directory | Tree ID |
  | --- | --- |
  | `src` | `b2e5c262c6b791776ccde823c629687ac3c88f8f` |
  | `tests` | `237819c94da8efb3c1961fbbd70d63d41ee98008` |
  | `inputs` | `60e1c44df00f5fef8a67b77db01e9858c8df2862` |
  | `prompts` | `d75599f49eeff2558bdebb19dce9760582a9e860` |

- Pinned inputs (SHA-256):

  | File | SHA-256 |
  | --- | --- |
  | `inputs/plinth-framework-v0.2-working.md` | `2e5071026fd3477ad874168ef552ba26943721f60ece45bd65ac816bc1b59a0a` |
  | `inputs/trust-center-output-contract-v0.1.md` | `fad5967d9ca6a2347179ff202e8fc510cefabe57ffa4e951e1c48e3574bba77c` |
  | `inputs/catalogue.json` | `7945d9419003d43f98e35d129c6c0c41743e0c50c9446499c96d931ec9c4b3c7` |

  The framework and output-contract files are snapshots. Framework authoring happens
  elsewhere; see the maintainer checklist in `README.md`.

## Trust-center skill

- Source: a local Codex skill directory, `plinth-trust-center`. It was not under version
  control, so its files are identified by hash. Imported into `skills/plinth-trust-center/`.
- SHA-256 of each imported file, as imported:

  | File | SHA-256 |
  | --- | --- |
  | `SKILL.md` | `2688317b6c04f74da6ece004e7b3061efa521f512ec1c76c45f2746b401aa84d` |
  | `agents/openai.yaml` | `a385c0b8b4b36b850bbf57ab58e64c579eb84c1aa61297792c8f085a2f69e365` |
  | `assets/v0.3-two-mode-composition-skeleton.html` | `7fdaabfaca9a8a401898302a146e0e105b0064b0d6f74710199d6299895fa50e` |
  | `references/assessment-and-authoring.md` | `206dcd68d715083fcd3aa46ddd3f6c5bb3c65a67a80186e16ccc0719bd90fd97` |
  | `references/input-contract.md` | `ab417cfd7dd453e08e7ae692a58479f5a999bd665daa28cb1d8af3a67c05b887` |
  | `references/plinth-framework-v0.2.md` | `2e5071026fd3477ad874168ef552ba26943721f60ece45bd65ac816bc1b59a0a` |
  | `references/trust-center-output-contract-v0.1.md` | `fad5967d9ca6a2347179ff202e8fc510cefabe57ffa4e951e1c48e3574bba77c` |
  | `references/two-mode-interface-contract.md` | `ce7bfeef333ccaacc49dc847dac9d0d35c8cccdc5be5ea3252c94237db29be97` |
  | `scripts/check_assessment.py` | `84c1c62735a49919aa103a301531d8d3976b4c0464b104e10d1e77ca646815e4` |
  | `scripts/check_morphed_html.py` | `0c8a7b39bae1c173572d695da273a742873835ce8740d0ae37efeb5eb7f39106` |

- Not imported: `assets/v0.3-two-mode-interface-reference.html`
  (SHA-256 `ff3db76329218be04ed831967d390470a36f78094c9b75657d7c1370602f39be`). It is a
  finished Trust Center for a real product. It was used only as the input from which the
  product-neutral `assets/v0.3-two-mode-shell.html` was derived; none of its content is in
  this repository's history.

## Derived shell

`skills/plinth-trust-center/assets/v0.3-two-mode-shell.html` was produced from that
exemplar by a one-off script that is not part of this repository, because it needs the
exemplar as input. What the script preserved and changed:

- `<head>` is the exemplar's, byte for byte, except two things. The `<title>` is now
  `{{PRODUCT}} · Plinth Trust Center v0.3`. Product names inside CSS comments were replaced
  by neutral words.
- The four embedded font data URIs and the `<style id="v03-skin">` block are byte-identical
  to the exemplar's. The SHA-256 of the `v03-skin` inner CSS is
  `8792c57c991bd44c40154fa876ea148385d3b6c91a6f50d63983c3df6953d11a`.
- The navigation script is the exemplar's with one fix. Fragment decoding is wrapped in a
  `try`/`catch`, so a malformed link falls back to Executive mode instead of stranding the
  page.
- One style block, `<style data-purpose="shell-fixes">`, is added after the exemplar's
  styles. Below 760px the exemplar made record badges full-width without letting the summary
  row wrap, so every record title collapsed to zero width. The added rule wraps that row.
- The body keeps one neutral example of every component, together with the structural
  counts the router and checker rely on. All product text became `{{UPPER_CASE}}`
  placeholders. Identifiers and links became placeholders or `https://example.invalid/`.
  Regions that are rendered mechanically from accepted records are empty and marked
  `data-fill`.
- Before commit, the script checked that the shell contains none of the exemplar's
  product names or record identifiers, and that every attribute value is either
  structural or a placeholder.
