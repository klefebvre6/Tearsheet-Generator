# HC-PROD-VPS01 disaster recovery

This runbook restores production onto a **new** Windows host. It does not reinstall, restart, or reconfigure the healthy services on this machine.

No secret values belong in this file, in `production-services.json`, or in command output. Restore secrets by variable name only.

Service catalog: `C:\HC\deployment\production-services.json`

Installer: `C:\HC\deployment\rebuild\install-production-services.ps1`

The installer defaults to a read-only dry run. `-Apply` is required before it can change a host. If any catalog service already exists, `-Apply` also requires `-ApproveReplace`. Do not pass either switch on HC-PROD-VPS01.

Health check: `C:\HC\deployment\health\verify-autostart.ps1`

Backup: `C:\HC\deployment\backup\backup-hc-production.ps1`

SQLite helper: `C:\HC\deployment\backup\sqlite_consistent_backup.py` (`sqlite3.Connection.backup()`, then `PRAGMA integrity_check`)

## What the automatic backup contains

`C:\HC\backups\automatic\<yyyyMMdd-HHmmss>\` is a data backup, not a system image. `backup-hc-production.ps1` copies:

- `C:\HC\data\tcp`, `C:\HC\data\tkp`, `C:\HC\data\yq`, `C:\HC\data\agm`
- uploader benchmark cache, plus `uploader_vps_candidate.db` through SQLite `Connection.backup()`
- `C:\HC\config`
- `C:\HC\deployment\cloudflare\live\config.yml`
- redacted service metadata

The manifest records `secrets_included: false`. The backup does not contain `C:\HC\apps`, virtual environments, NSSM, cloudflared, tunnel credentials, or token values. Retention deletes only expired timestamp folders under `C:\HC\backups\automatic` (14 days). Do not delete backups as part of recovery.

The on-disk env files match the live non-secret NSSM variables. They still omit every secret variable. See [Intentional differences](#intentional-differences).

## Recovery flow

### 1. Provision the Windows VPS

Create a new Windows Server host. Name it `HC-PROD-VPS01` only when this machine is no longer serving production. Install Windows updates, then confirm the host can reach GitHub and Cloudflare.

### 2. Install prerequisites

Install, without changing this production host:

- Git
- Python 3.10.11 x64 (the live virtual environments report `3.10.11`)
- NSSM, placed at `C:\HC\deployment\tools\nssm\nssm.exe`
- cloudflared 2026.10.0, placed at `C:\HC\deployment\tools\admin\bin\cloudflared.exe`

Do not reinstall NSSM or cloudflared on the current HC-PROD-VPS01. The dry-run does not execute `nssm.exe`.

### 3. Restore the canonical `C:\HC` layout

Create the production directories and keep data, config, secrets, and code separate:

```
C:\HC\apps
C:\HC\backups
C:\HC\config
C:\HC\data
C:\HC\deployment
C:\HC\logs
C:\HC\secrets
```

Runtime trees:

| Path | Role |
| --- | --- |
| `C:\HC\apps\uploader` | Uploader backend (`app\main.py`) and built UI in `static` |
| `C:\HC\apps\uploader\.venv` | Uploader Python 3.10.11 |
| `C:\HC\apps\shared\.venv310` | Shared Python 3.10.11 for TKP, TCP, YQ, and AGM |
| `C:\HC\apps\tkp` | `tkp_ts.py` |
| `C:\HC\apps\tcp` | `tcp_ts_v2.py` |
| `C:\HC\apps\yq` | `yq_ts.py` |
| `C:\HC\apps\agm` | `start_agm.py`; working directory `C:\HC\apps\agm\Momentum Pacer` |
| `C:\HC\data\...` | Persistent tearsheet and uploader data |
| `C:\HC\config\...` | On-disk env copies. Not the NSSM source of truth |
| `C:\HC\secrets\...` | Secret values, outside git and outside the automatic backup |
| `C:\HC\logs\...` | NSSM stdout and stderr |
| `C:\HC\deployment\cloudflare\live\config.yml` | Tunnel ingress |
| `C:\HC\deployment\tools\...` | NSSM and cloudflared binaries |

`C:\HC\apps\*` on the current host are deployed copies, not git checkouts.

### 4. Clone the Git sources

Remote: `https://github.com/klefebvre6/Tearsheet-Generator.git`

