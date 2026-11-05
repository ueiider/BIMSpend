# BIMSpend — Licensing and Dependencies

## Pins

| Source | Revision | License | Conclusion |
|---|---|---|---|
| ActivityWatch bundle | `9fee4702fea08dbe0149cc6e28f4ef66b49f54ec` | MPL-2.0 evidence in umbrella/relevant submodules | file-level copyleft boundary; legal/distribution validation required |
| Miru develop | `10e457e1d0cd2ac782be9d1edbcbd5a1a573486a` | MIT root license | retain copyright/permission notice for copies/substantial portions |
| BIMSpend | `03c47f37ff37f0126170305a1c4f220b9ea22a68` | commercial repository policy still to confirm | do not infer product license from upstream |

Miru `main` was `e8dddef86c0210baf8ac8162139f2db2b0bfa08f` and diverged from the newer `develop` functionality previously audited. Keep `10e457...` for implementation evidence; reassess branch drift before coding.

MPL engineering controls: isolate derived files, preserve headers/notices/license, maintain upstream/local/modification manifest, provide covered source through counsel-approved method, inventory bundled dependencies/assets, and avoid scattering copied fragments through proprietary domain files. This is not legal advice.

MIT permits commercial use/modification/sublicensing subject to notice. Direct Miru copying should remain exceptional because the Rails runtime is incompatible; port behavior and write native tests.

| Candidate dependency | Treatment | Status |
|---|---|---|
| pywin32 306 | likely native capture dependency; pin/scan | **REQUIRES VALIDATION** |
| wmi | measure fallback need and latency; omit if possible | **REQUIRES VALIDATION** |
| requests/persist-queue/aw-server stack | unnecessary for native collector | **DEFER** |
| Peewee/AW datastore | do not vendor; retain BIMSpend SQLite | **DEFER** |
| Qt | port lifecycle concepts; avoid dependency | **PORT LOGIC** |
| Ruby/Rails/PostgreSQL/Miru JS | no desktop runtime dependency | **PORT LOGIC** only |
| Stripe/Razorpay/PayPal | exclude from MVP | **DEFER** |
| PyInstaller/Inno Setup | retain packaging, adapt AW patterns | **ADAPT SOURCE** |

Before build: recursive license/NOTICE inventory; copied/derived manifest and hashes; Python lock and CycloneDX/SPDX SBOM; vulnerability/license scan; installer/runtime asset licenses; Revit SDK redistribution/signing terms; font/icon/fixture provenance.

Stop distribution if provenance is incomplete, MPL source delivery is undefined, incompatible licenses or unreviewed critical vulnerabilities exist, binaries cannot be signed, or privacy tests find raw sensitive titles outside the approved boundary.

No upstream dependency was installed/executed. No SBOM, scan, binary inspection or legal opinion was produced; these remain **REQUIRES VALIDATION**.
