# Exercise 1: Experiment with patterns (about 10 minutes)

**Goal:** feel the trade-offs between Sequential, Parallel and Hierarchical designs.

```bash
python -m part2_multi_agent.patterns.run sequential
python -m part2_multi_agent.patterns.run parallel
python -m part2_multi_agent.patterns.run hierarchical
python -m part2_multi_agent.patterns.run generator_critic
python -m part2_multi_agent.patterns.run supervisor_travel
python -m scripts.trace_report --label pattern     # compare response time and LLM calls
```

## Try

1. **Sequential → Parallel.** In `patterns/parallel.py`, add a fourth reviewer (for example a
   `translation_reviewer` that checks the notice would translate cleanly). You only add one entry to
   `REVIEWERS`. Why does the wall-clock time barely change?
2. **Hierarchical.** Change `GOAL` in `patterns/hierarchical.py` to a broader request. How many sub-tasks does
   the planner create? What happens to cost as it grows? Cap it with `plan.subtasks[:N]`.
3. **Generator & Critic.** Tighten `CRITERIA` (for example "max 160 characters"). How many rounds does it take
   now? What stops an endless loop?
4. **Coordinator.** Run `python -m part2_multi_agent.patterns.coordinator "I disagree with my rejection"`.
   Did it reach `complaints_desk`? Add a `translation_desk`.

## Pick the pattern

| Situation | Pattern |
|---|---|
| Fixed steps, same order every time | Sequential |
| Independent checks you want fast | Parallel fan-out |
| Big goal, unknown number of sub-tasks | Hierarchical |
| Output must pass explicit criteria | Generator & Critic |
| One of several specialists should handle it | Coordinator / Supervisor |
