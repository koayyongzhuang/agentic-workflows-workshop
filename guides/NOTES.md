# Notes

Working notes for whoever maintains these guides.

## Environment facts the guides rely on
- The Makefile uses Docker if installed, otherwise Podman (`COMPOSE` variable). Guides say "Docker or Podman".
- Inside `make shell`, use single quotes around questions that contain `$` (the shell expands `$2` in double quotes). Never pass `$` amounts through `make ... ARGS=` (make expands them too).
- Default model (`.env.example` and the facilitator's `.env`): `bifrost:bedrock/global.anthropic.claude-haiku-4-5-20251001-v1:0`, through the Bifrost gateway at `BIFROST_URL` with `BIFROST_API_KEY`. Bedrock direct (`bedrock_converse:…`, `AWS_BEARER_TOKEN_BEDROCK`, region `ap-southeast-1`), OpenRouter and OpenAI still work. `MODEL=mock` is the offline fallback; it ignores prompts, so Lab 1 prompt and role steps need a real model.
- Studio graph names (langgraph.json): `lab_1_single_agent`, `lab_2_citizen_platform`, `pattern_1_sequential_pipeline`, `pattern_2_routing`, `pattern_4_parallel_fan_out_gather`, `pattern_3_hierarchical_decomposition`, `pattern_5_generator_critic`.
- Code, `make patterns P=…` values and Studio graph names all use the same names: `lab_1_single_agent`, `lab_2_multi_agent`, `pattern_1_sequential_pipeline` … `pattern_5_generator_critic`. Plain `make patterns` runs all five.

## Naming
- Pattern 2 is called "Routing" everywhere: the guides, the file `pattern_2_routing.py` and its node `router`, matching Anthropic's article. Anthropic's "orchestrator-workers" is what the slide calls Hierarchical Decomposition. The patterns reference sheet carries this mapping; keep it consistent.

## Format decisions
- One lesson per lab or pattern, numbered in workshop order: Lab 1, patterns 1-5, Lab 2 platform.
- Each lesson: the idea (cited), a diagram, numbered steps with predict-then-check reveals, a Studio section, one change to make, a 3-question quiz, a primary source, and a reminder to ask.
- Quiz options in one question have the same word count.
- Learning records are not used: the guides serve many participants, not one learner.
