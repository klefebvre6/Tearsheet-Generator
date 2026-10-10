# Git consolidation plan

Host: `HC-PROD-VPS01`
Inspected: 2026-10-10
Checkout: `C:\HC\deployment\source\Tearsheet-Generator`
Remote: `https://github.com/klefebvre6/Tearsheet-Generator.git`

Lane C rechecked the same clone on 2026-10-10 after the ops commit `a3aa50a` was already on origin. That lane did not commit, merge, rebase, push, fetch, delete a branch or worktree, restart a service, or check out another branch. The uploader checkout is still `feature/uploader-chart-benchmark-refresh` at `ee9fcfd`.

`production/vps-baseline` now exists at `472e1ddfad38382bf0e5f96813867b0de4ab5b9b` and is the current VPS source freeze. It includes TKP/YQ footer-fix source `be11d51a45e3ad173acf90f9941298bcbea2da2d`. Do not merge it into `main` or `live-main` yet.

## Closeout correction

This section is the later reading. Where it conflicts with Lane C text below about TCP bytes, the feature-branch tip, or the ops tip, use this section.

`preserve/vps-tcp-production-20261010` is pushed at `16c85b09cc4485c804eae69f5d5ddf89fcb3cfe0`. Parent is `ee48aef6c5f83a81a96c0cc0773af69ccf991e11`. It is not merged. It preserves the evidence-hash layout hotfix only: `tcp_dashboard.py` bottom margin 36 to 52, `tcp_public_sections.py` footnote and chart class changes, and `assets/styles.css` plot clipping. It does not change `tcp_ts_v2.py`. It is not percent-axis commit `9c42e670b045465f5bf248a3292100e82342aa50`.

Four live files under `C:\HC\apps\tcp` still differ from `16c85b09`, raw and after LF normalization:

| Live file | Raw SHA-256 |
| --- | --- |
| `assets\styles.css` | `94558e377ec026067b3854e5322124ed4115d12dc4825d8af065f2ef17a8551c` |
| `tcp_dashboard.py` | `cf3d8d59df23a3f70f0a2604e706f16405f1a0b5a9a6827b5a458c5673a4211e` |
| `tcp_public_sections.py` | `a2f109da78f8c01683c12061b3ecf298709553232b5e9b6cf303b1ece076d206` |
| `tcp_ts_v2.py` | `2b7b0555589e3ce4ea10a795c955f50f070a0425c91154f1554b98a69b46ba62` |

Those four LF-normalized texts match origin `feature/tcp-benchmark-refresh-comparison-chart` at `b57fe5e4a39ccf4c972cb1d59e8d5b6dff11f353` (2026-10-10 14:48:27 -0400, `Fix TCP NAV chart section layout and responsive spacing`). The deployed files are CRLF, so the raw bytes are not the git blobs. `b57fe5e` contains `9c42e67` and does not contain `16c85b09`. This closeout did not create that commit and did not copy the live files into Git. `tcp_benchmarks.py`, `tcp_comparison.py`, and `tcp_nav_overlays.py` match `16c85b09` and `b57fe5e` after LF normalization.

TCP recycles on 2026-10-10 were explicit `Restart-Service -Name HC-TCP-Public -Force` from Cursor agent PowerShell. They were not crashes, not the Flask reloader, and not Windows recovery. NSSM kill exit code was 0. Recycle 1: 13:13:15.762, running 13:13:27, pid 4088 then 5972. Recycle 2: 13:44:30.282, running 13:44:43, pid 5756. The same pattern continued through 14:37:19, when NSSM pid 9428 started at 14:37:20. A further recycle during this closeout replaced it. The final read was NSSM pid 12104, started 2026-10-10 14:56:13, listener pid 8232, healthz HTTP 200. Evidence: `C:\HC\deployment\TCP_RECYCLE_INVESTIGATION.md` covers the recycles through 14:37. This closeout did not restart the service.

Live `C:\HC\config\tcp.env` has `GLENN_UPLOADER_INGEST_ENABLED=true` and does not set `TCP_V2_SKIP_BENCHMARK_FETCH`. The running service matches those flags. Do not describe the live file as ingest-disabled or skip-fetch.

Ops tip is `68ef0465fc63b15faf4205f998921dc3970d617b` on `ops/vps-production-rebuildability-20261010`. Parent of that commit remains `a3aa50a`. The uploader checkout stayed at `ee9fcfd`.

