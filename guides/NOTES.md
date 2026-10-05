# Notes

Working notes for whoever maintains these guides.

## Environment facts the guides rely on
- The Makefile uses Docker if installed, otherwise Podman (`COMPOSE` variable). Guides say "Docker or Podman".
- Inside `make shell`, use single quotes around questions that contain `$` (the shell expands `$2` in double quotes). Never pass `$` amounts through `make ... ARGS=` (make expands them too).
- Default model in the facilitator's `.env`: `openrouter:openai/gpt-6-luna`. `MODEL=mock` is the offline fallback; it ignores prompts, so Lab 1 prompt and role steps need a real model.
- Studio graph names (langgraph.json): `lab_1_single_agent`, `lab_2_citizen_platform`, `pattern_1_sequential_pipeline`, `pattern_2_orchestrator`, `pattern_3_parallel_fan_out_gather`, `pattern_4_hierarchical_decomposition`, `pattern_5_generator_critic`.
- Code, `make patterns P=…` values and Studio graph names all use the same names: `lab_1_single_agent`, `lab_2_multi_agent`, `pattern_1_sequential_pipeline` … `pattern_5_generator_critic`. Plain `make patterns` runs all five.

## Naming
- The slide calls pattern 2 "Orchestrator". The code file is `pattern_2_orchestrator.py`; its routing node is still named `coordinator`. Anthropic's article calls the same idea "routing", and uses "orchestrator-workers" for what the slide calls Hierarchical Decomposition. The patterns reference sheet carries this mapping; keep it consistent.

## Format decisions
- One lesson per lab or pattern, numbered in workshop order: Lab 1, patterns 1-5, Lab 2 platform.
- Each lesson: the idea (cited), a diagram, numbered steps with predict-then-check reveals, a Studio section, one change to make, a 3-question quiz, a primary source, and a reminder to ask.
- Quiz options in one question have the same word count.
- Learning records are not used: the guides serve many participants, not one learner.
