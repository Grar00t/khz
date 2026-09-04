# Head-to-head protocol

Goal: decide by measurement, not by impression, whether a local flow beats a hosted coding agent on code that compiles and passes tests.

## Rules

1. Thirty tasks, fixed before the first run, written as a one-line requirement plus a hidden test file. Ten C, ten C#, ten C++.
2. Every task ships an ABI contract: exact entry point, exact return codes, exact error strings.
3. No task is scored by prose. A task passes only when the produced unit compiles clean with `-Wall -Wextra` and every hidden test passes.
4. Tests are written before any candidate sees the task, and are never shown to a candidate.
5. One attempt per candidate per task for pass@1. A second scored column allows three repair rounds fed only by compiler and test output.
6. Unicode is a failure, not a warning: an en dash inside code counts as a compile failure.
7. Record for every task: pass@1, pass@3-repair, total tokens, wall seconds, and whether the failure was semantic, syntactic, or contract drift.

## Arms

```text
A  single prompt, local model, one shot
B  local staged flow: spec, tests, implement, verify, repair
C  hosted coding agent, one shot
D  hosted coding agent, its own agentic loop
```

## Reporting

Publish the table even when the local arms lose. Report tokens per solved task next to pass rate; a flow that wins by burning ten times the tokens has not won on cost.

## Observed so far

```text
task   parse a decimal integer from a NUL-terminated string, reject overflow
local  three model attempts at the implement stage failed: wrong constants, en dash in source, const.char typo, bool without stdbool.h, invented return code -4
frozen hand-written reference: 563 code chars, compile rc 0, 8 of 8 tests pass
```

The honest reading of that single data point: the staged flow catches the failures, but a 14B model at Q4 is not yet the author. The next experiment swaps the implement stage to a code-specialized model and keeps the reasoning model for spec and tests.
