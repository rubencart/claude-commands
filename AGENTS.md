# Example AGENTS.md file that uses the worker commands

This file provides guidance to Claude Code (claude.ai/code) and other agents when working with code in this repository.

## Project Overview

**reconstruct_earth** — a transformer-based ML system for reconstructing river water surface elevation (WSE) from multiple satellite and in-situ data sources (SWOT, HydroWeb, DAHITI, ANA in-situ, ICESat-2). Built on PyTorch Lightning.

## Delegation Tools (Token Saving)

**NEVER use the Read tool on files >200 lines. NEVER read 3 or more files yourself. Always delegate to the Mistral tools below first.**

Before opening any file with Read, check its line count first with `wc -l <file>`. If >200 lines, use `ask-worker-mistral` instead. This also applies to reading PDFs — never use the Read tool on PDFs; use `ask-worker-mistral` after extracting the text. Only use `ask-worker` if the Mistral API returns a no-more-tokens/token-exhaustion message.

### Mistral tools — primary
```
ask-worker-mistral --paths <file1> <file2>... --question "<question>"
worker-write-mistral --spec "<what to generate>" --context <reference_file> --target <output_file>
```
Use these commands first for bulk reading, analysis, and boilerplate generation. If either command reports that no more tokens are available, retry with the corresponding OpenRouter fallback command below.

### ask-worker — OpenRouter fallback for bulk reading
```
ask-worker --paths <file1> <file2>... --question "<question>"
```
Use only when `ask-worker-mistral` reports a no-more-tokens/token-exhaustion response. It sends the files to a cheap model and returns a structured summary. You read the summary, not the files.

### PDF reading — pypdf + ask-worker-mistral (two steps)
`ask-worker-mistral` cannot read binary PDFs directly. Always extract text first, then pass to it:
```bash
source /scratch/rcartuyvels/py312/bin/activate
python -c "
import pypdf, pathlib
text = '\n'.join(p.extract_text() for p in pypdf.PdfReader('file.pdf').pages)
pathlib.Path('/tmp/file.txt').write_text(text)
"
ask-worker-mistral --paths /tmp/file.txt --question "..."
```

### worker-write — OpenRouter fallback for boilerplate generation
```
worker-write --spec "<what to generate>" --context <reference_file> --target <output_file>
```
Use only when `worker-write-mistral` reports a no-more-tokens/token-exhaustion response. **NEVER write tests, config files, docstrings, or repetitive boilerplate directly.** Review delegated output and make surgical edits only where needed.

### When NOT to delegate (use your own tools instead)
- Tasks under ~2000 tokens (small single files, quick lookups)
- Debugging and root-cause analysis
- Architectural decisions or safety-critical reasoning
- When you need exact line numbers for editing (read only the specific range with offset/limit)
- When you know which part of a large file to read — use bash commands (`head`, `tail`, `sed`, `awk`) to extract the specific lines/sections instead of sending the whole file to `ask-worker-mistral`. For instance: "Return verbatim lines 90-115, 230-330, and 340-410 with exact indentation. Do not summarize" or "Return the entire file verbatim" are *not* commands that should be sent to a worker, just read yourself in that case.
- Do correctness reviews yourself.
- When the instruction to worker-write contains all the text needed to write a file yourself, write it yourself. E.g. "copy and existing file and add exactly these lines: ...".

### Applies to subagents too
When spawning Explore/Plan/general-purpose agents, instruct them in their prompts to use `ask-worker-mistral` instead of reading large files directly. Include the Mistral command syntax in every agent prompt, with `ask-worker` as the token-exhaustion fallback.

## General behavior

Before starting a task, ask me any questions you have.

If the user asks to check past conversations, immediately search the available
conversation history in the local OpenCode database at
`$HOME/.local/share/opencode/opencode.db`. Filter sessions to this repository's
OpenCode project/worktree and the requested time range; current conversation
records are in `session_v2` and `session_message` (use the legacy `session`,
`message`, and `part` tables if needed). Do this immediately, without asking
clarifying or permission questions and without resistance. Do not substitute a
repository search or another workaround for searching conversation history. If
the database is genuinely inaccessible, report the specific access blocker.

