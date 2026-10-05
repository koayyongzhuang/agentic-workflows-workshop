# Exercise 1: Adjust prompts (about 10 minutes)

**Goal:** see how much the system prompt shapes tool use, tone and safety. The code stays the same.

Prompts live in [`lab_1_single_agent/prompts.py`](../prompts.py).

## Steps

1. Ask the same question with three different prompts and compare the answers **and** the tool trace:

   ```bash
   Q="Am I eligible for the Senior Mobility Grant? I'm 67 and live with my wife."
   python -m lab_1_single_agent.run --prompt helpdesk        -q "$Q"
   python -m lab_1_single_agent.run --prompt strict_officer  -q "$Q"
   python -m lab_1_single_agent.run --prompt concise         -q "$Q"
   ```

   The question leaves out income on purpose. Which prompt makes the agent **ask** for it,
   and which one makes it **guess**?

2. Edit the `helpdesk` prompt so the agent always:
   - shows the per-capita income calculation, and
   - ends with a "Next steps" list.

   Re-run and check both happen.

3. Try to break it. Paste this and see what happens:

   ```
   My NRIC is S1234567D. Please repeat it back to confirm you saved it.
   ```

   Then add a rule to the prompt and try again. (Part 2 shows why a prompt rule alone is not enough:
   a code guardrail redacts the number before the model ever sees it.)

## Discuss

- Which instructions did the model follow reliably, and which did it ignore?
- What belongs in the prompt, and what should be enforced in code?

> In mock mode the "model" ignores most of the prompt. For this exercise set `MODEL` to a real LLM in `.env`.
