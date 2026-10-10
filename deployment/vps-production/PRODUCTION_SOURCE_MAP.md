# Production source map

Host: `HC-PROD-VPS01`
Captured: 2026-10-10
Git checkout: `C:\HC\deployment\source\Tearsheet-Generator`
Remote: `https://github.com/klefebvre6/Tearsheet-Generator.git`

## Current freeze

Primary production source branch: `production/vps-baseline`.
Baseline SHA: `472e1ddfad38382bf0e5f96813867b0de4ab5b9b`.
This freeze includes the TKP/YQ footer fix from `be11d51a45e3ad173acf90f9941298bcbea2da2d` (`origin/fix/vps-tearsheet-footer-overlap-20261010`). AGM was audited and left unchanged. Uploader remains `ee9fcfd`. TCP executable Python and `assets/styles.css` LF-match unpushed local `b43d93ffebb3d97ff55ea61d7b3742e71968eeb1`; live `assets/nav_chart_fit.js` is newer than that commit and is copied into the baseline. Historical lineage below is preserved.

No secret values are recorded here. `C:\HC\apps` was not modified by this freeze.

`origin/main` is `f540135c070b8e2143c098327bc088085e31c94f`. `origin/live-main` is `3cfda4fdde5eaa8fae42c87b56d30d34aa717f68`. Neither is the current VPS baseline.

Lane C rechecked this map on 2026-10-10 and did not modify `C:\HC\apps`. The afternoon closeout below is the later TCP reading. Where it conflicts with the Lane C TCP paragraphs, use the closeout.

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
| Matching local commit | `b43d93ffebb3d97ff55ea61d7b3742e71968eeb1` |
| Matching remote feature tip | `origin/feature/tcp-benchmark-refresh-comparison-chart` is `662ae032bcbcc685bc76c3ae19c636bf5f55935e` (short of `816fc75` and `b43d93f`) |
| Preserve branch | `preserve/vps-tcp-production-20261010` at `16c85b09` |
| Mixed tree | YES for `assets/nav_chart_fit.js` only; all other executable/UI `.py` and `assets/styles.css` LF-match `b43d93f` |

`16c85b09` is a single-parent child of `ee48aef`. Subject: `Preserve deployed TCP production UI and dashboard changes`. It is the evidence-hash layout hotfix only, and it is not the later percent-axis commit `9c42e670b045465f5bf248a3292100e82342aa50`. The preserve commit changes three files and does not change `tcp_ts_v2.py`:

- `tcp_dashboard.py`: NAV chart bottom margin 36 to 52. Blob `dce3dd4c0b95516ffcfc86f3f88ec4c26b4cf593`. Raw SHA-256 `484cf5262a726e965906802de0a499f02bc90859e2de55420a47981653c77e1c`.
- `tcp_public_sections.py`: footnote and chart class changes. Blob `6c0a669df3722845750d8ef3786c8336f9959890`. Raw SHA-256 `ca097e65db4f786c096805383536413b3d29787b67a4bef58c67cc7bc01da03e`.
- `assets/styles.css`: plot clipping. Blob `f89b16f2540c7ae28cb894fda7dd61a5ac0d4b47`. Raw SHA-256 `edf1ec68db25ecb07389ea9c2decc3331574b8461ea6097ed9578d49c59a08ac`.

`ee48aef` remains the overlay parent (single parent `815b1d8`, subject `Merge BTC/ETH overlays into the TCP NAV chart instead of a separate comparison chart`). `tcp_ts_v2.py` at `16c85b09` is still blob `ebb0e6763f18aef131eb1edc801e8ca015283463`, raw SHA-256 `0f3db05c36c6351b1f48849ce34a858979ade73f8f11d280bf4f64154b1d6718`.

Re-hashed during this closeout, these four live files differ from `16c85b09` on raw bytes and after LF normalization. They were not copied into Git here, and `C:\HC\apps` was not modified.

| Live file | Raw SHA-256 | Length | Versus `16c85b09` | Versus `b57fe5e` |
| --- | --- | --- | --- | --- |
| `assets\styles.css` | `94558e377ec026067b3854e5322124ed4115d12dc4825d8af065f2ef17a8551c` | 21359 | differs | LF match, raw CRLF differs |
| `tcp_dashboard.py` | `cf3d8d59df23a3f70f0a2604e706f16405f1a0b5a9a6827b5a458c5673a4211e` | 27235 | differs | LF match, raw CRLF differs |
| `tcp_public_sections.py` | `a2f109da78f8c01683c12061b3ecf298709553232b5e9b6cf303b1ece076d206` | 39542 | differs | LF match, raw CRLF differs |
| `tcp_ts_v2.py` | `2b7b0555589e3ce4ea10a795c955f50f070a0425c91154f1554b98a69b46ba62` | 66835 | differs | LF match, raw CRLF differs |

