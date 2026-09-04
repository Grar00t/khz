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

## Identity lock

`oracle.jinja` replaces the vendor chat template at inference time. It passes a client system message through, otherwise injects the operator identity block, then emits one frozen anchor exchange before the live turns.

Measured on Phi-4-reasoning-plus Q4_K_M:

```text
vendor template   prompt_tokens 246   answer: "I'm Phi, a large language model developed by Microsoft"
identity block    prompt_tokens 106   answer: "I'm a large language model trained by Microsoft"
block + anchor    prompt_tokens 202   answer: "I am Oracle, of the Rawaseeng series ..."
```

The instruction alone loses to pretraining. The anchor pair wins because the model reads its own prior turn as fact. The durable fix is a supervised identity dataset; the template is the zero-cost fix that works today.

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
