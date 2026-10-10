# Production source map

Host: `HC-PROD-VPS01`
Captured: 2026-10-10
Git checkout: `C:\HC\deployment\source\Tearsheet-Generator`
Remote: `https://github.com/klefebvre6/Tearsheet-Generator.git`

No secret values are recorded here. `C:\HC\apps` was not modified.

No single branch contains every running component. `origin/main` is `f540135c070b8e2143c098327bc088085e31c94f` (merge of PR #62, 2026-07-22). `origin/live-main` is `3cfda4fdde5eaa8fae42c87b56d30d34aa717f68` (2026-07-31). Both are ancestors of the commits below. Neither contains the October VPS commits. The future combination is in `C:\HC\deployment\GIT_CONSOLIDATION_PLAN.md`. It has not been started.

## Uploader

| | |
| --- | --- |
| Runtime | `C:\HC\apps\uploader` |
| Service | `HC-Uploader-Public` on `127.0.0.1:8091` |
| Branch | `feature/uploader-chart-benchmark-refresh` |
| Commit | `ee9fcfd542a0248467cffddd2e8a93ff76e54175` |
| Remote | `origin/feature/uploader-chart-benchmark-refresh` |
| Exact production code preserved remotely | YES for the chart and benchmark source |

The running backend modules `app\performance.py` and `app\benchmark_store.py` match that commit. SHA-256:

- `performance.py` `592CDD55E6ADEEB3999B5AE9EB30F7EAEB61D94F71BA1297ED05FE719F05CD05`
- `benchmark_store.py` `B91A04183E5E7082579BFAA511B7D52CAD7755E4895F8C9C283D4CE4067AE1A2`

The other deployed `app\*.py` modules match the same tree. `db.py`, `main.py`, and `downstream_export.py` also match `7a935e4` and `815b1d8`. Those three files on `0a157c4` are different blobs, and they are not what `HC-Uploader-Public` runs. The served UI is the built bundle `C:\HC\apps\uploader\static` (not source). Its behavior comes from the frontend files in this commit, including `chartSeriesSelection.ts`.

Persistent data: `C:\HC\data\uploader\uploader_vps_candidate.db`
Benchmark cache: `C:\HC\data\uploader\benchmark_cache`
Runtime config: NSSM environment for `HC-Uploader-Public`. On-disk copy: `C:\HC\config\uploader\uploader.env` (no token).

## TCP

| | |
| --- | --- |
| Runtime | `C:\HC\apps\tcp\tcp_ts_v2.py` |
| Service | `HC-TCP-Public` on `127.0.0.1:8302` |
| Branch | `feature/tcp-benchmark-refresh-comparison-chart` |
| Commit | `815b1d8d607b1dc73fc86d852d64902b2e24acda` |
| Remote | `origin/feature/tcp-benchmark-refresh-comparison-chart` |
| Exact match | YES |

Deployed SHA-256 `CDE21E3FC1922B1D905227FDD08A214C5089D5EBC2E7943E51E8A03636B0355C`. Git blob `5fa6f6752693e73d995f6de0bd19018da3b4952f` is the blob of `tcp_ts_v2.py` in that commit. These other files in `C:\HC\apps\tcp` also match `815b1d8`: `tcp_benchmarks.py`, `tcp_comparison.py`, `tcp_dashboard.py`, `tcp_public_sections.py`, and `assets\styles.css`. See same-named copies below.

Persistent data: `C:\HC\data\tcp\tcp_daily_returns_secret_state.json`
Runtime config: NSSM environment. See the config-drift section. Do not rebuild the service from `C:\HC\config\tcp.env` alone.

## TKP

| | |
| --- | --- |
| Runtime | `C:\HC\apps\tkp\tkp_ts.py` |
| Service | `HC-TKP-Public` on `127.0.0.1:8301` |
| Branch | `refactor/github-vps-deployment-structure` |
| Commit | `0a157c49d769202c1c92590d6acc31ca512588fc` |
| Remote | `origin/refactor/github-vps-deployment-structure` |
| Exact match | YES |

Deployed SHA-256 `86047B1AFFD7ABEB6A0342682FD3B331AE38AAB0131AEBC7139EF63B351F0589`. Git blob `f5a37fed2164912c4196847467c7de523635bed7`.

Persistent data: `C:\HC\data\tkp\daily_returns_secret_state.json`
Runtime config: NSSM environment. On-disk non-secret copy: `C:\HC\config\tkp.env`.

## YQ

| | |
| --- | --- |
| Runtime | `C:\HC\apps\yq\yq_ts.py` |
| Service | `HC-YQ-Public` on `127.0.0.1:8303` |
| Logic commit | `7a935e4e66bcd0983b4ccc7cb962eafeb6db59c0` |
| Logic branch | `origin/feature/vps-yq-loopback-healthz` |
| Path resolver commit | `0a157c49d769202c1c92590d6acc31ca512588fc` |
| Exact production bytes preserved | NO, and they should not be committed |
| Executable source preserved remotely | YES |

Deployed `yq_ts.py` SHA-256 `1E13E9C323928C16A48E6F1ECBB91D6EF8322DEEADB127604119FE4BD22E1C94`.

The file is the committed source with three non-functional differences:

- a UTF-8 BOM
- one extra trailing newline
- non-ASCII punctuation rewritten as CP437 mojibake (box drawing, em dashes, check marks, and the non-breaking space in the column-name cleaner)

Decoding those mojibake characters as CP437 and then as UTF-8 reproduces `yq_ts.py` at `7a935e4`, including the loopback `/healthz` startup. Committing the deployed bytes would put the corrupted strings into Git. The health check, port 8303, and `debug=False` behavior are already in that commit.

`C:\HC\apps\yq\tearsheet_paths.py` is a separate, exact match to `tearsheet_paths.py` at `0a157c4`. On a `vps-*` profile that copy resolves `yq.csv` from the VPS data root before a sibling file. Current HEAD checks the sibling first. The YQ service uses the `0a157c4` order. The TKP and AGM copies do too. `C:\HC\apps\shared\tearsheet_paths.py` matches the sibling-first blob on `7a935e4`, `ee9fcfd`, and `815b1d8`.

`yq_data_current.py` and `tearsheet_disclosure.py` in `C:\HC\apps\yq` match the current checkout.

Persistent data: `C:\HC\data\yq\yq.csv`
Runtime config: NSSM environment, including `YQ_CSV_PATH` and `GLENN_UPLOADER_INGEST_ENABLED=false`.

## AGM

| | |
| --- | --- |
| Runtime | `C:\HC\apps\agm` |
| Entry point | `C:\HC\apps\agm\start_agm.py` |
| Service | `HC-AGM-Public` on `127.0.0.1:8304` |
| Application commit | `0a157c49d769202c1c92590d6acc31ca512588fc` |
| Launcher branch | `preserve/vps-agm-production-20261010` |
| Launcher commit | `5ca9a7c6419559ae1375d8b4adb5533bc0ba16c5` |
| Remote | `origin/preserve/vps-agm-production-20261010` |
| Pushed | YES |

`Momentum Pacer\mp_ts.py` matches `0a157c4`, `815b1d8`, and `7a935e4` (same blob). These deployed files also match `0a157c4` exactly: `tearsheet_paths.py`, `assets\styles.css`, `tcp_public_sections.py`, and `tcp_ts.py`.

The deployed launcher is not that commit. It is a two-line absolute-path script:

SHA-256 `C3F3314FDDFFC3F0B6B1FA55440C9BA1FD98B7C18BE2DA025473391EA1ECCC2B`

```python
import runpy
runpy.run_path(r"C:\HC\apps\agm\Momentum Pacer\mp_ts.py", run_name="__main__")
```

`start_agm.cmd` on the server calls the shared venv with that same absolute path. Classification: STARTUP / DEPLOYMENT/PATH. It does not change tearsheet calculations.

Git now has a repo-relative `start_agm.py` and `start_agm.cmd` on top of `0a157c4`. The Python launcher resolves `Momentum Pacer\mp_ts.py` next to itself and only runs it under `__main__`, so importing the module does not bind port 8304. Checked out, that path exists and `py` parsing succeeded. The server was not started.

Persistent data: `C:\HC\data\agm`
Runtime config: NSSM environment (`HC_AGM_*`, ingest enabled). On-disk non-secret copy: `C:\HC\config\agm.env`.

## Same-named copies

One repo path is deployed as more than one blob. Hashes were compared with `git hash-object` against the five production commits.

| Repo path | Deployed copy | Matches |
| --- | --- | --- |
| `tearsheet_paths.py` | `C:\HC\apps\yq`, `C:\HC\apps\tkp`, `C:\HC\apps\agm` | `0a157c4` and `5ca9a7c` |
| `tearsheet_paths.py` | `C:\HC\apps\shared` | `7a935e4`, `ee9fcfd`, `815b1d8` |
| `tcp_ts_v2.py`, `tcp_benchmarks.py`, `tcp_comparison.py`, `tcp_dashboard.py`, `tcp_public_sections.py`, `assets\styles.css` | `C:\HC\apps\tcp` | `815b1d8` |
| `tcp_ts_v2.py` and the older `tcp_*.py` helpers | `C:\HC\apps\tkp`, `C:\HC\apps\agm` | `0a157c4` and `5ca9a7c` |
| `assets\styles.css` | `C:\HC\apps\tkp`, `C:\HC\apps\yq`, `C:\HC\apps\agm` | `0a157c4` and `5ca9a7c` |
| `assets\styles.css` | `C:\HC\apps\shared` | `7a935e4` and `ee9fcfd` |

The only `tearsheet_paths.py` difference is the order inside `resolve_yq_csv_path`. TCP imports `resolve_tcp_data_root` and `resolve_tcp_ingest_audit_path` from the shared file. Those functions are the same in both blobs. YQ uses its own app-directory copy.

AGM `mp_ts.py` imports `ACCOUNT_STATS_TABLE_CLASS`, `MONTHLY_PERFORMANCE_CLASS`, and `monthly_performance_cell_class` from its app-local `tcp_public_sections.py`. It does not import the nominal-asset tuples. The running TCP service uses the `815b1d8` module: the account-stat label is `$50,000`, and the module includes the comparison chart. The `0a157c4` copy of that module says `$100,000`.

`tkp_ts.py` does not import `tcp_public_sections` or `tcp_ts`. The running TKP behavior is `tkp_ts.py` at `0a157c4`.

## Config drift

Authoritative runtime source for every service is the NSSM `AppEnvironmentExtra` block, not `C:\HC\config\*.env`. The process reads the environment it was started with.

`C:\HC\config\tcp.env` says it is the source of record and contains `GLENN_UPLOADER_INGEST_ENABLED=false`. It has no ingest token. It also sets `TCP_V2_SKIP_BENCHMARK_FETCH=1`.

The running `HC-TCP-Public` environment has ingest enabled. The ingest token, admin token, and session secret are loaded there. `PYTHONPATH` is `C:\HC\apps\shared;C:\HC\apps\tcp`. `TCP_V2_SKIP_BENCHMARK_FETCH` is not set on the service. `C:\HC\secrets\tcp.env` contains the admin token and session secret key names only; it does not contain the Glenn ingest token.

Future rebuild risk: injecting `tcp.env` into NSSM would turn TCP ingest off and would not restore the ingest token. A later fix should refresh `tcp.env` to the live non-secret flags, keep secrets out of that file, and record that the ingest token has to be supplied from the service secret store. Do not change the live service or the env file until that is done on purpose.

The 12:19 automatic backup's `redacted-runtime-env.json` marks secret keys as not loaded. That flag is wrong: a PowerShell `$Matches` overwrite cleared the value before the loaded check. The backup script now saves the value before that test. The tokens themselves were never written into the backup.

## Worktrees left in place

- `C:\HC\deployment\source\Tearsheet-Generator` on `feature/uploader-chart-benchmark-refresh` at `ee9fcfd`
- `C:\HC\deployment\worktrees\tcp-benchmark-refresh-comparison-chart` on `815b1d8`
- `C:\HC\deployment\worktrees\preserve-vps-agm-production-20261010` on `5ca9a7c`
- `C:\HC\deployment\_pr65-deploy` detached at `0a157c4`

Nothing was merged or deleted.
