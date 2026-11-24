# LLM Worker Tools for Claude Code

These command-line tools delegate file analysis or boilerplate generation to a model API. Use the OpenRouter tools, the Mistral tools, or both. The API credentials are optional **per provider**: set the key for the provider whose tools you plan to run.

> **Privacy:** The tools send the contents of the files you specify, along with your prompt, to the selected API provider. Only pass files you are comfortable sharing with that provider. `worker-write*` writes to the `--target` path and replaces that file if it already exists.

## Tools

| Command | Provider | Purpose |
| --- | --- | --- |
| `ask-worker` | OpenRouter | Analyze one or more files and answer a question |
| `worker-write` | OpenRouter | Generate a file, optionally using context files |
| `ask-worker-mistral` | Mistral API | Analyze one or more files and answer a question |
| `worker-write-mistral` | Mistral API | Generate a file, optionally using context files |

OpenRouter tools default to `deepseek/deepseek-v4.1-flash`. Mistral tools default to `zai-glm-5-3`. `ask-worker-mistral` lets you select another Mistral model with `--model`; `worker-write-mistral` currently uses the default model. Both provider variants accept `--max-tokens`.

## Requirements

- Python 3.12
- An API key for each provider you intend to use:
  - OpenRouter: [create/manage keys](https://openrouter.ai/settings/keys)
  - Mistral: create an API key in your Mistral account
- OpenRouter tools need the `openrouter` Python package. Mistral tools use only the Python standard library.

## Install

Clone or copy this repository to a directory on your machine. The examples below use `/path/to/openrouter_proj`; substitute your actual repository directory:

```bash
export WORKER_DIR="/path/to/openrouter_proj"
cd "$WORKER_DIR"
python3.12 -m venv .venv
.venv/bin/python -m pip install openrouter
chmod +x ask-worker worker-write ask-worker-mistral worker-write-mistral
```

The scripts currently have an **absolute Python interpreter path** in their first line (the shebang). Edit the first line of each of these four files to point to your own environment, for example:

```text
#!/absolute/path/to/openrouter_proj/.venv/bin/python3.12
```

Replace the example with the actual absolute path; do not leave the placeholder in the shebang. The Mistral scripts import `mistral_client.py` from the same directory, so no path changes are needed in that module.

To run the commands without typing their full paths, add the repository directory to your `PATH`. For Bash, add this to `~/.bashrc` (replace the example path):

```bash
export PATH="/path/to/openrouter_proj:$PATH"
```

Then run `source ~/.bashrc` or open a new terminal. Alternatively, invoke a command by its full path, such as `"$WORKER_DIR/ask-worker-mistral"`.

## Configure API keys

Set only the key(s) for the provider(s) you will use. For the current shell session:

```bash
export OPENROUTER_API_KEY='<your-openrouter-api-key>'  # needed by ask-worker and worker-write
export MISTRAL_API_KEY='<your-mistral-api-key>'        # needed by the Mistral commands
```

You do not need both keys. To make a key available in future Bash sessions, put its export in `~/.bashrc` or use your preferred secrets manager. Never commit real keys to this repository. The Mistral client uses `https://api.mistral.ai/v1/chat/completions` by default; `MISTRAL_API_ENDPOINT` can optionally override that endpoint.

## Usage

Run commands from the project whose files you want to process. File paths are resolved relative to your current directory.

### Ask a question about files

```bash
ask-worker --paths README.md src/main.py \
  --question "Summarize the application structure."

ask-worker-mistral --paths README.md src/main.py \
  --question "Summarize the application structure."
```

OpenRouter example with a different model:

```bash
ask-worker --paths src/main.py --question "Summarize this file." \
  --model google/gemini-2.5-flash
```

Mistral example with a different model supported by your account:

```bash
ask-worker-mistral --paths src/main.py --question "Summarize this file." \
  --model '<mistral-model-id>'
```

### Generate a file

```bash
worker-write \
  --spec "Write a short README section describing the CLI" \
  --context pyproject.toml \
  --target docs/cli.md

worker-write-mistral \
  --spec "Write a short README section describing the CLI" \
  --context pyproject.toml \
  --target docs/cli.md
```

`--context` can be omitted or given multiple paths. The target's parent directories are created as needed; an existing target file is overwritten. Review generated output before relying on it.

## Claude Code routing

If you want Claude Code to use these commands, add a short note to the relevant project's `CLAUDE.md`, for example:

This repository's [AGENTS.md](AGENTS.md) is another example of agent instructions that route work through the Mistral commands and provide an OpenRouter fallback.

```markdown
## Worker tools

Use `ask-worker` or `ask-worker-mistral` when delegating analysis of multiple or large files is appropriate. Use `worker-write` or `worker-write-mistral` for draft boilerplate. Choose the provider whose API key is configured. These tools send the specified file contents to an external API, so do not pass secrets or confidential files unless approved.

Examples:
- `ask-worker --paths <files...> --question "<question>"`
- `worker-write --spec "<what to generate>" --context <files...> --target <output-path>`
```

Use your own tools instead when a task is small, requires exact line-by-line edits, or involves sensitive data that should not be sent to an external service.
