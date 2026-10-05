# Performance

DBeeApp is designed for short-lived, sequential jobs. Its primary performance choices are lazy connections, one reused session per database, bounded result retention, a PostgreSQL server-side cursor for stream mode, and no pool/concurrency/daemon.

## Initial Observation

One run per scenario was measured locally; these are sanity observations, not statistically meaningful benchmarks or production predictions.

| Scenario | Wall | User CPU | System CPU | Input |
| --- | ---: | ---: | ---: | --- |
| CLI startup (`version`) | 0.04 s | 0.02 s | 0.00 s | Python 3.13.13 |
| Small SQL workflow | 0.15 s | 0.07 s | 0.02 s | One control DB query |
| Cross-database workflow | 0.16 s | 0.09 s | 0.02 s | Control -> reporting -> control |
| Sequential SQL | 0.15 s | 0.08 s | 0.02 s | 20 bound SELECT steps on a reused reporting session |
| Streamed output | 0.14 s | 0.10 s | 0.02 s | 10,000 rows to JSONL using server-side cursor |

Environment: macOS 26.6.2 arm64, Python 3.13.13, Docker PostgreSQL 16.4 (Debian image), pg8000 1.31.5, local loopback connections. Containers were warm. Peak RSS and repeated-run distributions were not measured. Do not use these numbers to estimate RHEL or remote-database performance.

For stronger results, repeat with warm/cold runs and record median/range and peak RSS. See `TESTING.md` for the testbed and workflow commands.
