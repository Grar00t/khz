# khz-runtime

Local GGUF model runtime CLI over llama.cpp. Pull a model, give it your own name, hard-link it into a flat model directory, serve it on loopback, stop it, inspect it. No external service, no vendor daemon, no telemetry.

Part of the Rawaseeng series. Author: Suliman Nazal Alshammari.

## Why

A model runner should do four things and nothing else: fetch weights, name them, serve them on a port you chose, and tell you the truth about what is running. `khz` is a single Python file with no dependencies beyond the standard library and the `llama` binary.

Weights are never committed here. GitHub rejects files above 100 MB; GGUF weights belong on Hugging Face. This repository holds the runtime, the chat template, and the launcher only.

## Install

```sh
install -m 755 khz /home/a/.local/bin/khz
mkdir -p /home/a/models /home/a/khz
```

Requires `llama` (llama.cpp unified CLI, build b10679 or newer) on PATH and Python 3.

## Commands

```text
khz pull <owner/repo[:quant]> <name> [oracle|builtin]
khz list
khz run <name> [port] [ngl]
khz stop <name>
khz ps
khz logs <name>
```

`pull` downloads through `llama download`, resolves the Hugging Face blob, hard-links it to `~/models/<name>.gguf`, and appends a row to `~/khz/models.tsv`. A hard link costs zero extra bytes; `df` does not move.

`run` starts `llama serve -m ... --alias <name>`, waits for `/health`, writes a PID file, and prints the served model id. If the process dies it prints the return code and the tail of the log instead of hanging.

The third `pull` argument selects the chat template. `oracle` forces `oracle.jinja`; `builtin` keeps the template embedded in the GGUF, which is required for models with native tool calling.

## Registry format

`~/khz/models.tsv`, tab separated:

```text
name    path    template    spec    bytes
```

Model aliases are unique. A malformed registry or duplicate alias fails closed instead of choosing one row implicitly.

## Runtime persona and model provenance

`oracle.jinja` replaces the vendor chat template at inference time when the operator explicitly selects the `oracle` mode. It names the local runtime persona **Oracle**, but it does **not** replace the provenance of the loaded GGUF weights.

The underlying model developer, trainer, and license remain whatever the model metadata and source records establish. A prompt/template can change what the model says about its identity; it cannot change who trained the weights.

A previous revision intentionally anchored the model to claim that no company made or trained it. That was a presentation-layer identity override, not a supported provenance claim, and it has been removed.

## Verified environment

```text
GPU        RTX 3060 12 GB, driver 591.86, CUDA 13.1, sm_86
host       WSL2, 10 GB memory cap, 24 GB swap
engine     llama.cpp b10679-50f068fff
model      Phi-4-reasoning-plus Q4_K_M, 14.66B, 8.43 GB, ctx 8192
throughput about 32 tokens/s generation
KV budget  200 KiB per token; 8192 f16 fits, 16384 f16 does not
```

One 12 GB card serves one model of this size at a time. Run a second model on another port only with `-ngl` layer splitting.

## Tool calling

Phi-4-reasoning-plus emits no tool calls: a request carrying a `tools` array returns `tool_calls: None` and answers in prose. Tool use needs a model trained for it and a template that renders the tool schemas. `oracle.jinja` deliberately does not render tools, so pair it with `builtin` templates for agent work.

## License

UNSEALED. Upstream weights keep their own licenses: Phi-4 MIT, gpt-oss Apache-2.0, Mellum Apache-2.0.
