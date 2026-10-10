# Production secret contract

Host: HC-PROD-VPS01
Scope: live NSSM `AppEnvironmentExtra` for HC-Uploader-Public, HC-TKP-Public, HC-TCP-Public, HC-YQ-Public, and HC-AGM-Public.

This document lists variable names only. It contains no secret values and no lengths.

Authoritative runtime is NSSM, not the files in `C:\HC\config`. Those files describe non-secret production behavior. They must not store the variables below.

YQ has no ingest token. `HC-YQ-Public` sets `GLENN_UPLOADER_INGEST_ENABLED=false` and does not set a token variable.

## Ingest tokens

| App | Variable | Required or optional | Current source | Required for rebuild |
| --- | --- | --- | --- | --- |
| Uploader | `DOWNSTREAM_INGEST_TOKEN` | required | NSSM. Not in `C:\HC\secrets`. Not in config. | yes |
| Uploader | `GLENN_UPLOADER_INGEST_TOKEN` | not used | Not set in NSSM. Not in config. The uploader credential name is `DOWNSTREAM_INGEST_TOKEN`. | no |
| TKP | `GLENN_UPLOADER_INGEST_TOKEN` | required | NSSM. Key name also present in `C:\HC\secrets\tkp-ingest.env`. Not in config. | yes |
| TCP | `GLENN_UPLOADER_INGEST_TOKEN` | required | NSSM supplies the running service. Key name also present in `C:\HC\secrets\tcp-ingest.env`. Not in `C:\HC\secrets\tcp.env`. Not in config. | yes |
| AGM | `GLENN_UPLOADER_INGEST_TOKEN` | required | NSSM. Key name also present in `C:\HC\secrets\agm-ingest.env`. Not in config. | yes |
| YQ | none | not used | No ingest token in NSSM or config. | no |

The running service is what NSSM injected. A key name in `C:\HC\secrets` records where that name is stored on disk. This document does not assert that the on-disk copy equals the NSSM copy.

## TCP admin and session

| App | Variable | Required or optional | Current source | Required for rebuild |
| --- | --- | --- | --- | --- |
| TCP | `TCP_V2_ADMIN_TOKEN` | required | NSSM and `C:\HC\secrets\tcp.env`. Not in config. | yes |
| TCP | `TCP_V2_SESSION_SECRET` | required | NSSM and `C:\HC\secrets\tcp.env`. Not in config. | yes |

## Rebuild

Required for rebuild means a replacement `AppEnvironmentExtra` has to include that variable or the service will not match current production. The running copy is the NSSM value. Do not take it from `C:\HC\config`.

No other live `AppEnvironmentExtra` key on these five services matched `TOKEN`, `SECRET`, `PASSWORD`, or `CREDENTIAL`.