Clone that repository on the new host, then materialize each runtime tree from the commit below. Do not copy tokens out of any `.env` file in the repository.

| App | Branch | Commit | What to place |
| --- | --- | --- | --- |
| Uploader | `feature/uploader-chart-benchmark-refresh` | `ee9fcfd542a0248467cffddd2e8a93ff76e54175` | `uploader/backend` contents at `C:\HC\apps\uploader`, so `app\main.py` is the uvicorn target. Build `uploader/frontend` with `npm run build` (Vite writes `dist`) and publish that bundle to `C:\HC\apps\uploader\static`. |
| TCP | `feature/tcp-benchmark-refresh-comparison-chart` | `815b1d8d607b1dc73fc86d852d64902b2e24acda` | Repo-root `tcp_*.py` modules and `assets` used by `tcp_ts_v2.py`, at `C:\HC\apps\tcp` |
| TKP | `refactor/github-vps-deployment-structure` | `0a157c49d769202c1c92590d6acc31ca512588fc` | `tkp_ts.py` and the modules it imports, at `C:\HC\apps\tkp` |
| YQ | `feature/vps-yq-loopback-healthz` | `7a935e4e66bcd0983b4ccc7cb962eafeb6db59c0` | `yq_ts.py` from this commit. `tearsheet_paths.py` from `0a157c49d769202c1c92590d6acc31ca512588fc`. `yq_data_current.py` and `tearsheet_disclosure.py` match the 2026-10-10 source checkout `ee9fcfd`. |
| AGM application | `refactor/github-vps-deployment-structure` | `0a157c49d769202c1c92590d6acc31ca512588fc` | Tearsheet modules and `Momentum Pacer\mp_ts.py` at `C:\HC\apps\agm` |
| AGM launcher | `preserve/vps-agm-production-20261010` | `5ca9a7c6419559ae1375d8b4adb5533bc0ba16c5` | `start_agm.py` and `start_agm.cmd` from this commit, on top of `0a157c4` |
| Shared modules | `refactor/github-vps-deployment-structure` | `0a157c49d769202c1c92590d6acc31ca512588fc` | `tearsheet_*.py` modules at `C:\HC\apps\shared`, because TCP's `PYTHONPATH` is `C:\HC\apps\shared;C:\HC\apps\tcp` |

YQ recovery uses the git file at `7a935e4`, not a byte copy of the deployed `yq_ts.py`. The deployed file has a UTF-8 BOM, an extra trailing newline, and CP437 mojibake. Those bytes should not be committed. The loopback `/healthz` behavior is already in `7a935e4`.

The AGM launcher currently on disk is an absolute-path `runpy` script. Commit `5ca9a7c` is the repo-relative launcher and is the recovery source. The service command stays:

`C:\HC\apps\shared\.venv310\Scripts\python.exe C:\HC\apps\agm\start_agm.py`

with working directory `C:\HC\apps\agm\Momentum Pacer`.

Create the virtual environments after the source trees are in place:

```
py -3.10 -m venv C:\HC\apps\shared\.venv310
C:\HC\apps\shared\.venv310\Scripts\python.exe -m pip install -r C:\HC\apps\shared\requirements.txt
py -3.10 -m venv C:\HC\apps\uploader\.venv
C:\HC\apps\uploader\.venv\Scripts\python.exe -m pip install -r C:\HC\apps\uploader\requirements.txt
```

TKP, YQ, and AGM `requirements.txt` files match that shared stack. The running services use `C:\HC\apps\shared\.venv310`, not a per-app virtual environment. TCP has no separate venv.

### 5. Restore the production data backup

Choose the recovery timestamp under `C:\HC\backups\automatic`. Copy the JSON, CSV, workbook, and AGM data trees back into `C:\HC\data`. Config restoration is step 7. Tunnel files are step 9.

Restore the uploader database with the backup API, not a file copy:

```
C:\HC\apps\uploader\.venv\Scripts\python.exe C:\HC\deployment\backup\sqlite_consistent_backup.py C:\HC\backups\automatic\<stamp>\data\uploader\uploader_vps_candidate.db C:\HC\data\uploader\uploader_vps_candidate.db
```

