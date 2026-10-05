# Exercise 1: Experiment with patterns (about 10 minutes)

**Goal:** feel the trade-offs between Sequential, Parallel and Hierarchical designs.

```bash
python -m lab_2_multi_agent.patterns.run pattern_1_sequential_pipeline
python -m lab_2_multi_agent.patterns.run pattern_3_parallel_fan_out_gather
python -m lab_2_multi_agent.patterns.run pattern_4_hierarchical_decomposition
python -m lab_2_multi_agent.patterns.run pattern_5_generator_critic
python -m scripts.trace_report --label pattern     # compare response time and LLM calls
```

## Try

1. **Sequential → Parallel.** In `patterns/pattern_3_parallel_fan_out_gather.py`, add a fourth reviewer (for example a
   `translation_reviewer` that checks the notice would translate cleanly). You only add one entry to
   `REVIEWERS`. Why does the wall-clock time barely change?
2. **Hierarchical.** Change `GOAL` in `patterns/pattern_4_hierarchical_decomposition.py` to a broader request. How many sub-tasks does
   the planner create? What happens to cost as it grows? Cap it with `plan.subtasks[:N]`.
3. **Generator & Critic.** Tighten `CRITERIA` (for example "max 160 characters"). How many rounds does it take
   now? What stops an endless loop?
4. **Coordinator.** Run `python -m lab_2_multi_agent.patterns.pattern_2_orchestrator "I disagree with my rejection"`.
   Did it reach `complaints_desk`? Add a `translation_desk`.

## Pick the pattern

| Situation | Pattern |
|---|---|
| Fixed steps, same order every time | Sequential |
| Independent checks you want fast | Parallel fan-out |
| Big goal, unknown number of sub-tasks | Hierarchical |
| Output must pass explicit criteria | Generator & Critic |
| One of several specialists should handle it | Coordinator / Supervisor |