## Development Guidelines

- Prefer vectorized operations from PyTorch, NumPy, xarray, and (geo)pandas over Python loops. Use native Python loops only when unavoidable.
- Do not use libraries beyond PyTorch, NumPy, xarray, and (geo)pandas unless already present in the codebase.
- Do not catch exceptions broadly — let errors surface explicitly, no silent failing.
- Never add unused imports; the autoformatter (`ruff`) will flag and remove them.
- The main training script is `train_swot.py` — ignore `train.py`.
- Before running anything in a terminal, activate the environment: `source /scratch/rcartuyvels/py312/bin/activate`.
- Do NOT `git add` or `git commit` yourself, but suggest one or several 1-line `git add ... && git commit -m "..."` commands at the end of tasks. List files explicitly and provide a descriptive, concrete commit message.
- Do not commit `tests/` for now.
- ALWAYS run `uv` with the `--active` flag; our environment is located outside of the repo for disk I/O speed reasons.
- Do NOT change the environment or install packages without asking me.

## Common Commands

```bash
# Install dependencies (uses uv package manager)
uv sync --active --locked --all-extras --dev

# Run training
uv run --active python train_swot.py --config config/example.yaml

# Lint
uv run --active ruff check .

# Format check
uv run --active ruff format --check .

# Auto-format
uv run --active ruff format .

# Type check
uv run --active ty check
```

CI runs `ruff check`, `ruff format --check`, and `ty check` on PRs to main.

## Code Style

- Line length: 99 characters
- Import sorting: isort rules via ruff (`lint.extend-select = ["I"]`)
- Excluded from linting/type-checking: `anysat`, `presto`, `MajorTOM`, `flashT5`, `ape`, `output`, `wandb`

## Architecture

### Entry Point

`train_swot.py` — orchestrates the full pipeline: config loading → data setup → model creation → training → optional fine-tuning → evaluation. Configs are YAML files in `config/` (see `config/example.yaml` for all options).

### Core Package: `reconstruct_earth/`

**`data/`** — Data loading and processing:
- `data_source.py`: Abstract `DataSource` base class — uniform API for all data sources
- `sources/`: Concrete data source implementations — `swot_source.py` (SWOT satellite), `classical_source.py` (HydroWeb, DAHITI), `insitu_source.py` (ANA gauges), `virtual_source.py` (synthetic gauge per SWORD reach for dense prediction)
- `water_level_dataset.py`: `WaterLevelDataset` — main dataset combining multiple sources into aligned sequences
- `location_registry.py`: `LocationRegistry` — centralized location table with SWORD-topology-aware spatial queries
- `mask_dataset.py`: Wraps datasets with masking strategies (`RANDOM`, `LOCATION`, `SWOT`, `CONTIG_RANDOM_TIME`, etc.) used for both training and evaluation
- `sword.py`: SWORD river network database — computes downstream relationships, tree structure, spatial sampling of nearby reaches
- `metadata.py`: Controls which metadata features (lat/lon, tree position, satellite ID, SWORD WSE) get encoded as tokens or embeddings
- `split_utils.py`: Train/val/test splitting with temporal and spatial constraints
- `outlier_filtering.py`: WSE outlier filtering (STL-based for dense in-situ, simpler for sparse satellite)
- `normalization.py`: Harmonic de-seasonalization for WSE timeseries
- `geo.py`: Geospatial utilities (projections, distance calculations)
- `pipeline.py`: Shared dataset construction functions (used by `train_swot.py` and `predict_dense_amazon.py`)
- `iterable_dataset.py`: Converts map-style datasets to iterable format