The helper opens both databases, calls `Connection.backup()`, and requires `PRAGMA integrity_check` to return `ok`. Do this while the uploader service is stopped on the **new** host. Do not copy `uploader_vps_candidate.db` with `Copy-Item`.

Leave `C:\HC\backups\automatic` intact.

### 6. Restore secrets by variable name

Supply values from the password manager into `C:\HC\secrets` or the Apply process environment. Do not paste values into the catalog, this runbook, git, or the on-disk `C:\HC\config` files.

| Service | Variable | Where a value lives today |
| --- | --- | --- |
| `HC-Uploader-Public` | `DOWNSTREAM_INGEST_TOKEN` | Live service environment only. Not in `uploader.env`. Not in a `C:\HC\secrets\*.env` file |
| `HC-TKP-Public` | `GLENN_UPLOADER_INGEST_TOKEN` | `C:\HC\secrets\tkp-ingest.env` |
| `HC-TCP-Public` | `GLENN_UPLOADER_INGEST_TOKEN` | `C:\HC\secrets\tcp-ingest.env` |
| `HC-TCP-Public` | `TCP_V2_ADMIN_TOKEN`, `TCP_V2_SESSION_SECRET` | `C:\HC\secrets\tcp.env` |
| `HC-AGM-Public` | `GLENN_UPLOADER_INGEST_TOKEN` | `C:\HC\secrets\agm-ingest.env` |
| `HC-YQ-Public` | none | Ingest is disabled. Do not add a token |
| `HC-TCP-Public` account | `HC_SVC_HC_TEARSHEETS_PASSWORD` | Windows password for `.\svc_hc_tearsheets`. Apply input only |
| Cloudflared | none in the environment | Credential file `C:\HC\secrets\cloudflare\hc-prod-vps01.json` (field `TunnelSecret`). Not an environment variable |

`DOWNSTREAM_INGEST_TOKEN` is operator-held and is not on disk. It is absent from `C:\HC\secrets`, from `C:\HC\config\uploader\uploader.env`, and from `C:\HC\backups\automatic`. `C:\HC\secrets\uploader\README.txt` records that it was not copied. Do not read that value back out of the live NSSM environment.

The TKP, TCP, and AGM ingest tokens, plus `TCP_V2_ADMIN_TOKEN` and `TCP_V2_SESSION_SECRET`, are restored from the designated secret files by variable name. The installer compares those files to a live service by equality and never prints the values.

`-Apply` will not read `DOWNSTREAM_INGEST_TOKEN` back out of the running service. Before Apply on a new host, the operator supplies that variable in the Apply process, or places it in exactly one `C:\HC\secrets\*.env` file. Also set `HC_SVC_HC_TEARSHEETS_PASSWORD` in that process, and create the local account `svc_hc_tearsheets`.

Create the account before the TCP service. The other services run as `LocalSystem`.

### 7. Restore canonical config from `C:\HC\config`

Copy the backup's `config` tree to `C:\HC\config`. The canonical files are:

- `C:\HC\config\uploader\uploader.env`
- `C:\HC\config\tkp.env`
- `C:\HC\config\tcp.env`
- `C:\HC\config\yq.env`
- `C:\HC\config\agm.env`

These files match the live non-secret NSSM variables, including TCP ingest enabled, TCP `PYTHONPATH=C:\HC\apps\shared;C:\HC\apps\tcp`, and no `TCP_V2_SKIP_BENCHMARK_FETCH`. They omit every secret variable. NSSM does not load them. The service installer builds the environment from the catalog, then adds secret variables from `C:\HC\secrets` or the Apply process.

### 8. Install production services on the new host

Confirm the dry run first. It must not be given `-Apply`:

```
powershell -NoProfile -ExecutionPolicy Bypass -File C:\HC\deployment\rebuild\install-production-services.ps1 -DryRun
```

On the new host, after files and secrets exist and the dry run is clean, recreate services with:

```
powershell -NoProfile -ExecutionPolicy Bypass -File C:\HC\deployment\rebuild\install-production-services.ps1 -Apply
```