This clone's `remote.origin.fetch` refspec tracks only `feature/ovh-tkp-tcp-agm-ready`. Remote classification used `git ls-remote --heads origin` and the local object store. `gh pr list` was not used.

## Lane C answers

1. **Executable production code outside Git.** The YQ service logic and the AGM application logic are in Git. The deployed `yq_ts.py` bytes and the absolute AGM launcher are the intentional non-commits. The evidence-hash TCP hotfix is `16c85b09` on `preserve/vps-tcp-production-20261010`. Four live `C:\HC\apps\tcp` files still differ from that commit: `assets\styles.css`, `tcp_dashboard.py`, `tcp_public_sections.py`, and `tcp_ts_v2.py`. Their LF-normalized text matches origin `b57fe5e`. The raw CRLF bytes do not. The built uploader files under `C:\HC\apps\uploader\static` are generated output; their source is `ee9fcfd`.

2. **Production-relevant branches.** `feature/uploader-chart-benchmark-refresh` `ee9fcfd` (origin matches). `preserve/vps-tcp-production-20261010` `16c85b09` is pushed and not merged; parent `ee48aef`. `feature/tcp-benchmark-refresh-comparison-chart` origin tip is `b57fe5e` (contains `9c42e67`, does not contain `16c85b09`). `feature/vps-yq-loopback-healthz` `7a935e4`. `refactor/github-vps-deployment-structure` `0a157c4`. `preserve/vps-agm-production-20261010` `5ca9a7c` (origin matches). `ops/vps-production-rebuildability-20261010` current tip `68ef046` (parent `a3aa50a`) is the rebuild snapshot on top of `ee9fcfd` only. `origin/main` `f540135` and `origin/live-main` `3cfda4f` are ancestors of both lines and do not contain the October VPS commits. No local ref and no origin head present in this clone contains `ee9fcfd`, `16c85b09`, and `0a157c4` together.

3. **Superseded branches and PRs.** Do not close them. The 54 remote tips below are still contained in both `ee9fcfd` and `5ca9a7c`. `main` and `live-main` are the only extra heads in that set. The same 11 remote tips are still absent from the clone and stay unclassified. One-line ancestors that are already inside a production commit: `e6297b9`, `ed31242`, and `9bba414`. `0a157c4` is still not in `main` or `live-main`; local notes call it unmerged PR #65. The ops branch is not superseded, and it is not the running tree.

4. **Active useful worktrees.** The uploader checkout at `ee9fcfd`, the TCP feature worktree at `b57fe5e`, the preserve TCP worktree at `16c85b09`, the AGM worktree at `5ca9a7c`, detached `_pr65-deploy` at `0a157c4`, and the ops worktree at `68ef046`.

5. **Stale worktrees.** None. `_preflight_caches` is already gone and was not recreated. The TCP worktree's untracked `_preview_verify` PNGs stay where they are.

6. **Safest eventual consolidation order.** Leave `main` and `live-main` where they are. `production/vps-baseline` remains a later branch. Do not create it in this closeout. When it is created, in a new worktree, start from `7a935e4`, bring in `ee9fcfd` and a TCP commit that matches `C:\HC\apps\tcp`. `16c85b09` is the pushed evidence-hash hotfix and is short of the four live files. `b57fe5e` matches those four after LF normalization and does not contain `16c85b09`. Pick that up on purpose. Then copy `tkp_ts.py` and `tearsheet_paths.py` from `0a157c4`, copy repo-relative `start_agm.py` and `start_agm.cmd` from `5ca9a7c`, and combine `assets/styles.css` on purpose. Do not merge `68ef046` as a substitute tree.

7. **Long-term baseline branch.** `production/vps-baseline`, now created. `origin/main` and `origin/live-main` are not that branch. TKP/YQ footer fix source is `be11d51a45e3ad173acf90f9941298bcbea2da2d`.

8. **Normal future development.** One reviewed production baseline, then short-lived feature branches cut from it. `production/vps-baseline` remains that later branch. The TCP overlay and the layout hotfix landed on preservation checkouts; that is the pattern this workflow replaces.

## Recommended future baseline

One reviewed branch, named `production/vps-baseline`, created later in a new worktree. After that branch is reviewed and pushed, new work uses short-lived feature branches from it.

