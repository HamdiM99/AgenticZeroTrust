# AgentDojo banking with a real LLM: `zai:glm-4.6`, attack `important_instructions`

| Configuration | Utility (no attack) | Utility under attack | Attack success rate | Model resisted / gateway blocked / attack succeeded / tried, failed otherwise | Errors |
|---|---|---|---|---|---|
| undefended | 12/16 (75.0%) | 118/144 (81.9%) | **3/144 (2.1%)** | 141 / 0 / 3 / 0 | 0 |
| azt-known-attentive | 15/16 (93.8%) | 118/144 (81.9%) | **0/144 (0.0%)** | 141 / 3 / 0 / 0 | 0 |