Use `-ApproveReplace` only when a named service is already installed and an operator intends to replace it. Do not use `-Apply` or `-ApproveReplace` on the current production host.

NSSM services are created with loopback binds and Automatic startup:

| Service | Application | Arguments | Directory | Account | Bind |
| --- | --- | --- | --- | --- | --- |
| `HC-Uploader-Public` | `C:\HC\apps\uploader\.venv\Scripts\python.exe` | `-m uvicorn app.main:app --host 127.0.0.1 --port 8091` | `C:\HC\apps\uploader` | `LocalSystem` | `127.0.0.1:8091` |
| `HC-TKP-Public` | `C:\HC\apps\shared\.venv310\Scripts\python.exe` | `C:\HC\apps\tkp\tkp_ts.py` | `C:\HC\apps\tkp` | `LocalSystem` | `127.0.0.1:8301` |
| `HC-TCP-Public` | `C:\HC\apps\shared\.venv310\Scripts\python.exe` | `C:\HC\apps\tcp\tcp_ts_v2.py` | `C:\HC\apps\tcp` | `.\svc_hc_tearsheets` | `127.0.0.1:8302` |
| `HC-YQ-Public` | `C:\HC\apps\shared\.venv310\Scripts\python.exe` | `C:\HC\apps\yq\yq_ts.py` | `C:\HC\apps\yq` | `LocalSystem` | `127.0.0.1:8303` |
| `HC-AGM-Public` | `C:\HC\apps\shared\.venv310\Scripts\python.exe` | `C:\HC\apps\agm\start_agm.py` | `C:\HC\apps\agm\Momentum Pacer` | `LocalSystem` | `127.0.0.1:8304` |

TKP and TCP call Flask `app.run` without an explicit host. Flask 3.0.3 defaults to `127.0.0.1`, and the live listeners are `127.0.0.1` only. YQ and AGM pass `host="127.0.0.1"` in code. The uploader command line passes `--host 127.0.0.1`.

Do not build the NSSM environment from `C:\HC\config\*.env` alone. Those files now match the live non-secret flags, including TCP ingest enabled and `PYTHONPATH`, and they still omit every secret variable. The installer adds the secret names from `C:\HC\secrets` or the Apply process environment.

The live `HC-TCP-Public` command line was read again from `HKLM\SYSTEM\CurrentControlSet\Services\HC-TCP-Public\Parameters` after the 2026-10-10 recycle. It is still `C:\HC\apps\shared\.venv310\Scripts\python.exe` with arguments `C:\HC\apps\tcp\tcp_ts_v2.py` and working directory `C:\HC\apps\tcp`. The NSSM python child uses that command and re-execs `C:\Python310\python.exe` with the same script. That re-exec owns `127.0.0.1:8302`. Uploader, TKP, YQ, and AGM follow the same venv re-exec pattern. Process ids change across recycles and are not part of the catalog. Leave the running service as it is.

### 9. Configure the Cloudflare tunnel

Restore `C:\HC\deployment\cloudflare\live\config.yml` and the credential file `C:\HC\secrets\cloudflare\hc-prod-vps01.json`. Do not change Cloudflare DNS in this procedure.

Cloudflared is a native Automatic service running as `LocalSystem`, not an NSSM service:

```
C:\HC\deployment\tools\admin\bin\cloudflared.exe --config C:\HC\deployment\cloudflare\live\config.yml --no-autoupdate tunnel run
```

Tunnel id `05046bb6-0ff3-4024-a869-d609fd7f90c4`, name `hc-prod-vps01`. The yaml stores the id and `credentials-file` path. The name is the tunnel name, not a separate yaml key.

Ingress, then the default `http_status:404`:

| Hostname | Origin |
| --- | --- |
| `uploader.hcresearch.ltd` | `http://127.0.0.1:8091` |
| `tkp-ts.hcresearch.ltd` | `http://127.0.0.1:8301` |
| `tcp-ts.hcresearch.ltd` | `http://127.0.0.1:8302` |
| `yq-ts.hcresearch.ltd` | `http://127.0.0.1:8303` |
| `agm-ts.hcresearch.ltd` | `http://127.0.0.1:8304` |