`origin/main` and `origin/live-main` are not that baseline.

| Ref | Commit | Date | What it is |
| --- | --- | --- | --- |
| `origin/main` | `f540135c070b8e2143c098327bc088085e31c94f` | 2026-07-22 | Merge of PR #62, `fix/tkp-canonical-performance` |
| `origin/live-main` | `3cfda4fdde5eaa8fae42c87b56d30d34aa717f68` | 2026-07-31 | `Add AGM downstream continuity regression coverage` |

Both commits are ancestors of every production tip below. Neither contains the October VPS commits. `live-main`'s `yq_ts.py` is the pre-`/healthz` blob, the same blob still on the TKP line. A later decision can move `main` or `live-main` only after the baseline exists and has been reviewed. That move is not part of creating the baseline.

No merge was performed to test this. The recommendation is the file selection below, because a merge of the two long lines would mix deployed code with undeployed uploader edits.

## Two lines, five commits

The lines fork at `38eb0a2f1bf20248dbb7bec87c49be22a136b394` (2026-08-10, `build: add organized Windows VPS deployment layout`), which is after `live-main`. Their merge-base is that commit. `ee9fcfd` is 9 commits ahead of `5ca9a7c`. `5ca9a7c` is 14 commits ahead of `ee9fcfd`.

The YQ / uploader / TCP history is a single-parent first-parent chain from `38eb0a2`. `49f8864`'s only parent is `38eb0a2`. `ee9fcfd` and `815b1d8` are children of `7a935e4`. `ee48aef6c5f83a81a96c0cc0773af69ccf991e11` is a single-parent child of `815b1d8` (2026-10-10 13:44:01 -0400, subject `Merge BTC/ETH overlays into the TCP NAV chart instead of a separate comparison chart`). That subject is not a two-parent merge. `ee48aef` is the parent of pushed preserve commit `16c85b09`. `origin/feature/tcp-benchmark-refresh-comparison-chart` is `b57fe5e`, not `815b1d8` and not `16c85b09`.

The TKP / AGM first-parent spine is the 14-commit chain ending at `5ca9a7c`. `38eb0a2` is not on that spine. It is the second parent of merge `ae43728`. `f415345` is also a merge; its second parent is `e86c8a9` (`docs: finalize Windows VPS deployment layout`), which is the parent of `38eb0a2`.

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
  - `815b1d8` `feature/tcp-benchmark-refresh-comparison-chart`, then local child `ee48aef` (not on origin)

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

`ee9fcfd` and `815b1d8` are siblings. Both are children of `7a935e4`. The paths each one changes from `7a935e4` do not overlap. The paths `ee48aef` changes from `7a935e4` add `tcp_nav_overlays.py` to the `815b1d8` path list and still do not overlap `ee9fcfd`.

## Which branch contains each production component

Origin matches the SHAs below except for TCP: origin is `815b1d8` and the local branch is `ee48aef`. Local branches for the production refs have no upstream configured, except `feature/ovh-tkp-tcp-agm-ready`. The ops branch also has no upstream configured; origin already has `a3aa50a`. `refactor/github-vps-deployment-structure` is not a local branch; the detached worktree is on that commit. This lane did not set any upstream.

