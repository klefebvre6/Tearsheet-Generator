# Git consolidation plan

Host: `HC-PROD-VPS01`
Inspected: 2026-10-10
Checkout: `C:\HC\deployment\source\Tearsheet-Generator`
Remote: `https://github.com/klefebvre6/Tearsheet-Generator.git`

This is a read of `git status`, `git worktree list`, and `git ls-remote --heads origin`. Nothing was merged, rebased, pushed, deleted, or committed. The sequence at the bottom does not start now.

## Recommended future baseline

One reviewed branch, named `production/vps-baseline`, created later in a non-production worktree. After that branch is reviewed and pushed, new work uses short-lived feature branches from it.

`origin/main` and `origin/live-main` are not that baseline.

| Ref | Commit | Date | What it is |
| --- | --- | --- | --- |
| `origin/main` | `f540135c070b8e2143c098327bc088085e31c94f` | 2026-07-22 | Merge of PR #62, `fix/tkp-canonical-performance` |
| `origin/live-main` | `3cfda4fdde5eaa8fae42c87b56d30d34aa717f68` | 2026-07-31 | `Add AGM downstream continuity regression coverage` |

Both commits are ancestors of every production tip below. Neither contains the October VPS commits. `live-main`'s `yq_ts.py` is the pre-`/healthz` blob, the same blob still on the TKP line. A later decision can move `main` or `live-main` only after the baseline exists and has been reviewed. That move is not part of creating the baseline.

No merge was performed to test this. The recommendation is the file selection below, because a merge of the two long lines would mix deployed code with undeployed uploader edits.

## Two lines, five commits

The lines fork at `38eb0a2f1bf20248dbb7bec87c49be22a136b394` (2026-08-10, `build: add organized Windows VPS deployment layout`), which is after `live-main`.

YQ / uploader / TCP line, from that fork to the split at `7a935e4`, then two sibling commits:

- `49f8864` fix: complete Windows VPS runtime dependencies
- `a3c61b3` docs: carry forward OVH migration inventory
- `a938b0b` docs: add TCP pilot package
- `9e17622` docs: make Glenn uploader cutover a mandatory TCP pilot gate
- `1bc440b` refactor: normalize OVH VPS root to `C:\HC`
- `ed31242` `feature/ovh-tkp-tcp-agm-ready` — fix: make OVH Python environment reproducible
- `e6297b9` `feature/uploader-program-specific-export`
- `7a935e4` `feature/vps-yq-loopback-healthz`
- then two siblings:
  - `ee9fcfd` `feature/uploader-chart-benchmark-refresh`
  - `815b1d8` `feature/tcp-benchmark-refresh-comparison-chart`

TKP / AGM line, from the same fork through `5ca9a7c`:

