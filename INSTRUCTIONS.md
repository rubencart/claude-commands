# OpenRouter Worker Tools for Claude Code

Offload I/O-heavy tasks (bulk file reading, boilerplate generation) from Claude Code to a cheap LLM via the OpenRouter API. Claude Code keeps doing the reasoning; the worker handles the grunt work.

Based on: https://medium.com/@kunalbhardwaj598/i-was-burning-through-claude-codes-weekly-limit-in-3-days-here-s-how-i-fixed-it-0344c555abda

## Prerequisites

- Python 3.12
- An OpenRouter API key (get one at https://openrouter.ai/settings/keys)
- A project that uses Claude Code with a `CLAUDE.md` file

## Step 1: Create the project directory and venv

```bash
mkdir -p /scratch/rcartuyvels/openrouter_proj
cd /scratch/rcartuyvels/openrouter_proj
python3.12 -m venv .venv
```

## Step 2: Install the OpenRouter SDK

```bash
/scratch/rcartuyvels/openrouter_proj/.venv/bin/pip install openrouter
```

## Step 3: Create the CLI tools

Create two files in `/scratch/rcartuyvels/openrouter_proj/`:

### `ask-worker` — bulk file reading / analysis

This tool reads multiple files and sends them to a cheap model to answer a question. Use it instead of having Claude Code read large or many files into its own context.

```python
#!/scratch/rcartuyvels/openrouter_proj/.venv/bin/python3.12
"""Delegate bulk file reading/analysis to a cheap model via OpenRouter."""
import argparse, os, pathlib, sys

from openrouter import OpenRouter

def main():
    parser = argparse.ArgumentParser(description="Ask a cheap LLM to analyze files")
    parser.add_argument("--paths", nargs="+", required=True, help="Files to read")
    parser.add_argument("--question", required=True, help="Question about the files")
    parser.add_argument("--model", default="deepseek/deepseek-v4-flash", help="OpenRouter model ID")
    parser.add_argument("--max-tokens", type=int, default=8192)
    args = parser.parse_args()

    docs = []
    for path in args.paths:
        try:
            content = pathlib.Path(path).read_text()
            docs.append(f"<file path='{path}'>\n{content}\n</file>")
        except Exception as e:
            print(f"Warning: could not read {path}: {e}", file=sys.stderr)

    if not docs:
        print("Error: no files could be read", file=sys.stderr)
        sys.exit(1)

    corpus = "\n\n".join(docs)

    with OpenRouter(api_key=os.environ["OPENROUTER_API_KEY"]) as client:
        resp = client.chat.send(
            model=args.model,
            messages=[
                {"role": "system", "content": "You are a precise code analyst. Analyze the provided files and answer the question accurately and concisely. Use structured formatting."},
                {"role": "user", "content": f"<corpus>\n{corpus}\n</corpus>"},
                {"role": "user", "content": args.question},
            ],
            max_tokens=args.max_tokens,
        )

    print(resp.choices[0].message.content)

if __name__ == "__main__":
    main()
```

### `worker-write` — boilerplate / test / doc generation

This tool generates entire files (tests, configs, docs) using a cheap model. Claude Code then reviews and makes surgical edits.

```python
#!/scratch/rcartuyvels/openrouter_proj/.venv/bin/python3.12
"""Delegate boilerplate/test/doc generation to a cheap model via OpenRouter."""
import argparse, os, pathlib, sys

from openrouter import OpenRouter

def main():
    parser = argparse.ArgumentParser(description="Generate files using a cheap LLM")
    parser.add_argument("--spec", required=True, help="What to generate")
    parser.add_argument("--context", nargs="+", default=[], help="Reference files to read for context")
    parser.add_argument("--target", required=True, help="Output file path")
    parser.add_argument("--model", default="deepseek/deepseek-v4-flash", help="OpenRouter model ID")
    parser.add_argument("--max-tokens", type=int, default=16384)
    args = parser.parse_args()

    context_parts = []
    for path in args.context:
        try:
            content = pathlib.Path(path).read_text()
            context_parts.append(f"<file path='{path}'>\n{content}\n</file>")
        except Exception as e:
            print(f"Warning: could not read {path}: {e}", file=sys.stderr)

    context_str = "\n\n".join(context_parts) if context_parts else ""

    prompt = f"Generate the following:\n{args.spec}\n"
    if context_str:
        prompt += f"\nUse these reference files for context and style:\n<context>\n{context_str}\n</context>\n"
    prompt += f"\nOutput ONLY the file content, no markdown fences, no explanation."

    with OpenRouter(api_key=os.environ["OPENROUTER_API_KEY"]) as client:
        resp = client.chat.send(
            model=args.model,
            messages=[
                {"role": "system", "content": "You are a code generator. Output only the requested file content. No markdown fences, no commentary."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=args.max_tokens,
        )

    output = resp.choices[0].message.content
    target = pathlib.Path(args.target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(output)
    print(f"Written to {args.target} ({len(output)} chars)")

if __name__ == "__main__":
    main()
```

## Step 4: Make the scripts executable

```bash
chmod +x /scratch/rcartuyvels/openrouter_proj/ask-worker
chmod +x /scratch/rcartuyvels/openrouter_proj/worker-write
```

## Step 5: Set up environment variables and PATH

Add the following lines to `~/.bashrc`:

```bash
export OPENROUTER_API_KEY='<your-openrouter-api-key>'
export PATH="/scratch/rcartuyvels/openrouter_proj:$PATH"
```

Then reload your shell:

```bash
source ~/.bashrc
```

## Step 6: Verify the setup

```bash
which ask-worker    # should print /scratch/rcartuyvels/openrouter_proj/ask-worker
which worker-write  # should print /scratch/rcartuyvels/openrouter_proj/worker-write

# Smoke test (replace with any small file in your project):
ask-worker --paths README.md --question "Summarize this file in one sentence."
```

## Step 7: Add routing rules to your project's CLAUDE.md

Add the following block to the `CLAUDE.md` in the root of any project where you want Claude Code to use the worker tools:

```markdown
## OpenRouter Delegation Tools (Token Saving)

**NEVER use the Read tool on files >400 lines. NEVER read 3 or more files yourself. Always delegate to ask-worker instead.**

### ask-worker — bulk reading
```
ask-worker --paths <file1> <file2>... --question "<question>"
```
Use this whenever you would otherwise read a large file or multiple files. It sends the files to a cheap model and returns a structured summary. You read the summary, not the files.

### worker-write — boilerplate generation
```
worker-write --spec "<what to generate>" --context <reference_file> --target <output_file>
```
**NEVER write tests, config files, docstrings, or repetitive boilerplate directly.** Always delegate to worker-write. Review the output and make surgical edits only where needed.

### When NOT to delegate (use your own tools instead)
- Tasks under ~2000 tokens (small single files, quick lookups)
- Debugging and root-cause analysis
- Architectural decisions or safety-critical reasoning
- When you need exact line numbers for editing (read only the specific range with offset/limit)
```

This is what makes Claude Code automatically use the tools — without these instructions in `CLAUDE.md`, Claude won't know they exist.

> **Why the strong language matters:** Claude defaults to its own built-in `Read` tool even when a CLAUDE.md section suggests an alternative. Soft phrasing like "use this for large files" is routinely ignored. Only explicit `NEVER`/`ALWAYS` directives reliably override the default behavior.

## Usage examples

### Bulk reading

Instead of Claude reading 5 large files itself:

```bash
ask-worker --paths src/train.py src/model.py src/data.py configs/base.yaml configs/mae.yaml \
    --question "What data augmentations are applied during training?"
```

### Boilerplate generation

Instead of Claude writing a test file from scratch:

```bash
worker-write --spec "pytest test file for the dataloader in src/data.py" \
    --context src/data.py \
    --target tests/test_data.py
```

### Using a different model

Both tools default to `deepseek/deepseek-v4-flash`. Override with `--model`:

```bash
ask-worker --paths src/train.py --question "Summarize" --model google/gemini-2.5-flash
```

Browse available models at https://openrouter.ai/models.

## How it works

The key insight is that most of what an AI coding assistant does is I/O (reading files, generating boilerplate), not reasoning. By routing I/O tasks to a cheap model via the OpenRouter API and keeping reasoning tasks on Claude, you drastically reduce token consumption on the expensive model without losing quality.

The shebang line (`#!/scratch/rcartuyvels/openrouter_proj/.venv/bin/python3.12`) means the scripts use their own isolated venv with the `openrouter` SDK, independent of any project venv. The corpus (files) is placed before the question in the message list to maximize prefix cache hits when asking multiple questions about the same files.