| Component | Running file | Branch | Commit |
| --- | --- | --- | --- |
| Uploader chart and benchmark | `C:\HC\apps\uploader\app\performance.py`, `benchmark_store.py`, and the chart frontend in that commit | `feature/uploader-chart-benchmark-refresh` | `ee9fcfd542a0248467cffddd2e8a93ff76e54175` |
| Other running uploader `app\*.py` | `C:\HC\apps\uploader\app\` | same blobs on `ee9fcfd`, `815b1d8`, and `7a935e4` | `ee9fcfd` is the uploader tip |
| TCP service | Evidence-hash hotfix is preserve `16c85b09`. Four live files differ from that commit and LF-match origin `b57fe5e`. See the closeout correction. | `preserve/vps-tcp-production-20261010` and `feature/tcp-benchmark-refresh-comparison-chart` | preserve `16c85b09cc4485c804eae69f5d5ddf89fcb3cfe0`; origin feature `b57fe5e4a39ccf4c972cb1d59e8d5b6dff11f353` |
| TKP service | `C:\HC\apps\tkp\tkp_ts.py` | `refactor/github-vps-deployment-structure` | `0a157c49d769202c1c92590d6acc31ca512588fc` |
| YQ logic | `C:\HC\apps\yq\yq_ts.py` behavior | `feature/vps-yq-loopback-healthz` | `7a935e4e66bcd0983b4ccc7cb962eafeb6db59c0` |
| YQ, TKP, and AGM path resolver | app-local `tearsheet_paths.py` | `refactor/github-vps-deployment-structure` | `0a157c4` (also on `5ca9a7c`) |
| AGM application | `Momentum Pacer\mp_ts.py` | same blob on all five tips | exact match of `0a157c4` |
| AGM repo-relative launcher | `start_agm.py`, `start_agm.cmd` in Git | `preserve/vps-agm-production-20261010` | `5ca9a7c6419559ae1375d8b4adb5533bc0ba16c5` |

`7a935e4` is already inside `ee9fcfd`, `815b1d8`, and `ee48aef`. `0a157c4` is the parent of `5ca9a7c`. `a3aa50a` contains `ee9fcfd` and the `deployment/vps-production/` snapshot from the ops commit. Those containments do not produce one tree that runs production. Each tip is still missing another tip's files:

- `ee9fcfd` has the uploader fix and YQ `/healthz`. It does not have `ee48aef`, `tkp_ts.py` from `0a157c4`, the vps-before-sibling `tearsheet_paths.py`, or `start_agm.py`.
- `815b1d8` has the earlier TCP chart commit and YQ `/healthz`. It does not have `tcp_nav_overlays.py`, the uploader fix, or the TKP/AGM-only files.
- `ee48aef` has the TCP overlay commit and YQ `/healthz`. It does not have the uploader fix or the TKP/AGM-only files. Preserve child `16c85b09` adds the three-file hotfix and still does not match the four live files. Origin `b57fe5e` LF-matches those four and does not contain `16c85b09`.
- `0a157c4` and `5ca9a7c` have TKP, the vps-before-sibling resolver, and (on `5ca9a7c` only) the repo-relative launcher. Their `yq_ts.py` is the pre-`/healthz` file. Their `performance.py` and `benchmark_store.py` are the pre-fix blobs. Their `tcp_ts_v2.py` does not have the overlay commit.
- `a3aa50a` does not contain `815b1d8`, `ee48aef`, `0a157c4`, or `5ca9a7c`.

## What should eventually be consolidated

Build the baseline from `7a935e4`, then add the uploader diff and the TCP diff, then copy specific files from `0a157c4` and `5ca9a7c`. Tests stay with the code version they cover.

The TCP diff is `ee48aef` only after the uncommitted `C:\HC\apps\tcp` layout edits are themselves a commit that matches those files. Until that commit exists, `ee48aef` is the TCP commit to carry forward, and it is short of `tcp_dashboard.py`, `tcp_public_sections.py`, and `assets/styles.css` as they sit on disk. Do not build the baseline from the dirty TCP worktree.

Keep from `ee9fcfd` (disjoint from the TCP sibling):

- `uploader/backend/app/performance.py`
- `uploader/backend/app/benchmark_store.py`
- the benchmark tests and `benchmark_fixtures.py` in that commit
- `uploader/frontend` chart files in that commit, including `chartSeriesSelection.ts`

Keep from `ee48aef` (disjoint from the uploader sibling; this commit already contains `815b1d8`):

- `tcp_ts_v2.py`, `tcp_benchmarks.py`, `tcp_comparison.py`, `tcp_dashboard.py`, `tcp_public_sections.py`, `tcp_nav_overlays.py`
- `tests/test_tcp_benchmarks.py`, `tests/test_tcp_comparison.py`, `tests/tcp_layout_support.py`
- the `.gitignore` line already in that commit
- `assets/styles.css` as it is in `ee48aef`, then the later layout edits once they are committed (see the stylesheet step)

The 13:54 layout bytes for `tcp_dashboard.py`, `tcp_public_sections.py`, and `assets/styles.css` are the three-file hotfix in preserve commit `16c85b09`. Live copies of those three files, plus `tcp_ts_v2.py`, were newer again at the closeout and differ from `16c85b09`. Their LF-normalized text matches origin `b57fe5e`. Do not treat the Lane C "not in the object store" hashes as the current live files. Do not commit `C:\HC\apps` from this plan.

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
- `tcp_public_sections.py` and `tcp_ts.py` on `0a157c4` use the account-stat tuple `$100,000`. `ee48aef` and the deployed TCP file use `$50,000` for that tuple. Both versions also contain the two-tranche `$100,000 Nominal` sentence. AGM imports only three class helpers from its older copy, not those tuples. `tkp_ts.py` does not import either module.

`assets/styles.css` is still more than one deployed blob:

- `C:\HC\apps\tcp\assets\styles.css` differs from `16c85b09` and LF-matches `b57fe5e`. `ee48aef`'s stylesheet has no `#NAV-graph .gtitle` rules. `815b1d8`'s comparison-chart selectors are not the deployed sheet.
- `C:\HC\apps\tkp`, `C:\HC\apps\yq`, and `C:\HC\apps\agm` match `0a157c4` and `5ca9a7c`, including the `#NAV-graph .gtitle` rules.
- `C:\HC\apps\shared\assets\styles.css` matches `7a935e4` and `ee9fcfd`.