- `9f58e8a` Fix TCP drawdown nominal exposure and duration calculations
- `c8b57b5` Redirect Y&Q launcher to live-deploy-main runtime
- `2af844c` Restore Glenn Uploader boot launchers
- `944a552` docs: record OVH VPS deployment target
- `9bba414` `fix/post-ingest-full-recalculation` — Sync local TKP/TCP/uploader export work and migration baselines
- `f415345` refactor: central path resolver and VPS profile defaults
- `ae43728` build: add organized Windows VPS deployment layout
- `dbee9bf` docs: inventory current H&C deployment structure
- `657761b` refactor: centralize deployable app manifests
- `11da73a` build: add reusable Windows VPS deployment scripts
- `26b6da9` refactor: normalize OVH VPS root to `C:\HC`
- `608c56e` fix: make OVH Python environment reproducible
- `0a157c4` `refactor/github-vps-deployment-structure` (local docs call this unmerged PR #65)
- `5ca9a7c` `preserve/vps-agm-production-20261010`

`26b6da9` / `608c56e` on the TKP line and `1bc440b` / `ed31242` on the YQ line share commit subjects. They are different commits.

`ee9fcfd` is 9 commits ahead of `5ca9a7c`. `5ca9a7c` is 14 commits ahead of `ee9fcfd`. Their merge-base is `38eb0a2`.

`ee9fcfd` and `815b1d8` are siblings. Both are children of `7a935e4`. The paths each one changes from `7a935e4` do not overlap.

## Which branch contains each production component

Remote tips match these SHAs. Local branches for the five production refs have no upstream configured, except `feature/ovh-tkp-tcp-agm-ready`. `refactor/github-vps-deployment-structure` is not a local branch; the detached worktree is on that commit.

| Component | Running file | Branch | Commit |
| --- | --- | --- | --- |
| Uploader chart and benchmark | `C:\HC\apps\uploader\app\performance.py`, `benchmark_store.py`, and the chart frontend in that commit | `feature/uploader-chart-benchmark-refresh` | `ee9fcfd542a0248467cffddd2e8a93ff76e54175` |
| Other running uploader `app\*.py` | `C:\HC\apps\uploader\app\` | same blobs on `ee9fcfd`, `815b1d8`, and `7a935e4` | `ee9fcfd` is the uploader tip |
| TCP service | `C:\HC\apps\tcp\tcp_ts_v2.py` plus `tcp_benchmarks.py`, `tcp_comparison.py`, `tcp_dashboard.py`, `tcp_public_sections.py`, `assets\styles.css` | `feature/tcp-benchmark-refresh-comparison-chart` | `815b1d8d607b1dc73fc86d852d64902b2e24acda` |
| TKP service | `C:\HC\apps\tkp\tkp_ts.py` | `refactor/github-vps-deployment-structure` | `0a157c49d769202c1c92590d6acc31ca512588fc` |
| YQ logic | `C:\HC\apps\yq\yq_ts.py` behavior | `feature/vps-yq-loopback-healthz` | `7a935e4e66bcd0983b4ccc7cb962eafeb6db59c0` |
| YQ, TKP, and AGM path resolver | app-local `tearsheet_paths.py` | `refactor/github-vps-deployment-structure` | `0a157c4` (also on `5ca9a7c`) |
| AGM application | `Momentum Pacer\mp_ts.py` | same blob on all five tips | exact match of `0a157c4` |
| AGM repo-relative launcher | `start_agm.py`, `start_agm.cmd` in Git | `preserve/vps-agm-production-20261010` | `5ca9a7c6419559ae1375d8b4adb5533bc0ba16c5` |

`7a935e4` is already inside both `ee9fcfd` and `815b1d8`. `0a157c4` is the parent of `5ca9a7c`. Those containments do not produce one tree that runs production. Each tip is still missing another tip's files:

- `ee9fcfd` has the uploader fix and YQ `/healthz`. It does not have the TCP chart commit, `tkp_ts.py` from `0a157c4`, the vps-before-sibling `tearsheet_paths.py`, or `start_agm.py`.
- `815b1d8` has the TCP chart commit and YQ `/healthz`. It does not have the uploader fix or the TKP/AGM-only files.
- `0a157c4` and `5ca9a7c` have TKP, the vps-before-sibling resolver, and (on `5ca9a7c` only) the repo-relative launcher. Their `yq_ts.py` is the pre-`/healthz` file. Their `performance.py` and `benchmark_store.py` are the pre-fix blobs. Their `tcp_ts_v2.py` does not have the comparison chart.

## What should eventually be consolidated

Build the baseline from `7a935e4`, then add the two sibling diffs, then copy specific files from `0a157c4` and `5ca9a7c`. Tests stay with the code version they cover.

Keep from `ee9fcfd` (disjoint from the TCP sibling):

- `uploader/backend/app/performance.py`
- `uploader/backend/app/benchmark_store.py`
- the benchmark tests and `benchmark_fixtures.py` in that commit
- `uploader/frontend` chart files in that commit, including `chartSeriesSelection.ts`

Keep from `815b1d8` (disjoint from the uploader sibling):

- `tcp_ts_v2.py`, `tcp_benchmarks.py`, `tcp_comparison.py`, `tcp_dashboard.py`, `tcp_public_sections.py`
- `tests/test_tcp_benchmarks.py`, `tests/test_tcp_comparison.py`, `tests/tcp_layout_support.py`
- the `.gitignore` line in that commit
- TCP comparison-chart rules in `assets/styles.css` (see the stylesheet step)

Keep from `7a935e4`, which both siblings already contain:

- `yq_ts.py` with `/healthz`, `debug=False`, `use_reloader=False`, `host=127.0.0.1`, port 8303
- `tests/test_yq_fixture_startup.py` from that commit
- the running uploader modules that match this commit, including `db.py`, `main.py`, and `downstream_export.py`
- `feature/uploader-program-specific-export` (`e6297b9`), which is the parent of `7a935e4`

Copy from `0a157c4` only:

- `tkp_ts.py` (public NAV chart title). Take the TKP test update that belongs with it (`tests/test_tkp_chart_cashflow_performance.py` on that commit).
- `tearsheet_paths.py`, vps data root before a sibling `yq.csv`. This is the file YQ, TKP, and AGM actually load.

Copy from `5ca9a7c` only:

- repo-relative `start_agm.py`
- repo-relative `start_agm.cmd`

Leave these `0a157c4` blobs out of the application baseline. They are not what the running services execute:

- `yq_ts.py` on `0a157c4` has no `/healthz` and still calls `app.run(debug=True, port=8303)`.
- `performance.py` and `benchmark_store.py` on `0a157c4` are the pre-fix blobs.
- `uploader/backend/app/db.py`, `main.py`, `downstream_export.py`, `export_summary.py`, and `ingest_preflight.py` on `0a157c4` differ from the running uploader. The running copies match `ee9fcfd`.
- The uploader export UI on `0a157c4` (`App.tsx`, `ExportActionBar`, `exportStatus`) differs from the running frontend source.
- `test_program_export.py` is absent on `0a157c4` and present on the YQ line. Keep the YQ-line test.
- `tcp_public_sections.py` and `tcp_ts.py` on `0a157c4` change the nominal-asset label from `$50,000` to `$100,000`. `HC-TCP-Public` runs the `815b1d8` module (`$50,000` plus the comparison chart). AGM imports only three class helpers from its older copy, not those tuples. `tkp_ts.py` does not import either module.

`assets/styles.css` is three deployed blobs, all already in Git:

- `C:\HC\apps\tcp\assets\styles.css` matches `815b1d8` (comparison-chart selectors).
- `C:\HC\apps\tkp`, `C:\HC\apps\yq`, and `C:\HC\apps\agm` match `0a157c4` (TKP `#NAV-graph .gtitle` rules, 8 lines).
- `C:\HC\apps\shared\assets\styles.css` matches `7a935e4` and `ee9fcfd`.

The baseline has one `assets/styles.css`. The future edit has to combine the TCP comparison-chart selectors and the TKP title rules on purpose. That combination was not made here.

`C:\HC\apps\shared\tearsheet_paths.py` matches the sibling-first blob. The functions TCP imports from it are the same in both versions. The baseline file is the `0a157c4` order, because that is what the YQ service loads. Updating the shared copy on disk is a later deploy, not part of writing this plan.

PR #65 deployment files (`deployment/windows-vps` manifests and scripts, and the migration docs added on `0a157c4`) are not the live NSSM configuration. NSSM `AppEnvironmentExtra` is the runtime source, as recorded in `PRODUCTION_SOURCE_MAP.md`. Bring those paths across only as an explicit list in a later review. A merge of `0a157c4` into the YQ line would also bring the undeployed uploader edits above. Do not run `deploy-app.ps1`.

## Production code still outside Git

Deployed Python and `.cmd` files under `C:\HC\apps\tcp`, `tkp`, `yq`, `agm`, `shared` (venv excluded), and `C:\HC\apps\uploader\app` were hashed with `git hash-object` and compared to the five commits.

Two launcher files and one encoded YQ file are the only application files that matched none of those commits. That is intentional. Do not byte-copy them.

| Deployed file | Why it is outside Git | What Git already has |
| --- | --- | --- |
| `C:\HC\apps\yq\yq_ts.py` | UTF-8 BOM, one extra trailing newline, and CP437 mojibake of non-ASCII punctuation. SHA-256 `1E13E9C323928C16A48E6F1ECBB91D6EF8322DEEADB127604119FE4BD22E1C94`. | Logic, `/healthz`, and the loopback `app.run` are `yq_ts.py` at `7a935e4` (blob `27c966a354`). Decoding the mojibake reproduces that blob. |
| `C:\HC\apps\agm\start_agm.py` | Absolute-path two-liner. SHA-256 `C3F3314FDDFFC3F0B6B1FA55440C9BA1FD98B7C18BE2DA025473391EA1ECCC2B`. | Repo-relative `start_agm.py` at `5ca9a7c`. |
| `C:\HC\apps\agm\start_agm.cmd` | Calls `C:\HC\apps\shared\.venv310\Scripts\python.exe` on the absolute `mp_ts.py` path. | Repo-relative `start_agm.cmd` at `5ca9a7c` (`python` on `PATH`, script next to the cmd). |

`C:\HC\apps\shared\.venv310\Scripts\pwiz.py` also matched nothing. It is a virtualenv script, not application source.

The served uploader UI is the built bundle `C:\HC\apps\uploader\static`. Its source is the frontend in `ee9fcfd`. This pass did not re-hash that bundle.

## Superseded branches

Do not close or delete these. GitHub PR state was not queried: `gh` is not authenticated on this host. Ancestry below is from the local object store plus `git ls-remote --heads origin`.

Still required as inputs. Not superseded:

- `feature/uploader-chart-benchmark-refresh` `ee9fcfd`
- `feature/tcp-benchmark-refresh-comparison-chart` `815b1d8`
- `feature/vps-yq-loopback-healthz` `7a935e4` (already inside both children; still the named YQ logic commit)
- `refactor/github-vps-deployment-structure` `0a157c4` (not contained in `main` or `live-main`; local migration notes call it unmerged PR #65)
- `preserve/vps-agm-production-20261010` `5ca9a7c`

Superseded as a place to resume production work. Their tips are already inside a production commit. Leave the refs in place until a later cleanup, after the baseline exists.

On the YQ / uploader / TCP line only:

- `feature/uploader-program-specific-export` `e6297b9` — parent of `7a935e4`. The running uploader includes it. The TKP line does not. Keep it by building from the YQ line, not by taking the TKP-line uploader files.
- `feature/ovh-tkp-tcp-agm-ready` `ed31242` — ancestor of `7a935e4`. The TKP line's deployment commits are `608c56e` and `0a157c4`, not this tip.

On the TKP / AGM line only:

- `fix/post-ingest-full-recalculation` `9bba414` — this remote tip is the TKP-line sync commit, and `0a157c4` contains it. It is not the PR #61 merge on `main` (`d3dacc1`). It is not the running uploader.

`origin/main` and `origin/live-main` are older than the VPS work. They are superseded as the description of what this VPS runs. They are not superseded as history, and this plan does not move them.

These 54 remote tips are ancestors of both lines. They are already in every production commit's history. The running TCP chart, uploader benchmark fix, YQ `/healthz`, TKP title, and AGM launcher are all later than this set. `release/tcp-v2-final-candidate` `18db918` and `integration/tcp-v2-final-acceptance` `016695f` are in this set. `feature/uploader-chart-ux-polish` `9f14996` is in this set; the running chart fix is `ee9fcfd`.

- `chore/production-alignment-runbook` `eafa650`
- `chore/tearsheet-git-hygiene` `0ee2807`
- `chore/tearsheet-reorg-prep` `a373e47`
- `chore/tearsheet-repo-map` `cd38bb2`
- `chore/tearsheet-smoke-harness` `27ab872`
- `chore/uploader-professional-cors` `6a761ff`
- `copy/agm-profile-section-copy` `6ff8b06`
- `copy/agm-style-trend-following` `642cda1`
- `feature/algominds-v2-account-registry` `68e853e`
- `feature/algominds-v2-config` `04f5c48`
- `feature/algominds-v2-daily-source` `d73ce37`
- `feature/algominds-v2-fee-engine` `649a343`
- `feature/algominds-v2-isolation` `be8cc3c`
- `feature/algominds-v2-per-account-state` `6827dd3`
- `feature/algominds-v2-profile-settings` `e060f24`
- `feature/algominds-v2-snapshot-identity` `b94a783`
- `feature/algominds-v2-snapshot-state` `cd9c767`
- `feature/algominds-v2-snapshots` `33f769c`
- `feature/algominds-v2-state` `059bfe8`
- `feature/glenn-uploader-downstream-export` `e2d0ef0`
- `feature/path-portability-integration` `9c21a97`
- `feature/reorg-yq-phase1` `fc70ed2`
- `feature/tcp-v2-access-daily-values` `7a377d9`
- `feature/tcp-v2-layout-fixes` `918662d`
- `feature/tcp-v2-migration` `016695f`
- `feature/tcp-v2-mobile-acceptance` `232b24a`
- `feature/tcp-v2-public-shell` `f0005c9`
- `feature/tearsheet-runtime-modes` `5f51c5f`
- `feature/tearsheets-password-gated-admin` `55aad97`
- `feature/uploader-agm-inception` `69676ce`
- `feature/uploader-chart-ux-polish` `9f14996`
- `feature/uploader-dev-hardening` `35ce9de`
- `feature/uploader-dev-hardening-frontend` `67c595a`
- `feature/uploader-downstream-export` `56de88d`
- `feature/uploader-downstream-export-ui` `59f45df`
- `feature/uploader-export-rollback` `b76a2e4`
- `feature/uploader-historical-backfill` `480cc8b`
- `feature/uploader-leverage-simulator` `1db3220`
- `feature/uploader-tkp-equity-display` `9498710`
- `fix/add-row-date-defaults` `cc648dc`
- `fix/agm-monthly-stats-derived` `490b170`
- `fix/agm-nav-title-account-stats` `352504d`
- `fix/data-current-label-sync` `572210b`
- `fix/export-mode-display` `5526a82`
- `fix/suppress-benchmark-warning-wall` `76f408c`
- `fix/tcp-agm-export-display-verification` `8466c31`
- `fix/tearsheet-dirty-root-launch-guard` `62f9257`
- `fix/tearsheet-restart-durability` `4f960ad`
- `fix/tkp-canonical-performance` `0c58f34`
- `fix/tkp-data-current-authoritative-date-clean` `c96a057`
- `fix/tkp-plus500-backfill` `b096072`
- `hotfix/tcp-v2-table-benchmark-auth-choice` `bf1df02`
- `integration/tcp-v2-final-acceptance` `016695f`
- `release/tcp-v2-final-candidate` `18db918`

These 11 remote tips are not in this clone's object store. This lane did not fetch them. They are not classified as superseded, and they are not production sources.

- `chore/tcp-test-runtime-optimization` `cc9d703`
- `chore/track-glenn-uploader-launcher` `94c8f50`
- `feature/algominds-v2-preview-shell` `7b942aa`
- `feature/algominds-v2-tearsheet-parity` `d2fe9a0`
- `feature/tearsheet-gate-ui-consistency` `3fb129d`
- `fix/tkp-data-current-authoritative-date` `cc5e250`
- `fix/uploader-cloudflare-user-agent` `4973684`
- `fix/uploader-save-before-export` `1aaa9d4`
- `hotfix/tcp-v2-production-title` `41c78a9`
- `rescue/live-deploy-main-wip-20260714` `cab827e`
- `rescue/root-wip-20260714` `b7f16cd`

## Worktrees to keep

All four current worktrees stay until `production/vps-baseline` exists. None is dirty except the untracked cache called out below.

| Path | HEAD | Why it stays |
| --- | --- | --- |
| `C:\HC\deployment\source\Tearsheet-Generator` | `ee9fcfd` on `feature/uploader-chart-benchmark-refresh` | Only checkout of the running uploader tip. Clean. |
| `C:\HC\deployment\worktrees\tcp-benchmark-refresh-comparison-chart` | `815b1d8` on `feature/tcp-benchmark-refresh-comparison-chart` | Only checkout of the running TCP chart commit. |
| `C:\HC\deployment\worktrees\preserve-vps-agm-production-20261010` | `5ca9a7c` on `preserve/vps-agm-production-20261010` | Only checkout of the repo-relative AGM launcher. Also contains the `0a157c4` tree. Clean. |
| `C:\HC\deployment\_pr65-deploy` | detached `0a157c4` | Pinned PR #65 snapshot of the TKP and path-resolver tree, without the AGM launcher commit. Clean. |

`C:\HC\deployment\worktrees\tcp-benchmark-refresh-comparison-chart\_preflight_caches` is untracked (`tcp_benchmark_cache.json`, `tcp_benchmark_btc_cache.json`, `tcp_benchmark_eth_cache.json`). It is not source. Another lane may delete that directory if it is unused. Do not depend on it. The TCP worktree itself stays.

`feature/vps-yq-loopback-healthz` does not need its own worktree. Both `ee9fcfd` and `815b1d8` already contain that commit.

## Future sequence

Do not start this sequence now. Do not merge, rebase, push, delete branches, delete worktrees, restart services, or edit `C:\HC\apps`.

1. Leave this document as the review input. Leave `origin/main` at `f540135` and `origin/live-main` at `3cfda4f`.
2. When the work is scheduled, add a new worktree. Create `production/vps-baseline` there from `7a935e4`. Do not use the four worktrees above as the place that moves.
3. Bring in `815b1d8` and `ee9fcfd`. Their diffs from `7a935e4` touch no common path, so this step is the uploader fix plus the TCP chart commit on top of YQ `/healthz`. Review the result. Do not merge it to `main`.
4. Copy `tkp_ts.py` and `tearsheet_paths.py` from `0a157c4`, with the TKP test that matches `tkp_ts.py`. Leave `yq_ts.py` at the `7a935e4` blob. Leave every running uploader path at the `ee9fcfd` blob. Leave the TCP chart paths at the `815b1d8` blobs.
5. Copy `start_agm.py` and `start_agm.cmd` from `5ca9a7c`. Leave the absolute-path launcher and the YQ mojibake out of the commit.
6. Edit `assets/styles.css` so the TCP comparison-chart selectors and the TKP `#NAV-graph .gtitle` rules are both present. Record that edit in the commit message. Do not pick one deployed blob and drop the other.
7. Review the baseline against the running entry points. Expected differences are only the YQ encoding (BOM, trailing newline, mojibake) and the absolute AGM launcher versus the repo-relative one. `db.py`, `main.py`, and `downstream_export.py` must still match the running uploader, not `0a157c4`.
8. In a separate review, list any `deployment/windows-vps` paths from `0a157c4` that should be added without the undeployed uploader edits. Do not run those scripts. Do not close PR #65.
9. Push `production/vps-baseline` only after that review, and set its upstream then. Set upstreams on the five existing production branches only if someone is already pushing them for another reason. This plan does not push.
10. After the baseline is on the remote, cut short-lived feature branches from it. Leave the old heads listed above until a cleanup that is outside this sequence. Do not delete the four worktrees until the baseline commit contains the files they were keeping.

## This pass

Written: `C:\HC\deployment\GIT_CONSOLIDATION_PLAN.md`.

Updated: `C:\HC\deployment\PRODUCTION_SOURCE_MAP.md` with the branch split, the same-named deployed copies, and the uploader modules that match `ee9fcfd` rather than `0a157c4`. The uploader commit `ee9fcfd` and the AGM commit `5ca9a7c` were already recorded and are still current.

Not committed.
