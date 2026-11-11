# Contributing

The software is AGPL-3.0; preserve existing source notices and attribution. Source documents have separate rights. Never contribute real corpus material, generated document text, operational data, credentials or private signing keys.

Agree on changes to public contracts, schemas, processing rights and component ownership before implementation. Work on an isolated feature branch. Make focused commits with DCO sign-off (`git commit -s`) using your configured identity; disclose AI assistance in contributions where applicable.

Python is managed with uv. Each package owns tests; use prepared model artifacts for offline integration checks. Run the checks required by `REVIEW.md`, record commands and outcomes, and report unavailable checks honestly. Never substitute mocked SQLite tests for PostgreSQL/vector/transaction coverage.

For suspected security issues, do not open a public issue containing sensitive content. Contact repository maintainers privately. Do not use production data to reproduce issues.
