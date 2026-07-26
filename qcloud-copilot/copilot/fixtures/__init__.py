"""P5.5 — product API fixtures (Monitor / CVM / CLS).

Each sub-package (`monitor`, `cvm`, `cls`) exposes five pure-data
factories: `*_success`, `*_failure`, `*_retry`, `*_rate_limited`,
`*_no_pricing_set`. All return `list[UsageEvent]` so they can plug into
`compute_cost` / `usage_stats` / `langfuse_exporter` / `quality_report`
without any I/O.
"""
