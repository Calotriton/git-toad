# git-toad

A 16-bit pond toad that grows out of your GitHub contributions. It starts as a clump of frogspawn and, commit by commit, becomes a tadpole, sprouts legs, crawls out as a froglet, and grows into a warty old toad with a mushroom sprouting from its head.

<p>
  <img src="docs/tadpole.gif" width="32%" alt="A tadpole swimming laps in a pixel-art pond">
  <img src="docs/frog.gif" width="32%" alt="A frog on a lily pad catching a fly with its tongue">
  <img src="docs/old-toad.gif" width="32%" alt="A warty old toad with a mushroom on its head catching a fly">
</p>

Inspired by [git-koi](https://github.com/yalongwastaken/git-koi).

## How your toad lives

**Total contributions grow it.**

| Level | Stage     | Contributions |
| ----- | --------- | ------------- |
| 0     | Spawn     | 0             |
| 1     | Tadpole   | 30            |
| 2     | Polliwog  | 300           |
| 3     | Froglet   | 1,000         |
| 4     | Frog      | 3,000         |
| 5     | Old Toad  | 10,000        |

The HUD shows the level, an XP bar toward the next stage, and your total contribution count.

**Streaks spot it.** Every 7 days of your longest daily streak unlocks a pair of spots (up to 3 pairs). The spots take the colors of your top three languages.

**Yesterday decides what it does.** The scene is rendered from the day that just ended (UTC):

| Behavior | When                                                                     | What you see                                                     |
| -------- | ------------------------------------------------------------------------ | ---------------------------------------------------------------- |
| `sleep`  | 14+ quiet days in a row                                                  | Night falls; the toad dozes and snores Z's.                      |
| `leap`   | Crossed a milestone or a new stage in the last 7 days, or had a top-10% day | Jumps off the lily pad (tadpoles dart around) with sparkles.  |
| `hunt`   | Contributed yesterday                                                    | Catches a fly with its tongue (tadpoles chase a food flake).     |
| `idle`   | Otherwise                                                                | Blinks, looks around, and croaks.                                |

![Every stage and behavior](docs/stages.png)

## Add it to your profile

1. In your profile repository (`github.com/<you>/<you>`), copy [examples/profile-workflow.yml](examples/profile-workflow.yml) to `.github/workflows/toad.yml`. It uses `Calotriton/git-toad@main`.
2. Add the toad to your profile `README.md`:
   ```markdown
   ![my toad](toad/toad.gif)
   ```
3. Run the workflow once from the Actions tab. After that it updates every night.

Action inputs:

| Input        | Default                 | Notes                                          |
| ------------ | ----------------------- | ---------------------------------------------- |
| `login`      | repository owner        | Whose public activity grows the toad.          |
| `skin`       | `meadow`                | `meadow`, `golden`, `azure`, `crimson`, `violet` |
| `output-dir` | `toad`                  | Gets `toad.gif` (animated) and `toad.png` (still). |
| `scale`      | `4`                     | The scene is 128x96 pixels; 4 gives 512x384.   |
| `token`      | `github.token`          | Only public data is read.                      |

## Run it locally

You need Python 3.9 or newer. There are no other dependencies: the GIF and PNG encoders are built in.

```sh
export GITHUB_TOKEN=...            # any token; only public data is read
python -m gittoad collect octocat --output snapshot.json
python -m gittoad render snapshot.json --output-dir toad --skin azure
```

Preview any stage or behavior without waiting for it:

```sh
python -m gittoad render snapshot.json --stage 3 --behavior leap
python -m gittoad demo --gifs      # every stage x behavior, plus demo/sheet.png
```

Run the tests with `python -m unittest discover -s tests`.

## How it is made

- `gittoad/collect.py` reads your contribution calendar and repository languages from the GitHub GraphQL API.
- `gittoad/life.py` turns that snapshot into a stage, spots and a behavior.
- `gittoad/art.py` paints the pond on a 128x96 canvas: banded, Bayer-dithered sky and water gradients, hand-made sprite templates for the frog (mirrored, auto-outlined), procedurally animated tadpole tails, and a 3x5 bitmap HUD font.
- `gittoad/encode.py` writes the looping GIF with its own LZW encoder. It only re-encodes the parts of each frame that changed.