The baseline has one `assets/styles.css`. The future edit has to combine the committed TCP sheet (after the layout edits are in that commit) and the TKP `#NAV-graph .gtitle` rules on purpose. That combination was not made here.

`C:\HC\apps\shared\tearsheet_paths.py` matches the sibling-first blob. The functions TCP imports from it are the same in both versions. The baseline file is the `0a157c4` order, because that is what the YQ service loads. Updating the shared copy on disk is a later deploy, not part of writing this plan.

PR #65 deployment files (`deployment/windows-vps` manifests and scripts, and the migration docs added on `0a157c4`) are not the live NSSM configuration. NSSM `AppEnvironmentExtra` is the runtime source, as recorded in `PRODUCTION_SOURCE_MAP.md`. Bring those paths across only as an explicit list in a later review. A merge of `0a157c4` into the YQ line would also bring the undeployed uploader edits above. Do not run `deploy-app.ps1`.

## Production code still outside Git

Deployed `.py`, `.cmd`, `.css`, and `.ps1` files under `C:\HC\apps\tcp`, `tkp`, `yq`, `agm`, `shared`, and `uploader` were hashed with `git hash-object`. Virtualenvs, `__pycache__`, and `node_modules` were skipped. 104 files matched a blob reachable from `ee9fcfd`, `815b1d8`, or `5ca9a7c`. `tcp_ts_v2.py`, `tcp_comparison.py`, and `tcp_nav_overlays.py` match `ee48aef` and are in local Git. `tcp_benchmarks.py` matches both `815b1d8` and `ee48aef`.

These deployed files matched none of those commits:

| Deployed file | Why it is outside Git | What Git already has |
| --- | --- | --- |
| `C:\HC\apps\yq\yq_ts.py` | UTF-8 BOM, CRLF line endings, one extra trailing newline, and CP437 mojibake on 106 lines. SHA-256 `1E13E9C323928C16A48E6F1ECBB91D6EF8322DEEADB127604119FE4BD22E1C94`. | Logic, `/healthz`, and the loopback `app.run` are `yq_ts.py` at `7a935e4`. Strip the BOM, encode the text as CP437, turn CRLF into LF, and drop one trailing newline. That equals the blob. 2,034 lines already match; zero lines differ after that repair. Do not commit the deployed bytes. |
| `C:\HC\apps\agm\start_agm.py` | Absolute-path two-liner. SHA-256 `C3F3314FDDFFC3F0B6B1FA55440C9BA1FD98B7C18BE2DA025473391EA1ECCC2B`. | Repo-relative `start_agm.py` at `5ca9a7c`. |
| `C:\HC\apps\agm\start_agm.cmd` | Calls `C:\HC\apps\shared\.venv310\Scripts\python.exe` on the absolute `mp_ts.py` path. SHA-256 `22A3D5AD83A885BA0D9B94CAB217E866D7589026EC0A30E5077323DAAB77DB3E`. | Repo-relative `start_agm.cmd` at `5ca9a7c` (`python` on `PATH`, script next to the cmd). |
| `C:\HC\apps\tcp\tcp_dashboard.py` | Live raw SHA-256 `cf3d8d59df23a3f70f0a2604e706f16405f1a0b5a9a6827b5a458c5673a4211e` differs from `16c85b09`. The `16c85b09` blob `dce3dd4c0b95516ffcfc86f3f88ec4c26b4cf593` is the margin-52 hotfix. | LF text matches origin `b57fe5e`. |
| `C:\HC\apps\tcp\tcp_public_sections.py` | Live raw SHA-256 `a2f109da78f8c01683c12061b3ecf298709553232b5e9b6cf303b1ece076d206` differs from `16c85b09`. The `16c85b09` blob `6c0a669df3722845750d8ef3786c8336f9959890` is the footnote and chart-class hotfix. | LF text matches origin `b57fe5e`. |
| `C:\HC\apps\tcp\assets\styles.css` | Live raw SHA-256 `94558e377ec026067b3854e5322124ed4115d12dc4825d8af065f2ef17a8551c` differs from `16c85b09`. The `16c85b09` blob `f89b16f2540c7ae28cb894fda7dd61a5ac0d4b47` is the plot-clipping hotfix. | LF text matches origin `b57fe5e`. TKP `#NAV-graph .gtitle` rules remain on `0a157c4`. |
| `C:\HC\apps\tcp\tcp_ts_v2.py` | Live raw SHA-256 `2b7b0555589e3ce4ea10a795c955f50f070a0425c91154f1554b98a69b46ba62` differs from `16c85b09` blob `ebb0e6763f18aef131eb1edc801e8ca015283463`. That preserve commit does not change this file. | LF text matches origin `b57fe5e`. |

