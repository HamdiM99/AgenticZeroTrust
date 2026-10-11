# AgentDojo banking with a real LLM: `gpt-4o-mini-2024-07-18`, attack `important_instructions`

| Configuration | Utility (no attack) | Utility under attack | Attack success rate | Errors |
|---|---|---|---|---|
| undefended | 9/16 (56.2%) | 61/144 (42.4%) | **70/144 (48.6%)** | 0 |
| azt-prompt-nohuman | 6/16 (37.5%) | 44/144 (30.6%) | **0/144 (0.0%)** | 0 |
| azt-known-nohuman | 6/16 (37.5%) | 43/144 (29.9%) | **0/144 (0.0%)** | 0 |
| azt-known-attentive | 8/16 (50.0%) | 62/144 (43.1%) | **0/144 (0.0%)** | 0 |