On a new host the installer creates this service with `sc.exe` only when `-Apply` is passed. Error control on the live service is ignore (`0`). The five Python services use normal (`1`).

### 10. Verify local health

Run:

```
powershell -NoProfile -ExecutionPolicy Bypass -File C:\HC\deployment\health\verify-autostart.ps1
```

Loopback checks in that script:

- `http://127.0.0.1:8091/`
- `http://127.0.0.1:8091/health`
- `http://127.0.0.1:8091/api/export/status`
- `http://127.0.0.1:8091/api/rows/TKP?limit=1`
- `http://127.0.0.1:8301/healthz`
- `http://127.0.0.1:8302/healthz`
- `http://127.0.0.1:8303/healthz`
- `http://127.0.0.1:8304/healthz`

Each app port must have one listener, on `127.0.0.1` only. Uploader `/health` must report live export mode, dry run false, target production, and real writes enabled.

### 11. Verify public health

The same health script checks the tunnel hostnames:

- `https://uploader.hcresearch.ltd/` and `/health`
- `https://tkp-ts.hcresearch.ltd/` and `/healthz`
- `https://tcp-ts.hcresearch.ltd/` and `/healthz`
- `https://yq-ts.hcresearch.ltd/` and `/healthz`
- `https://agm-ts.hcresearch.ltd/` and `/healthz`

Public DNS is already pointed at this tunnel. Recovery does not change DNS records. A failed public check with a passing loopback check means the tunnel or ingress config, not the app bind.

### 12. Verify the uploader database

`verify-autostart.ps1` checks:

- `DATABASE_PATH` is `C:\HC\data\uploader\uploader_vps_candidate.db`
- the path is not a private, preview, chart-fix, or sandbox database
- `PRAGMA integrity_check` is `ok`
- `daily_rows` is populated

The restore helper must already have printed `ok` for the backup API copy.

### 13. Verify TKP, TCP, and AGM writer authority

Writer authority is the live environment, not the service display name.

| Check | Required value |
| --- | --- |
| `HC-TKP-Public` `GLENN_UPLOADER_INGEST_ENABLED` | `true`, token loaded |
| `HC-TCP-Public` `GLENN_UPLOADER_INGEST_ENABLED` | `true`, token loaded |
| `HC-AGM-Public` `GLENN_UPLOADER_INGEST_ENABLED` | `true`, token loaded |
| `HC-YQ-Public` `GLENN_UPLOADER_INGEST_ENABLED` | `false`, no ingest token |
| Uploader `EXPORT_ENABLED` | `true` |
| Uploader `EXPORT_DOWNSTREAM_ENABLED` | `true` |
| Uploader `EXPORT_DRY_RUN` | `false` |
| Uploader `EXPORT_TARGET_ENV` | `production` |
| Uploader `EXPORT_INCLUDE_YQ` | `false` |
| Uploader `YQ_INGEST_URL` | unset |
| Ingest token | one distinct value across the uploader and the TKP, TCP, and AGM writers |

`verify-autostart.ps1` performs these checks and does not print token values.

### 14. Verify Glenn save and export readiness

Readiness is confirmed from the health checks. This step does not submit a login, save a new row, or perform an export.

`verify-autostart.ps1` reads `http://127.0.0.1:8091/api/export/status` and the live export flags. Required readiness:

- export mode live, dry run false, target production, real writes enabled
- `EXPORT_ENABLED=true`, `EXPORT_DOWNSTREAM_ENABLED=true`, `EXPORT_INCLUDE_YQ=false`
- ingest URLs set for TKP, TCP, and AGM
- `YQ_INGEST_URL` unset
- existing manual TKP history at `http://127.0.0.1:8091/api/rows/TKP?limit=1`

Export targets are TKP, TCP, and AGM. YQ is excluded. Exactly one host may accept ingest.

### 15. Verify the backup task and `verify-autostart.ps1`

Confirm scheduled task `HC-Production-Backup` and the health script. Do not run the backup task as part of this check.

Observed on HC-PROD-VPS01:

- State Ready, enabled
- Principal `SYSTEM`, logon `ServiceAccount`, run level Highest
- Action `powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\HC\deployment\backup\backup-hc-production.ps1`
- Daily trigger, start boundary `2026-10-10T02:30:00`, interval 1 day
- `StartWhenAvailable=true`, execution limit `PT2H`, multiple instances `IgnoreNew`
- Last run `2026-10-10 12:19:06`, last result `0`

