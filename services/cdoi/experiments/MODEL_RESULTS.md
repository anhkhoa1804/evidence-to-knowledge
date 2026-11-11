# Model Results

| Experiment | Dataset | N | Alignment F1 | False Merge | Unresolved | Property F1 | Bridge P | Review Rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| CDOI_LLM_CONTEXT | cdoi_bench | 0 | N/A | N/A | N/A | N/A | N/A | N/A |
| CDOI_REAL_EMBEDDING | cdoi_bench | 0 | N/A | N/A | N/A | N/A | N/A | N/A |
| V26_QWEN_ALIGNMENT | cdoi_bench | 0 | N/A | N/A | N/A | N/A | N/A | N/A |

## Model Status

Rows marked unavailable record no quality result. The deterministic embedding-signal baseline is reported separately from a sentence-transformer or remote-LLM run.

## Execution Notes

- `CDOI_LLM_CONTEXT`: `LLM experiment requires model_config.base_url, model_config.model, and the configured API-key environment variable.`.
- `CDOI_REAL_EMBEDDING`: `embedding_runtime_unavailable:OSError`.
- `V26_QWEN_ALIGNMENT`: `missing_credential`.