`b57fe5e` (2026-10-10 14:48:27 -0400, subject `Fix TCP NAV chart section layout and responsive spacing`, parent `e30bcc101d54bed9a80a2ec9c630f9886a4219a6`) is the feature-branch tip and is on origin. It contains `9c42e67`. It does not contain `16c85b09`. This closeout did not create or push it. `tcp_benchmarks.py`, `tcp_comparison.py`, and `tcp_nav_overlays.py` match both `16c85b09` and `b57fe5e` after LF normalization. Their deployed copies are CRLF.

The afternoon TCP recycles were explicit `Restart-Service -Name HC-TCP-Public -Force` from Cursor agent PowerShell, not crashes. Windows recovery did not fire. The Flask reloader did not fire. NSSM kill exit code was 0. Evidence is `C:\HC\deployment\TCP_RECYCLE_INVESTIGATION.md`. Recycle 1 was 2026-10-10 13:13:15.762, running again 13:13:27, service pid 4088 then 5972. Recycle 2 was 13:44:30.282, running again 13:44:43, new pid 5756. The same pattern continued through 14:37:19, when NSSM pid 9428 started at 14:37:20 with listener pid 12008. That pid did not stay. A further recycle during this closeout left the service Running as NSSM pid 12104, started 2026-10-10 14:56:13, listener pid 8232 on `127.0.0.1:8302`. healthz was HTTP 200, `debug` false, `state_revision` 89. This closeout did not restart it.

A separate `python tcp_ts_v2.py` listens on `127.0.0.1:8312`. It is not `HC-TCP-Public`. The 14:09:25 process pid 11060 was gone by the end of this closeout. The listener then was pid 9292, started 14:46:27, parent 8624. This closeout did not kill it.

Persistent data: `C:\HC\data\tcp\tcp_daily_returns_secret_state.json`
Runtime config: NSSM environment. See the config section. Live `tcp.env` has ingest enabled and does not set `TCP_V2_SKIP_BENCHMARK_FETCH`.

## TKP

| | |
| --- | --- |
| Runtime | `C:\HC\apps\tkp\tkp_ts.py` |
| Service | `HC-TKP-Public` on `127.0.0.1:8301` |
| Footer-fix source | `be11d51a45e3ad173acf90f9941298bcbea2da2d` |
| Title helper lineage | `0a157c49d769202c1c92590d6acc31ca512588fc` |
| Baseline | `production/vps-baseline` contains the deployed `tkp_ts.py` after LF normalize |
| Exact match to `be11d51` `tkp_ts.py` | NO — production keeps the nominal title helper |
| Exact match to baseline `tkp_ts.py` | YES after CRLF/LF |

Persistent data: `C:\HC\data\tkp\daily_returns_secret_state.json`
Runtime config: NSSM environment. On-disk non-secret copy: `C:\HC\config\tkp.env`.

## YQ

| | |
| --- | --- |
| Runtime | `C:\HC\apps\yq\yq_ts.py` |
| Service | `HC-YQ-Public` on `127.0.0.1:8303` |
| Footer-fix source | `be11d51a45e3ad173acf90f9941298bcbea2da2d` |
| Logic parent | `7a935e4e66bcd0983b4ccc7cb962eafeb6db59c0` |
| Exact production bytes preserved | NO — BOM, CRLF, CP437 mojibake on 106 lines. Do not commit those bytes. |
| Executable source preserved remotely | YES — `yq_ts.py` at `be11d51` / baseline |

Deployed `yq_ts.py` SHA-256 `1E13E9C323928C16A48E6F1ECBB91D6EF8322DEEADB127604119FE4BD22E1C94`.

The file is the committed source with four non-functional differences:

- a UTF-8 BOM
- CRLF line endings (the git blob is LF)
- one extra trailing newline after the CP437 repair
- non-ASCII punctuation rewritten as CP437 mojibake on 106 lines (box drawing, em dashes, check marks, and the non-breaking space in the column-name cleaner)

Strip the BOM, encode that text as CP437, turn CRLF into LF, and drop one trailing newline. The result is `yq_ts.py` at `7a935e4`, including the loopback `/healthz` startup. 2,034 lines already match the blob. Zero lines differ after the repair. Committing the deployed bytes would put the corrupted strings into Git. The health check, port 8303, and `debug=False` behavior are already in that commit.

`C:\HC\apps\yq\tearsheet_paths.py` is a separate, exact match to `tearsheet_paths.py` at `0a157c4`. On a `vps-*` profile that copy resolves `yq.csv` from the VPS data root before a sibling file. Current HEAD checks the sibling first. The YQ service uses the `0a157c4` order. The TKP and AGM copies do too. `C:\HC\apps\shared\tearsheet_paths.py` matches the sibling-first blob on `7a935e4`, `ee9fcfd`, `815b1d8`, and `ee48aef`.

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

`Momentum Pacer\mp_ts.py` is the same blob on `0a157c4`, `5ca9a7c`, `7a935e4`, `ee9fcfd`, `815b1d8`, and `ee48aef`. These deployed files also match `0a157c4` exactly: `tearsheet_paths.py`, `assets\styles.css`, `tcp_public_sections.py`, and `tcp_ts.py`.

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

