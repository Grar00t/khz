# Runtime repair boundary

The existing CLI is repaired in place; no model weights are supplied or renamed by installation.

- Exact quantization-tag selection, cached main revision when available, and ambiguity/split-file rejection replace largest-file selection.
- Alias validation prevents names from escaping the models/state directories.
- Replacement stages a link before atomic rename and refuses to replace a unique existing weight file.
- Registry writes are atomic; registry and link are not a crash-atomic pair. Report any registry write error before reuse.
- A healthy port must also report the requested model id. This is service metadata, not proof of model quality or a cryptographic weight identity.
- Linux process start ticks, session/group id and boot id bind managed process records. Legacy bare PID records are refused rather than trusted.
- Timeouts clean up the newly launched owned process; failed signals do not produce STOPPED success. An unverified remaining process-group member causes explicit failure and retained state.
- CLI invocations serialize through a local file lock. Hostile filesystem races, shell/MCP isolation and adversarial registry tampering are outside this patch.
- Context remains 8192. Do not raise GPU memory demands merely to match a client estimate.
- Set KHZ_HOME / KHZ_LLAMA / KHZ_TEMPLATE to existing locations when needed. Managed serving targets Linux / WSL.
- serve.sh delegates to khz instead of maintaining a second, weaker health-check path.

Run `python3 -m unittest discover -s tests -v`. The fixtures use synthetic GGUF headers, mocked network/download operations and one short-lived local child; they do not verify llama.cpp/model compatibility or generation quality.