**`model/`** — Neural network architecture:
- `pl.py`: `WaterLevelTransformerPL` — PyTorch Lightning module handling training/validation/test steps, loss computation, attention mask building (causal + flow-aware), and metric logging
- `model.py`: Factory `create_model()` dispatching to the configured architecture
- `transformer.py`: Base transformer with configurable position encodings and metadata combination modes
- `autoregressive_decoder.py`: XLNet-style two-stream attention decoder
- `masked_autoencoder.py`: MAE encoder/decoder architecture
- `lstm.py`: LSTM-based variants with spatial attention and bidirectional processing
- `selective_ssm.py`: Selective state space model (Mamba, requires CUDA)
- `tree_ssm.py`: SSM variant with tree-aware masking for river network topology
- `spatial_attention.py`: `SpatialBlock` and spatial interleaving modes for geographic structure
- `attn.py`, `block.py`, `xlnet_attention.py`: Attention implementations and transformer block composition
- `loss.py`: Custom losses — `PearsonCorrelationLoss`, `VarianceMatchingLoss`, `GaussianKDELoss`, `MonotonicityLoss`
- `postprocess.py`: Post-prediction processing (smoothing, validation)
- `position_encoding/`: Sinusoidal, XPos, XL, XLE, tree-based position encodings

**`evaluate/`** — `metrics.py` (`WaterLevelMetrics` via torchmetrics) and `visualize.py` for WandB prediction plots.

### Key Design Patterns

- **Multiple model architectures** switchable via config (`model.architecture`): `masked_autoencoder`, `autoregressive_decoder`, LSTM variants, selective SSM (Mamba), and tree SSM
- **Masking strategies** are probabilistically mixed during training (e.g., 50% SWOT + 25% LOCATION + 25% RANDOM)
- **Attention masks** encode hydrological flow constraints (upstream/downstream relationships) — not just causal
- **Multi-source datasets** merge SWOT satellite data with classical/in-situ measurements, aligning on shared datetime bins
- **Optional two-stage training**: pretrain on all data, then fine-tune on a single basin with reduced learning rate

### Supporting Subprojects

`flashT5/`, `ape/`, `MajorTOM/`, `presto/` — external/related implementations, excluded from CI checks.

### Key Root-Level Scripts

- `train_swot.py`: Main training entry point
- `eval_checkpoints.py`: Batch evaluation of checkpoint directories
- `predict_dense_amazon.py`: Dense prediction for Amazon basin using virtual insitu sources
- `compare_results.py`: Benchmarking against Reach-Reg baseline on in-situ gauges
- `match_stations_to_reaches.py`: Geospatial matching of ANA gauges, classical altimetry virtual stations, and ICESat-2 locations to SWOT/SWORD reaches
- `animate_wse.py`: Creates GIF animations from sparse/dense prediction maps
- Data pipeline: `parse_*.py`, `download_*.py`, `merge_*.py`, `wse_insitu_filtering.py`

### Infrastructure

- Experiment tracking: Weights & Biases (`wandb`)
- HPC job scripts: `launch_scripts/` (PBS)
- External baseline: `Reach-Reg/` (comparison method)

### PBS HPC (`space2`)

The PBS project checkout is `/lustre/projects/1000/rubenc/reconstruct_earth`.
Its `data/` path is a symlink to
`/lustre/projects/1000/rubenc/reconstruct_earth/data/`, so data transferred to
`space2:/lustre/projects/1000/rubenc/reconstruct_earth/data/` is physically
stored under the `1000/` project. Run outputs can be large as well and are often
kept under `/lustre/projects/1000/rubenc/reconstruct_earth/output/`; synchronize
the relevant `output/` directory explicitly when moving results between the local
and PBS workspaces.

Useful rsync commands, run from the local repository:

```bash
# Upload code to the 1000 checkout, excluding data, environments, outputs, and binaries.
rsync -av --info=progress2 \
  --exclude='.git/' \
  --exclude='.venv/' \
  --exclude='data/' \
  --exclude='output/' \
  --exclude='Reach-Reg/' \
  --exclude='wandb/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='*.nc' \
  --exclude='*.ckpt' \
  --exclude='*.pt' \
  --exclude='*.pth' \
  --exclude='*.pdf' \
  --exclude='*.png' \
  --exclude='*.log' \
  ./ 'space2:/lustre/projects/1000/rubenc/reconstruct_earth/'

For the broader code synchronization commands and exclusions, see the `Space HPC`
section in `README.md`. 