One repo path is deployed as more than one blob. Lane C compared hashes with `git hash-object` against `ee9fcfd`, `815b1d8`, `7a935e4`, `0a157c4`, `5ca9a7c`, and local `ee48aef`. The TCP rows below were rechecked at the afternoon closeout against `16c85b09` and `b57fe5e`.

| Repo path | Deployed copy | Matches |
| --- | --- | --- |
| `tearsheet_paths.py` | `C:\HC\apps\yq`, `C:\HC\apps\tkp`, `C:\HC\apps\agm` | `0a157c4` and `5ca9a7c` |
| `tearsheet_paths.py` | `C:\HC\apps\shared` | `7a935e4`, `ee9fcfd`, `815b1d8` |
| `tcp_comparison.py`, `tcp_nav_overlays.py`, `tcp_benchmarks.py` | `C:\HC\apps\tcp` | LF match of `16c85b09` and `b57fe5e`. Deployed bytes are CRLF. |
| `tcp_ts_v2.py`, `tcp_dashboard.py`, `tcp_public_sections.py`, `assets\styles.css` | `C:\HC\apps\tcp` | Differ from `16c85b09`. LF match of origin `b57fe5e`. Raw CRLF bytes are not that blob. |
| `tcp_ts_v2.py` and the older `tcp_*.py` helpers | `C:\HC\apps\tkp`, `C:\HC\apps\agm` | `0a157c4` and `5ca9a7c` |
| `assets\styles.css` | `C:\HC\apps\tkp`, `C:\HC\apps\yq`, `C:\HC\apps\agm` | `0a157c4` and `5ca9a7c` |
| `assets\styles.css` | `C:\HC\apps\shared` | `7a935e4` and `ee9fcfd` |

The only `tearsheet_paths.py` difference is the order inside `resolve_yq_csv_path`. TCP imports `resolve_tcp_data_root` and `resolve_tcp_ingest_audit_path` from the shared file. Those functions are the same in both blobs. YQ uses its own app-directory copy.

AGM `mp_ts.py` imports `ACCOUNT_STATS_TABLE_CLASS`, `MONTHLY_PERFORMANCE_CLASS`, and `monthly_performance_cell_class` from its app-local `tcp_public_sections.py`. It does not import the nominal-asset tuples. The deployed TCP account-stat tuple is `$50,000`, the same tuple as `ee48aef`. The `0a157c4` copy of that tuple is `$100,000`. Both copies contain the two-tranche `$100,000 Nominal` sentence.

`tkp_ts.py` does not import `tcp_public_sections` or `tcp_ts`. The running TKP behavior is `tkp_ts.py` at `0a157c4`.

## Config drift

Authoritative runtime source for every service is the NSSM `AppEnvironmentExtra` block, not `C:\HC\config\*.env`. The process reads the environment it was started with.

`C:\HC\config\tcp.env` sets `GLENN_UPLOADER_INGEST_ENABLED=true`. It does not set `TCP_V2_SKIP_BENCHMARK_FETCH`. It has no ingest token.

The running `HC-TCP-Public` environment matches those flags. Ingest is enabled. `PYTHONPATH` is `C:\HC\apps\shared;C:\HC\apps\tcp`. `TCP_V2_SKIP_BENCHMARK_FETCH` is not set on the service. The ingest token, admin token, and session secret are loaded there. Their values are not recorded here. `C:\HC\secrets\tcp.env` contains the admin token and session secret key names only; it does not contain the Glenn ingest token.

An older copy of this paragraph said `tcp.env` had ingest disabled and `TCP_V2_SKIP_BENCHMARK_FETCH=1`. That is not the live file. Do not rebuild TCP from that older description.

The 12:19 automatic backup's `redacted-runtime-env.json` marks secret keys as not loaded. That flag is wrong: a PowerShell `$Matches` overwrite cleared the value before the loaded check. The backup script now saves the value before that test. The tokens themselves were never written into the backup.

## Worktrees left in place

- `C:\HC\deployment\source\Tearsheet-Generator` on `feature/uploader-chart-benchmark-refresh` at `ee9fcfd`. This closeout did not check out another branch.
- `C:\HC\deployment\worktrees\tcp-benchmark-refresh-comparison-chart` on `feature/tcp-benchmark-refresh-comparison-chart` at `b57fe5e`. Untracked `_preview_verify` remains. `_preflight_caches` is gone and was not recreated.
- `C:\HC\deployment\worktrees\preserve-vps-tcp-production-20261010` on `preserve/vps-tcp-production-20261010` at `16c85b09`. Pushed. Not merged.
- `C:\HC\deployment\worktrees\preserve-vps-agm-production-20261010` on `5ca9a7c`
- `C:\HC\deployment\_pr65-deploy` detached at `0a157c4`
- `C:\HC\deployment\worktrees\ops-vps-production-rebuildability-20261010` on `ops/vps-production-rebuildability-20261010` at `68ef046`

`production/vps-baseline` is the current freeze branch. This freeze did not merge it elsewhere, did not restart a service, and did not modify `C:\HC\apps`.