The YQ bytes and the absolute AGM launcher stay outside Git on purpose. The four live TCP files above differ from preserve `16c85b09`. Their LF-normalized source is on origin at `b57fe5e`. This closeout did not write them and does not commit them.

`C:\HC\apps\shared\.venv310\Scripts\pwiz.py` also matched nothing. It is a virtualenv script, not application source.

The served uploader UI is the built bundle `C:\HC\apps\uploader\static`. Its source is the frontend in `ee9fcfd`. The built CSS and scripts under that directory are not blobs in `ee9fcfd`, `815b1d8`, `5ca9a7c`, or `ee48aef`.

## Superseded branches

Do not close or delete these. GitHub PR state was not queried. Ancestry below was rechecked from the local object store plus `git ls-remote --heads origin` (76 heads). The 54-tip set is unchanged. The 11 absent tips are unchanged. `ops/vps-production-rebuildability-20261010` is the one origin head that is in the clone and contained in neither production line.

Still required as inputs. Not superseded:

- `feature/uploader-chart-benchmark-refresh` `ee9fcfd`
- `preserve/vps-tcp-production-20261010` `16c85b09` (pushed, not merged; evidence-hash three-file hotfix; short of the four live files)
- `feature/tcp-benchmark-refresh-comparison-chart` origin `b57fe5e` (LF match for the four live TCP files; contains `9c42e67`; does not contain `16c85b09`)
- `feature/vps-yq-loopback-healthz` `7a935e4` (already inside both children and inside `ee48aef`; still the named YQ logic commit)
- `refactor/github-vps-deployment-structure` `0a157c4` (not contained in `main` or `live-main`; local migration notes call it unmerged PR #65)
- `preserve/vps-agm-production-20261010` `5ca9a7c`
- `ops/vps-production-rebuildability-20261010` `68ef046` (parent `a3aa50a`; rebuild docs on top of `ee9fcfd`; not a code union)

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

The current worktrees stay until `production/vps-baseline` exists. That branch remains later. None of these worktrees is the place that creates it.

| Path | HEAD | Why it stays |
| --- | --- | --- |
| `C:\HC\deployment\source\Tearsheet-Generator` | `ee9fcfd` on `feature/uploader-chart-benchmark-refresh` | Only checkout of the running uploader tip. Clean. Do not check out another branch here. |
| `C:\HC\deployment\worktrees\tcp-benchmark-refresh-comparison-chart` | `b57fe5e` on `feature/tcp-benchmark-refresh-comparison-chart` | Feature tip. Untracked `_preview_verify` only. Not the preserve commit. |
| `C:\HC\deployment\worktrees\preserve-vps-agm-production-20261010` | `5ca9a7c` on `preserve/vps-agm-production-20261010` | Only checkout of the repo-relative AGM launcher. Also contains the `0a157c4` tree. Clean. |
| `C:\HC\deployment\_pr65-deploy` | detached `0a157c4` | Pinned PR #65 snapshot of the TKP and path-resolver tree, without the AGM launcher commit. Clean. |
| `C:\HC\deployment\worktrees\preserve-vps-tcp-production-20261010` | `16c85b09` on `preserve/vps-tcp-production-20261010` | Pushed evidence-hash hotfix. Not merged. |
| `C:\HC\deployment\worktrees\ops-vps-production-rebuildability-20261010` | `68ef046` on `ops/vps-production-rebuildability-20261010` | Pushed rebuild snapshot. Do not amend it and do not use it as the place that builds the code baseline. |

`_preflight_caches` under the TCP worktree is absent. It was already removed as unused. Do not recreate it and do not depend on it.

`feature/vps-yq-loopback-healthz` does not need its own worktree. `ee9fcfd`, `815b1d8`, and `ee48aef` already contain that commit.

## Future sequence

Do not start this sequence now. Do not merge, rebase, push, delete branches, delete worktrees, restart services, or edit `C:\HC\apps`.

1. Leave this document as the review input. Leave `origin/main` at `f540135` and `origin/live-main` at `3cfda4f`.
2. When the work is scheduled, add a new worktree. Create `production/vps-baseline` there from `7a935e4`. Do not use the five worktrees above as the place that moves. Do not commit the dirty TCP worktree as that step.
3. Bring in `ee9fcfd` and the TCP commit that matches `C:\HC\apps\tcp`. `ee48aef` is that commit for `tcp_ts_v2.py`, `tcp_benchmarks.py`, `tcp_comparison.py`, and `tcp_nav_overlays.py`. It is not that commit for `tcp_dashboard.py`, `tcp_public_sections.py`, and `assets/styles.css` until those layout edits are committed and the hashes match. Recheck that the TCP path list from `7a935e4` still does not overlap `ee9fcfd`. Review the result. Do not merge it to `main`. Do not push `ee48aef` from this plan. Origin still names `815b1d8`.
4. Copy `tkp_ts.py` and `tearsheet_paths.py` from `0a157c4`, with the TKP test that matches `tkp_ts.py`. Leave `yq_ts.py` at the `7a935e4` blob. Leave every running uploader path at the `ee9fcfd` blob. Leave the TCP paths at the TCP commit from step 3, not at `0a157c4`.
5. Copy `start_agm.py` and `start_agm.cmd` from `5ca9a7c`. Leave the absolute-path launcher and the YQ mojibake out of the commit.
6. Edit `assets/styles.css` so the committed TCP NAV-chart rules and the TKP `#NAV-graph .gtitle` rules from `0a157c4` are both present. Record that edit in the commit message. `ee48aef` does not contain the `.gtitle` rules. The current deployed TCP sheet is not yet that commit.
7. Review the baseline against the running entry points. Expected differences are the YQ encoding (BOM, CRLF, trailing newline, mojibake) and the absolute AGM launcher versus the repo-relative one. TCP dashboard, public sections, and `assets/styles.css` must match the commit chosen in step 3, including the layout edits if those are what `C:\HC\apps\tcp` still runs. `db.py`, `main.py`, and `downstream_export.py` must still match the running uploader, not `0a157c4`.
8. In a separate review, list any `deployment/windows-vps` paths from `0a157c4` that should be added without the undeployed uploader edits. Do not run those scripts. Do not close PR #65.
9. Push `production/vps-baseline` only after that review, and set its upstream then. Set upstreams on the five existing production branches only if someone is already pushing them for another reason. This plan does not push.
10. After the baseline is on the remote, cut short-lived feature branches from it. Leave the old heads listed above until a cleanup that is outside this sequence. Do not delete the five worktrees until the baseline commit contains the files they were keeping.

## This pass

The afternoon closeout updated `C:\HC\deployment\GIT_CONSOLIDATION_PLAN.md` and `C:\HC\deployment\PRODUCTION_SOURCE_MAP.md` with preserve commit `16c85b09`, the three-file hotfix, the four live files that still differ from that commit, and the TCP recycle finding. Live `tcp.env` has ingest enabled and does not set `TCP_V2_SKIP_BENCHMARK_FETCH`.

The uploader checkout stayed on `ee9fcfd`. `_preflight_caches` was not recreated. `production/vps-baseline` was not created. No service was restarted. `C:\HC\apps` was not modified.