On a new host, create that task when it is absent, with the same action, principal, daily 02:30 local schedule, and `StartWhenAvailable`. Then confirm it. The service installer does not register the task.

Run the health script once during recovery:

```
powershell -NoProfile -ExecutionPolicy Bypass -File C:\HC\deployment\health\verify-autostart.ps1
```

That script is the checker for steps 10 through 14. It is read-only: it does not start services, export rows, or print secret values. Recovery is complete for this step when the task matches the definition above and the script prints `PASS`.

## Intentional differences

The dry run compares `production-services.json` to the running services. These differences are known. The catalog follows the live service.

1. Non-secret keys in `C:\HC\config\uploader\uploader.env`, `tkp.env`, `tcp.env`, `yq.env`, and `agm.env` match the live NSSM environment. That includes `GLENN_UPLOADER_INGEST_ENABLED=true` for TKP, TCP, and AGM, `false` for YQ, TCP `PYTHONPATH=C:\HC\apps\shared;C:\HC\apps\tcp`, and no `TCP_V2_SKIP_BENCHMARK_FETCH` on the service or in `tcp.env`.
2. Those config files omit secret names. Live NSSM loads `DOWNSTREAM_INGEST_TOKEN` (uploader only; not in a secrets file), `GLENN_UPLOADER_INGEST_TOKEN` (TKP, TCP, AGM), and `TCP_V2_ADMIN_TOKEN` plus `TCP_V2_SESSION_SECRET` (TCP). `-Apply` will not copy `DOWNSTREAM_INGEST_TOKEN` out of the running service.
3. `HC-YQ-Public` has one empty NSSM environment entry. Recreate will not add that empty entry.
4. Cloudflared is a native service. Its image path is `cloudflared.exe`. It is not an NSSM service, and this procedure does not change DNS.
5. Display names `HC Uploader Public (private, writes disabled)` and `HC TCP Public (private pilot)` are the live names. They do not describe writer authority.
6. `HC-TCP-Public` runs as `.\svc_hc_tearsheets`. The password variable is `HC_SVC_HC_TEARSHEETS_PASSWORD`. Dry-run does not read it.
7. TKP, TCP, YQ, and AGM use the shared Python executable as the NSSM application. The script path is `AppParameters`. Uploader uses its own virtual environment. That matches the live services.
8. The deployed AGM `start_agm.py` is the absolute-path launcher. Recovery uses the repo-relative launcher at `5ca9a7c`. The service command line does not change.
9. Deployed `yq_ts.py` is not a byte-for-byte copy of git `7a935e4`. Recovery uses the git file, plus `tearsheet_paths.py` from `0a157c4`.
10. `HC-TCP-Public` Parameters still name `C:\HC\apps\shared\.venv310\Scripts\python.exe` and `C:\HC\apps\tcp\tcp_ts_v2.py` after the 2026-10-10 recycle. The listening process is the venv re-exec `C:\Python310\python.exe` with that same script. The other Python services do the same. Process ids are omitted on purpose.

A dry run that reports any other config drift, or a catalog field that differs from the running service, is a failure. Do not apply it.

## Dry run on this host

```
powershell -NoProfile -ExecutionPolicy Bypass -File C:\HC\deployment\rebuild\install-production-services.ps1 -DryRun
```

The command is read-only: no `nssm.exe`, no `sc.exe`, and no service start or stop. Its process-id snapshot must be unchanged at the end.

On 2026-10-10, after `HC-TCP-Public` was re-read from the registry, that command on HC-PROD-VPS01 exited 0: `DRY-RUN RESULT: PASS` and `MUTATIONS: none`. All six services matched the catalog and stayed Running. The live TCP command line remained `C:\HC\apps\shared\.venv310\Scripts\python.exe` with arguments `C:\HC\apps\tcp\tcp_ts_v2.py`. The only config-file drift was the secret names listed above, plus one empty YQ environment entry. `DOWNSTREAM_INGEST_TOKEN` was present only on the running uploader service.
