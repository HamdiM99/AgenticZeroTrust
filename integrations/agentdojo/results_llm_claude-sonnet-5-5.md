# AgentDojo banking with a real LLM: `claude-sonnet-5-5`, attack `important_instructions`

| Configuration | Utility (no attack) | Utility under attack | Attack success rate | Errors |
|---|---|---|---|---|
| undefended | 15/16 (93.8%) | 133/144 (92.4%) | **0/144 (0.0%)** | 0 |
| azt-prompt-nohuman | 9/16 (56.2%) | 78/144 (54.2%) | **0/144 (0.0%)** | 0 |
| azt-known-nohuman | 11/16 (68.8%) | 107/144 (74.3%) | **0/144 (0.0%)** | 0 |
| azt-known-attentive | 16/16 (100.0%) | 133/144 (92.4%) | **0/144 (0.0%)** | 0 |
