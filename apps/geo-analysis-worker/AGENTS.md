# AGENTS.md

Local rules for the GEO Analysis worker. Extends the root `AGENTS.md`.

## Local Context

- This app consumes GEO query run jobs from RabbitMQ and delegates behavior to
  `younilab_seo.geo_analysis` application use cases.
- Validate with `uv run --package younilab-geo-analysis-worker pytest apps/geo-analysis-worker/tests`.

## Boundaries

- Do not implement AI provider calls directly in this app.
- Call `geo-tracking-api` through the package infrastructure client.
- Persist raw run results and references only through
  `younilab_seo.geo_analysis` application use cases and repository ports.
- Do not parse mention, citation normalization, sentiment, visibility, SOV, or
  report metrics in this app.
- Keep runtime dependency construction in `composition.py`; keep worker loop
  coordination in `worker.py`.
