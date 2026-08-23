# Laporan Audit Rekonsiliasi PRD

> Read-only. Kandidat gap adalah temuan mekanis untuk direview, bukan kesalahan pasti dan bukan requirement yang disetujui.

- Dibuat (UTC): `2026-08-21T10:48:27.180420+00:00`
- Baseline canonical: `v0.0.0` (`BOOTSTRAPPED`, rilis: `UNRELEASED`, perubahan semantik: `NONE`)

## Ringkasan Global

- Kelompok: **7** | E2E: **23** | PRD unik: **209**
- Kandidat gap (cakupan report): **738** | masih terbuka: **401** | tertutup dari source fact: **218** | dikecualikan: **119**
- Register global: 738 kandidat, 218 tertutup otomatis, 1 menunggu keputusan manusia
- Sesi rekonsiliasi tercatat: **0** | keputusan USER_CONFIRMED: **0** | rilis: **0**
- **Belum ada sesi rekonsiliasi manusia yang tercatat.** Seluruh fix di bawah berasal dari penutupan otomatis source fact.

## Kelompok: administrasi-keuangan

### E2E-BILLING | Billing dan Kasir

- Tujuan: Tagihan, kasir, deposito, dan penerimaan kas.
- PRD: **9** | relasi: 86 | lintas-domain: 58
- Gap terbuka: **18** | fix source fact: **7** | dikecualikan: **3**
- Sesi: belum ada

| Kode | PRD | Stage |
|---|---|---|
| `PRD-BILLING-001` | PRD — Billing/Kasir — Pengelolaan Dana Wadiah / Deposit Pasien (G3) | FOUNDATION |
| `PRD-BILLING-002` | PRD — Billing: Tagihan Pasien (G2) | FOUNDATION |
| `PRD-BILLING-003` | PRD — Pengaturan Tagihan Pasien (A60) | FOUNDATION |
| `PRD-BILLING-004` | PRD — Billing/Kasir: Verifikasi Penerimaan Kas | VALIDATION |
| `PRD-BILLING-005` | PRD — Dashboard Billing (G2c) — Phase 1 Quantity Dashboard | WORKLIST |
| `PRD-BILLING-006` | buka tutup kasir | SETTLEMENT |
| `PRD-BILLING-007` | PRD — Billing: Tagihan Pasien (G2) | SETTLEMENT |
| `PRD-BILLING-008` | PRD — Deposito Pasien (G2a) — Tab Deposito (Tampilan Read-Only) pada Workspace … | SETTLEMENT |
| `PRD-BILLING-009` | PRD — Penjualan Obat Bebas / OTC (G2b) — Tab Penjualan Obat Bebas pada Workspac… | SETTLEMENT |

#### Gap terbuka (18)

| ID | Mode | PRD | Jenis | Status | Bukti |
|---|---|---|---|---|---|
| `AR-ED4A1E1EB4AEF2` | BUSINESS_CASES | `PRD-BILLING-001` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-34062EC4175CB8` | BUSINESS_CASES | `PRD-BILLING-003` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-D19072325B57D7` | BUSINESS_CASES | `PRD-BILLING-003` | ALTERNATE_CASE_CONTEXT | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-636A76F4F20188` | BUSINESS_CASES | `PRD-BILLING-003` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-B4E7246E675DBF` | BUSINESS_CASES | `PRD-BILLING-003` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-AC65E430182A16` | BUSINESS_CASES | `PRD-BILLING-003` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pengaturan (.md)/prd-pengaturan-tagihan-pasien.md:17 |
| `AR-E909B77FB2B56F` | BUSINESS_CASES | `PRD-BILLING-004` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-9B197FDAC63BBF` | BUSINESS_CASES | `PRD-BILLING-004` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Billing/prd-billing-kasir-billing-verifikasi-penerimaan-kas-.md:2… |
| `AR-81F0C7A8DE09A2` | BUSINESS_CASES | `PRD-BILLING-005` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-7E288958DDA5F4` | BUSINESS_CASES | `PRD-BILLING-005` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-A21B8141F78039` | BUSINESS_CASES | `PRD-BILLING-006` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-C3CF3008435159` | BUSINESS_CASES | `PRD-BILLING-008` | ALTERNATE_CASE_CONTEXT | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-1D818030E98614` | BUSINESS_CASES | `PRD-BILLING-008` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-648B65D61A6964` | BUSINESS_CASES | `PRD-BILLING-008` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-AC8B45CAB7FE4D` | BUSINESS_CASES | `PRD-BILLING-008` | VALIDATION_BEHAVIOR | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-E9D10D497FD81B` | BUSINESS_CASES | `PRD-BILLING-009` | ALTERNATE_CASE_CONTEXT | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-4D3B071C634A14` | BUSINESS_CASES | `PRD-BILLING-009` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-0B706A5AD1F922` | BUSINESS_CASES | `PRD-BILLING-009` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |

#### Sudah diperbaiki dari source fact (7)

| ID | Mode | PRD | Jenis | Bukti literal |
|---|---|---|---|---|
| `AR-705DF9AF3E8E8C` | BUSINESS_CASES | `PRD-BILLING-006` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Billing/prd-buka-tutup-kasir.md:210 |
| `AR-8DDAB7FD58F0A8` | BUSINESS_CASES | `PRD-BILLING-007` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Billing/prd-tagihan-pasien.md:517 |
| `AR-16D7AEA220EE52` | BUSINESS_CASES | `PRD-BILLING-007` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Billing/prd-tagihan-pasien.md:515 |
| `AR-70C2F25C7A988D` | MAIN_FLOW | `PRD-BILLING-003` | handoff | PRD/PRD Generator (.md)/Pengaturan (.md)/prd-pengaturan-tagihan-pasien.md:87 |
| `AR-34F37B24E49A18` | MAIN_FLOW | `PRD-BILLING-005` | output | PRD/PRD Generator (.md)/Billing/prd-G2c-Dashboard-Billing.md:90 |
| `AR-8FDBD1DB028A0B` | MAIN_FLOW | `PRD-BILLING-005` | trigger_input | PRD/PRD Generator (.md)/Billing/prd-G2c-Dashboard-Billing.md:90 |
| `AR-E50C9468F5E7C4` | MAIN_FLOW | `PRD-BILLING-008` | trigger_input | PRD/PRD Generator (.md)/Billing/prd-G2a-Deposito-Pasien.md:254 |

#### Keputusan terkonfirmasi (0)

Belum ada keputusan manusia yang tercatat.

### E2E-CASEMIX | Casemix dan Klaim

- Tujuan: Dokumen, pengajuan, penerimaan, dan rekonsiliasi klaim.
- PRD: **5** | relasi: 13 | lintas-domain: 13
- Gap terbuka: **6** | fix source fact: **4** | dikecualikan: **7**
- Sesi: belum ada

| Kode | PRD | Stage |
|---|---|---|
| `PRD-CASEMIX-001` | PRD — Casemix — Pengelolaan Klaim BPJS: Penerimaan & Rekonsiliasi Klaim (G9) | VALIDATION |
| `PRD-CASEMIX-002` | PRD — Casemix — Pengelolaan Klaim BPJS: Managemen Dokumen dan Data Medis (G8) | SETTLEMENT |
| `PRD-CASEMIX-003` | PRD — Casemix: Pengelolaan Klaim Asuransi Swasta (Integrasi SATUSEHAT) | SETTLEMENT |
| `PRD-CASEMIX-004` | PRD — Integrasi E-Klaim: Informasi Hemodialisis dan Kantong Darah (N28) | SETTLEMENT |
| `PRD-CASEMIX-005` | PRD — Casemix: Manajemen Dokumen & Data Medis (G8) | SUPPORTING |

#### Gap terbuka (6)

| ID | Mode | PRD | Jenis | Status | Bukti |
|---|---|---|---|---|---|
| `AR-6046EEAA0095A7` | BUSINESS_CASES | `PRD-CASEMIX-001` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-E07C2447CB7010` | BUSINESS_CASES | `PRD-CASEMIX-003` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-17D7D9BBAEF8E7` | BUSINESS_CASES | `PRD-CASEMIX-004` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Casemix/N28__casemix-integrasi-e-klaim-informasi-hemodialisis-dan… |
| `AR-1A876E732763E6` | BUSINESS_CASES | `PRD-CASEMIX-004` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Casemix/N28__casemix-integrasi-e-klaim-informasi-hemodialisis-dan… |
| `AR-7A67A4FD620E11` | BUSINESS_CASES | `PRD-CASEMIX-005` | ALTERNATE_CASE_CONTEXT | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-01062E498A09DE` | BUSINESS_CASES | `PRD-CASEMIX-005` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |

#### Sudah diperbaiki dari source fact (4)

| ID | Mode | PRD | Jenis | Bukti literal |
|---|---|---|---|---|
| `AR-FE52914B58C282` | BUSINESS_CASES | `PRD-CASEMIX-002` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Casemix/G8__casemix-pengelolaan-klaim-bpjs-managemen-dokumen-dan-… |
| `AR-F63DEA867D5FA0` | BUSINESS_CASES | `PRD-CASEMIX-004` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Casemix/N28__casemix-integrasi-e-klaim-informasi-hemodialisis-dan… |
| `AR-53BCEB38628E6A` | BUSINESS_CASES | `PRD-CASEMIX-004` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Casemix/N28__casemix-integrasi-e-klaim-informasi-hemodialisis-dan… |
| `AR-D256F3E31935D3` | BUSINESS_CASES | `PRD-CASEMIX-005` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Casemix/prd-manajemen-dokumen-casemix.md:175 |

#### Keputusan terkonfirmasi (0)

Belum ada keputusan manusia yang tercatat.

## Kelompok: administrasi-pasien

### E2E-SURAT | Administrasi Surat dan Consent

- Tujuan: Pembuatan surat, persetujuan, penolakan, dan consent.
- PRD: **6** | relasi: 14 | lintas-domain: 13
- Gap terbuka: **7** | fix source fact: **16** | dikecualikan: **2**
- Sesi: belum ada

| Kode | PRD | Stage |
|---|---|---|
| `PRD-SURAT-001` | informasi tindakan kedokteran | EXECUTION |
| `PRD-SURAT-002` | persetujuan penolakan tindakan | EXECUTION |
| `PRD-SURAT-003` | PRD - Pembuatan Surat: Rujuk ke RS Lain (E21) | EXECUTION |
| `PRD-SURAT-004` | PRD - Pembuatan Surat: Surat Keterangan Dokter (E21_SK_DOKTER) | OUTPUT |
| `PRD-SURAT-005` | PRD - Pembuatan Surat: Surat Keterangan Kematian (E21_SK_KEMATIAN) | OUTPUT |
| `PRD-SURAT-006` | PRD - Pembuatan Surat: Surat Keterangan Lahir (E21_SK_LAHIR) | OUTPUT |

#### Gap terbuka (7)

| ID | Mode | PRD | Jenis | Status | Bukti |
|---|---|---|---|---|---|
| `AR-7EA846C295DB11` | BUSINESS_CASES | `PRD-SURAT-001` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Surat Penunjang/prd-informasi-tindakan-kedokteran.md:172 |
| `AR-C9A55B3E953179` | BUSINESS_CASES | `PRD-SURAT-001` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Surat Penunjang/prd-informasi-tindakan-kedokteran.md:53 |
| `AR-D5986E73653935` | BUSINESS_CASES | `PRD-SURAT-001` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Surat Penunjang/prd-informasi-tindakan-kedokteran.md:84 |
| `AR-F18DE5FC6D0E18` | BUSINESS_CASES | `PRD-SURAT-002` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Surat Penunjang/prd-persetujuan-penolakan-tindakan.md:371 |
| `AR-E9199737C8912F` | BUSINESS_CASES | `PRD-SURAT-002` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Surat Penunjang/prd-persetujuan-penolakan-tindakan.md:474 |
| `AR-599593A56476FF` | BUSINESS_CASES | `PRD-SURAT-002` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Surat Penunjang/prd-persetujuan-penolakan-tindakan.md:61 |
| `AR-7C3B402A468B3B` | BUSINESS_CASES | `PRD-SURAT-002` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Surat Penunjang/prd-persetujuan-penolakan-tindakan.md:80 |

#### Sudah diperbaiki dari source fact (16)

| ID | Mode | PRD | Jenis | Bukti literal |
|---|---|---|---|---|
| `AR-C21357DA37F594` | BUSINESS_CASES | `PRD-SURAT-001` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Surat Penunjang/prd-informasi-tindakan-kedokteran.md:68 |
| `AR-7CF0CF55B10251` | BUSINESS_CASES | `PRD-SURAT-001` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Surat Penunjang/prd-informasi-tindakan-kedokteran.md:948 |
| `AR-841BC5443EF89B` | BUSINESS_CASES | `PRD-SURAT-002` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Surat Penunjang/prd-persetujuan-penolakan-tindakan.md:80 |
| `AR-439259D6AE98D6` | BUSINESS_CASES | `PRD-SURAT-002` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Surat Penunjang/prd-persetujuan-penolakan-tindakan.md:853 |
| `AR-0B9CC0B546918A` | BUSINESS_CASES | `PRD-SURAT-003` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-pembuatan-surat-surat-rujuk-ke-rs-lain.md:186 |
| `AR-3F0D0F53EAF4BC` | BUSINESS_CASES | `PRD-SURAT-003` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-pembuatan-surat-surat-rujuk-ke-rs-lain.md:149 |
| `AR-1C2C078D6BE9BE` | BUSINESS_CASES | `PRD-SURAT-003` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-pembuatan-surat-surat-rujuk-ke-rs-lain.md:186 |
| `AR-F6F8665B86AABF` | BUSINESS_CASES | `PRD-SURAT-004` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-surat-keterangan-dokter.md:203 |
| `AR-25D9AD9DB88D68` | BUSINESS_CASES | `PRD-SURAT-004` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-surat-keterangan-dokter.md:173 |
| `AR-4C9C1D53847DC4` | BUSINESS_CASES | `PRD-SURAT-004` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-surat-keterangan-dokter.md:203 |
| `AR-DA946BA35C6F47` | BUSINESS_CASES | `PRD-SURAT-005` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-Pembuatan-Surat-surat-kematian.md:172 |
| `AR-9AEDD4CDE64F95` | BUSINESS_CASES | `PRD-SURAT-005` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-Pembuatan-Surat-surat-kematian.md:172 |
| `AR-C81FD6D0B9759A` | BUSINESS_CASES | `PRD-SURAT-005` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-Pembuatan-Surat-surat-kematian.md:172 |
| `AR-48EA437C7C4372` | BUSINESS_CASES | `PRD-SURAT-006` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-surat-keterangan-lahir.md:180 |
| `AR-19FE3F141D8FEC` | BUSINESS_CASES | `PRD-SURAT-006` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-surat-keterangan-lahir.md:179 |
| `AR-DC8A81CCA9FB2A` | BUSINESS_CASES | `PRD-SURAT-006` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-surat-keterangan-lahir.md:180 |

#### Keputusan terkonfirmasi (0)

Belum ada keputusan manusia yang tercatat.

## Kelompok: backoffice

### E2E-INVENTORY | Inventory dan Pengadaan

- Tujuan: Perencanaan, pemesanan, penerimaan, stok, dan distribusi barang.
- PRD: **14** | relasi: 62 | lintas-domain: 29
- Gap terbuka: **28** | fix source fact: **8** | dikecualikan: **1**
- Sesi: belum ada

| Kode | PRD | Stage |
|---|---|---|
| `PRD-INVENTORY-001` | Pemesanan Barang Barang Farmasi | REQUEST |
| `PRD-INVENTORY-002` | Pemesanan Barang Barang Gizi | REQUEST |
| `PRD-INVENTORY-003` | Pemesanan Barang Barang Rumah Tangga | REQUEST |
| `PRD-INVENTORY-004` | PRD — Inventory: Pemesanan Barang (Farmasi) | REQUEST |
| `PRD-INVENTORY-005` | PRD — Inventory: Rencana Pengadaan Barang (H10) | REQUEST |
| `PRD-INVENTORY-006` | PRD — Pemisahan RI–RJ pada Pemesanan Barang dan Jatah Stok (H1a) | REQUEST |
| `PRD-INVENTORY-007` | PRD — Inventory: Informasi Stok | WORKLIST |
| `PRD-INVENTORY-008` | PRD — Inventory: Distribusi Barang | EXECUTION |
| `PRD-INVENTORY-009` | PRD — Inventory: Penerimaan Barang | EXECUTION |
| `PRD-INVENTORY-010` | PRD — Inventory: Penggunaan Barang Unit (Pemakaian Barang Unit) | EXECUTION |
| `PRD-INVENTORY-011` | PRD — Inventory: Retur Pembelian | EXECUTION |
| `PRD-INVENTORY-012` | PRD — Inventory: Mutasi Stok (Mutasi Barang Antar Unit) | SUPPORTING |
| `PRD-INVENTORY-013` | PRD — Inventory: Peminjaman dan Pengembalian Barang | SUPPORTING |
| `PRD-INVENTORY-014` | PRD — Inventory: Stok Opname | SUPPORTING |

#### Gap terbuka (28)

| ID | Mode | PRD | Jenis | Status | Bukti |
|---|---|---|---|---|---|
| `AR-B90E6AE5D0A161` | BUSINESS_CASES | `PRD-INVENTORY-001` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-A2515F8B3438BC` | BUSINESS_CASES | `PRD-INVENTORY-001` | BUSINESS_RULES | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-7447C46D6E413D` | BUSINESS_CASES | `PRD-INVENTORY-002` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-6F34550ADB2C93` | BUSINESS_CASES | `PRD-INVENTORY-002` | BUSINESS_RULES | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-41F1D13DA24F4A` | BUSINESS_CASES | `PRD-INVENTORY-003` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-C58F3B4AC30BDF` | BUSINESS_CASES | `PRD-INVENTORY-003` | BUSINESS_RULES | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-0F86052855472D` | BUSINESS_CASES | `PRD-INVENTORY-004` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-44EF06F2FBAFC1` | BUSINESS_CASES | `PRD-INVENTORY-005` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-4FADE1456398E9` | BUSINESS_CASES | `PRD-INVENTORY-005` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-55BCD257EF0BF2` | BUSINESS_CASES | `PRD-INVENTORY-006` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-444C45153CB261` | BUSINESS_CASES | `PRD-INVENTORY-006` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-2EE3BFB554AF04` | BUSINESS_CASES | `PRD-INVENTORY-007` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-F438A21491064A` | BUSINESS_CASES | `PRD-INVENTORY-008` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-595B05BB8A4A88` | BUSINESS_CASES | `PRD-INVENTORY-008` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-8EF96209EB0C34` | BUSINESS_CASES | `PRD-INVENTORY-008` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-82CB3FD7A8ADA7` | BUSINESS_CASES | `PRD-INVENTORY-009` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-3BEC321B4FEDDE` | BUSINESS_CASES | `PRD-INVENTORY-009` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-29AD59BADF2238` | BUSINESS_CASES | `PRD-INVENTORY-009` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-433C82C4B1AC52` | BUSINESS_CASES | `PRD-INVENTORY-010` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-D108F6F1847DD1` | BUSINESS_CASES | `PRD-INVENTORY-010` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-75F5560BA89567` | BUSINESS_CASES | `PRD-INVENTORY-011` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-BC60A3C5B33035` | BUSINESS_CASES | `PRD-INVENTORY-011` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-E13866AC8B0126` | BUSINESS_CASES | `PRD-INVENTORY-012` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-B1A0A6F9BF7F71` | BUSINESS_CASES | `PRD-INVENTORY-012` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-5ACCF398FCA6E5` | BUSINESS_CASES | `PRD-INVENTORY-013` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-689E7775D2646B` | BUSINESS_CASES | `PRD-INVENTORY-013` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-B038D04BBB9B1A` | BUSINESS_CASES | `PRD-INVENTORY-014` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-E35E0AFB64A20D` | BUSINESS_CASES | `PRD-INVENTORY-014` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |

#### Sudah diperbaiki dari source fact (8)

| ID | Mode | PRD | Jenis | Bukti literal |
|---|---|---|---|---|
| `AR-F8181E67498960` | BUSINESS_CASES | `PRD-INVENTORY-004` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/inventory (.md)/prd-inventory-pemesanan-barang.md:217 |
| `AR-D50A891EE94C46` | BUSINESS_CASES | `PRD-INVENTORY-006` | CASES_CONDITIONS | PRD/PRD Generator (.md)/inventory (.md)/prd-pemisahan-ri-rj.md:75 |
| `AR-52DDB3566995E2` | BUSINESS_CASES | `PRD-INVENTORY-007` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/inventory (.md)/prd-inventory-informasi-stok (2).md:114 |
| `AR-2FA3ED1330D62B` | BUSINESS_CASES | `PRD-INVENTORY-007` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/inventory (.md)/prd-inventory-informasi-stok (2).md:248 |
| `AR-7568F040F5219C` | BUSINESS_CASES | `PRD-INVENTORY-010` | ACCEPTANCE_CRITERIA | PRD/PRD Generator (.md)/inventory (.md)/prd-inventory-penggunaan-barang-unit.md:140 |
| `AR-08B66E0D3247F4` | BUSINESS_CASES | `PRD-INVENTORY-011` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/inventory (.md)/prd-inventory-retur-pembelian (1).md:115 |
| `AR-5CA54A8BD9BAA0` | BUSINESS_CASES | `PRD-INVENTORY-013` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/inventory (.md)/prd-inventory-peminjaman-dan-pengembalian-barang.… |
| `AR-AA4D447F706355` | BUSINESS_CASES | `PRD-INVENTORY-014` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/inventory (.md)/prd-inventory-stok-opname (1).md:199 |

#### Keputusan terkonfirmasi (0)

Belum ada keputusan manusia yang tercatat.

## Kelompok: pelayanan-lintas-domain

### E2E-EMR | Rekam Medis dan Dokumentasi Klinis

- Tujuan: Dokumentasi klinis yang digunakan lintas unit pelayanan.
- PRD: **5** | relasi: 87 | lintas-domain: 83
- Gap terbuka: **9** | fix source fact: **2** | dikecualikan: **0**
- Sesi: belum ada

| Kode | PRD | Stage |
|---|---|---|
| `PRD-EMR-001` | PRD — Asesmen Jawaban Konsulan | ASSESSMENT |
| `PRD-EMR-002` | PRD — Input Tindakan & BHP | EXECUTION |
| `PRD-EMR-003` | PRD — Input Tindakan & BHP | EXECUTION |
| `PRD-EMR-004` | PRD Pondasi — Resume Medis (N9) | OUTPUT |
| `PRD-EMR-005` | emr data alergi pasien | SUPPORTING |

#### Gap terbuka (9)

| ID | Mode | PRD | Jenis | Status | Bukti |
|---|---|---|---|---|---|
| `AR-CA1A3EA571C773` | BUSINESS_CASES | `PRD-EMR-001` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-8B00402EF952A1` | BUSINESS_CASES | `PRD-EMR-001` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-3246321E0A8A28` | BUSINESS_CASES | `PRD-EMR-002` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-99EF31B44440CA` | BUSINESS_CASES | `PRD-EMR-003` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-D7B5B0878C7258` | BUSINESS_CASES | `PRD-EMR-004` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-264BE95EB969CD` | BUSINESS_CASES | `PRD-EMR-004` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-CB382EDD612721` | BUSINESS_CASES | `PRD-EMR-004` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/N9__resume-medis.md:365 |
| `AR-DC35E4AB820FBC` | BUSINESS_CASES | `PRD-EMR-005` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-707A8ACB9DEA95` | BUSINESS_CASES | `PRD-EMR-005` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |

#### Sudah diperbaiki dari source fact (2)

| ID | Mode | PRD | Jenis | Bukti literal |
|---|---|---|---|---|
| `AR-F42207DCF6F586` | BUSINESS_CASES | `PRD-EMR-002` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Tindakan-BHP.md:339 |
| `AR-28D92D8C715A60` | BUSINESS_CASES | `PRD-EMR-003` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/Update/PRD-Tindakan-BHP-UPDATE.md:381 |

#### Keputusan terkonfirmasi (0)

Belum ada keputusan manusia yang tercatat.

## Kelompok: pelayanan-penunjang

### E2E-LAB | Laboratorium

- Tujuan: Order, konfirmasi, pelaksanaan, dan hasil laboratorium.
- PRD: **4** | relasi: 23 | lintas-domain: 18
- Gap terbuka: **7** | fix source fact: **4** | dikecualikan: **0**
- Sesi: belum ada

| Kode | PRD | Stage |
|---|---|---|
| `PRD-LAB-001` | PRD — Konfirmasi Order Laboratorium | REQUEST |
| `PRD-LAB-002` | PRD — Order Pemeriksaan Laboratorium | REQUEST |
| `PRD-LAB-003` | PRD Pondasi — Dashboard Laboratorium (N10) | WORKLIST |
| `PRD-LAB-004` | Product Requirement Document (PRD) — N15 Input Hasil Laboratorium | OUTPUT |

#### Gap terbuka (7)

| ID | Mode | PRD | Jenis | Status | Bukti |
|---|---|---|---|---|---|
| `AR-56FA345B9A8A1D` | BUSINESS_CASES | `PRD-LAB-001` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-12C8EFD694721C` | BUSINESS_CASES | `PRD-LAB-001` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Konfirmasi-Order-Laboratorium.md:22 |
| `AR-2DD324030AD01E` | BUSINESS_CASES | `PRD-LAB-002` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Order-Pemeriksaan-Laboratorium.md:181 |
| `AR-4B6F0802D48B12` | BUSINESS_CASES | `PRD-LAB-002` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Order-Pemeriksaan-Laboratorium.md:185 |
| `AR-9910D1528731B1` | BUSINESS_CASES | `PRD-LAB-003` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-81036654C768D2` | BUSINESS_CASES | `PRD-LAB-003` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-07F9CC3E930D20` | BUSINESS_CASES | `PRD-LAB-004` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |

#### Sudah diperbaiki dari source fact (4)

| ID | Mode | PRD | Jenis | Bukti literal |
|---|---|---|---|---|
| `AR-B1473DF8F8AC22` | BUSINESS_CASES | `PRD-LAB-001` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Konfirmasi-Order-Laboratorium.md:222 |
| `AR-959634EA7AE99E` | BUSINESS_CASES | `PRD-LAB-002` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Order-Pemeriksaan-Laboratorium.md:58 |
| `AR-AC9B6DC8008877` | BUSINESS_CASES | `PRD-LAB-002` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Order-Pemeriksaan-Laboratorium.md:541 |
| `AR-6344278DF1287C` | BUSINESS_CASES | `PRD-LAB-003` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Pelayanan (.md)/N10__dashboard-laboratorium.md:129 |

#### Keputusan terkonfirmasi (0)

Belum ada keputusan manusia yang tercatat.

### E2E-RAD | Radiologi

- Tujuan: Pendaftaran, order, konfirmasi, dan hasil radiologi.
- PRD: **5** | relasi: 21 | lintas-domain: 16
- Gap terbuka: **14** | fix source fact: **5** | dikecualikan: **10**
- Sesi: belum ada

| Kode | PRD | Stage |
|---|---|---|
| `PRD-RAD-001` | PRD — Pendaftaran Radiologi | ENTRY |
| `PRD-RAD-002` | PRD — Konfirmasi Order Radiologi | REQUEST |
| `PRD-RAD-003` | PRD — Order Permintaan Radiologi | REQUEST |
| `PRD-RAD-004` | PRD — Dashboard Radiologi (N12) | WORKLIST |
| `PRD-RAD-005` | PRD — Input Hasil Pemeriksaan Radiologi | OUTPUT |

#### Gap terbuka (14)

| ID | Mode | PRD | Jenis | Status | Bukti |
|---|---|---|---|---|---|
| `AR-CE66DE123FA2FC` | BUSINESS_CASES | `PRD-RAD-001` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-F1C6093410A196` | BUSINESS_CASES | `PRD-RAD-001` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-58E0B1A6AF8FE1` | BUSINESS_CASES | `PRD-RAD-001` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-1A304632DBB5D3` | BUSINESS_CASES | `PRD-RAD-003` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Order-Permintaan-Radiologi.md:185 |
| `AR-E1836968C78C6C` | BUSINESS_CASES | `PRD-RAD-004` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-F66271921FC546` | BUSINESS_CASES | `PRD-RAD-004` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-6AA7B2062B6677` | BUSINESS_CASES | `PRD-RAD-005` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-752726CE64C620` | BUSINESS_CASES | `PRD-RAD-005` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-01F8A18357EFDB` | BUSINESS_CASES | `PRD-RAD-005` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Input-Hasil-Pemeriksaan-Radiologi.md:200 |
| `AR-5E4A49C8CCCF90` | BUSINESS_CASES | `PRD-RAD-005` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Input-Hasil-Pemeriksaan-Radiologi.md:221 |
| `AR-BBB53459F0E481` | BUSINESS_CASES | `PRD-RAD-005` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Input-Hasil-Pemeriksaan-Radiologi.md:258 |
| `AR-3F7169293B6AAA` | BUSINESS_CASES | `PRD-RAD-005` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Input-Hasil-Pemeriksaan-Radiologi.md:261 |
| `AR-0F4BC7318DED12` | BUSINESS_CASES | `PRD-RAD-005` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Input-Hasil-Pemeriksaan-Radiologi.md:385 |
| `AR-5FA3C94BE2099A` | BUSINESS_CASES | `PRD-RAD-005` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Input-Hasil-Pemeriksaan-Radiologi.md:40 |

#### Sudah diperbaiki dari source fact (5)

| ID | Mode | PRD | Jenis | Bukti literal |
|---|---|---|---|---|
| `AR-07E3223E2F480F` | BUSINESS_CASES | `PRD-RAD-002` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Konfirmasi-Order-Radiologi.md:271 |
| `AR-103E7EDD5E4DB7` | BUSINESS_CASES | `PRD-RAD-002` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Konfirmasi-Order-Radiologi.md:271 |
| `AR-F375BD6529ED5C` | BUSINESS_CASES | `PRD-RAD-003` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Order-Permintaan-Radiologi.md:175 |
| `AR-42F128A2D7F0E8` | BUSINESS_CASES | `PRD-RAD-003` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Order-Permintaan-Radiologi.md:221 |
| `AR-3D919449C7B0ED` | BUSINESS_CASES | `PRD-RAD-004` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Pelayanan (.md)/N12__dashboard-radiologi.md:78 |

#### Keputusan terkonfirmasi (0)

Belum ada keputusan manusia yang tercatat.

### E2E-PA | Patologi Anatomi

- Tujuan: Order, konfirmasi, dan hasil patologi anatomi.
- PRD: **5** | relasi: 19 | lintas-domain: 16
- Gap terbuka: **5** | fix source fact: **7** | dikecualikan: **3**
- Sesi: belum ada

| Kode | PRD | Stage |
|---|---|---|
| `PRD-PA-001` | PRD — Pendaftaran Penunjang (Laboratorium & Patologi Anatomi) | ENTRY |
| `PRD-PA-002` | PRD — Konfirmasi Order Patologi Anatomi | REQUEST |
| `PRD-PA-003` | PRD — Order Pemeriksaan Patologi Anatomi | REQUEST |
| `PRD-PA-004` | Product Requirement Document (PRD) — Dashboard Patologi Anatomi (F49) | WORKLIST |
| `PRD-PA-005` | Product Requirement Document (PRD) - Input Hasil Patologi Anatomi (F50) | OUTPUT |

#### Gap terbuka (5)

| ID | Mode | PRD | Jenis | Status | Bukti |
|---|---|---|---|---|---|
| `AR-84BD3B66892995` | BUSINESS_CASES | `PRD-PA-001` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-0AFE61CD6AB5CB` | BUSINESS_CASES | `PRD-PA-001` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-55358FB008E315` | BUSINESS_CASES | `PRD-PA-002` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Konfirmasi-Order-Patologi-Anatomi-Neurovi-v2.… |
| `AR-B1EB7C32D1D29D` | BUSINESS_CASES | `PRD-PA-004` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-dashboard-patologi-anatomi.md:262 |
| `AR-1F31879A32F84C` | BUSINESS_CASES | `PRD-PA-005` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |

#### Sudah diperbaiki dari source fact (7)

| ID | Mode | PRD | Jenis | Bukti literal |
|---|---|---|---|---|
| `AR-2566B803843DBB` | BUSINESS_CASES | `PRD-PA-002` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Konfirmasi-Order-Patologi-Anatomi-Neurovi-v2.… |
| `AR-7B8638A6751E11` | BUSINESS_CASES | `PRD-PA-003` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Order-Pemeriksaan-Patologi-Anatomi-Neurovi-v2… |
| `AR-3A80C5718FA0AF` | BUSINESS_CASES | `PRD-PA-004` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-dashboard-patologi-anatomi.md:51 |
| `AR-FC09C26C2448F9` | BUSINESS_CASES | `PRD-PA-004` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-dashboard-patologi-anatomi.md:281 |
| `AR-6BE2FBB629622C` | BUSINESS_CASES | `PRD-PA-004` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-dashboard-patologi-anatomi.md:235 |
| `AR-19F3CF2AEC011C` | BUSINESS_CASES | `PRD-PA-005` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-input-hasil-patologi-anatomi.md:79 |
| `AR-46F16B227FB5C9` | BUSINESS_CASES | `PRD-PA-005` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-input-hasil-patologi-anatomi.md:79 |

#### Keputusan terkonfirmasi (0)

Belum ada keputusan manusia yang tercatat.

### E2E-REHAB | Rehabilitasi Medik

- Tujuan: Penjadwalan, asesmen, dan pelayanan rehabilitasi medik.
- PRD: **5** | relasi: 18 | lintas-domain: 17
- Gap terbuka: **14** | fix source fact: **0** | dikecualikan: **1**
- Sesi: belum ada

| Kode | PRD | Stage |
|---|---|---|
| `PRD-REHAB-001` | Product Requirement Document (PRD) - Penjadwalan Terapi Rehabilitasi Medis (F25) | SCHEDULING |
| `PRD-REHAB-002` | PRD — Dashboard Pelayanan Rehabilitasi Medik (Rehab Medik) | WORKLIST |
| `PRD-REHAB-003` | PRD — Dashboard Pelayanan Terapi | WORKLIST |
| `PRD-REHAB-004` | PRD — Asesmen Penunjang Medis Rehabilitasi Medik (Base/General) | ASSESSMENT |
| `PRD-REHAB-005` | PRD — Asesmen Rehabilitasi Medik (Optimalisasi Layout UI) | ASSESSMENT |

#### Gap terbuka (14)

| ID | Mode | PRD | Jenis | Status | Bukti |
|---|---|---|---|---|---|
| `AR-4720B150E53D63` | BUSINESS_CASES | `PRD-REHAB-001` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-509EC7EDD526A0` | BUSINESS_CASES | `PRD-REHAB-001` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-2398307DE0D13C` | BUSINESS_CASES | `PRD-REHAB-002` | ALTERNATE_CASE_CONTEXT | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-7C68A874F6FD42` | BUSINESS_CASES | `PRD-REHAB-002` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-4559324B432F87` | BUSINESS_CASES | `PRD-REHAB-002` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-10557F8B2F9DF3` | BUSINESS_CASES | `PRD-REHAB-002` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Dashboard-Rehab Medik.md:208 |
| `AR-C4F8335250AE33` | BUSINESS_CASES | `PRD-REHAB-003` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-F0BA422802141B` | BUSINESS_CASES | `PRD-REHAB-003` | ALTERNATE_CASE_CONTEXT | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-DA2D2DFE82B245` | BUSINESS_CASES | `PRD-REHAB-003` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-93EE1A8D06124A` | BUSINESS_CASES | `PRD-REHAB-003` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-11176F4367F5FE` | BUSINESS_CASES | `PRD-REHAB-004` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-CDB33FA75CB8AE` | BUSINESS_CASES | `PRD-REHAB-004` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-F3866D5567E495` | BUSINESS_CASES | `PRD-REHAB-005` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-F11288F6283819` | BUSINESS_CASES | `PRD-REHAB-005` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |

#### Sudah diperbaiki dari source fact (0)

Belum ada fix pada cakupan register ini.

#### Keputusan terkonfirmasi (0)

Belum ada keputusan manusia yang tercatat.

### E2E-HD | Hemodialisa

- Tujuan: Order, penjadwalan, asesmen, dan monitoring hemodialisa.
- PRD: **5** | relasi: 29 | lintas-domain: 21
- Gap terbuka: **10** | fix source fact: **4** | dikecualikan: **10**
- Sesi: belum ada

| Kode | PRD | Stage |
|---|---|---|
| `PRD-HD-001` | PRD — Order Hemodialisa | REQUEST |
| `PRD-HD-002` | Product Requirement Document (PRD) - Penjadwalan Hemodialisa (F26) | SCHEDULING |
| `PRD-HD-003` | Dashboard Hemodialisa (HD) | WORKLIST |
| `PRD-HD-004` | PRD — Asesmen Hemodialisa | ASSESSMENT |
| `PRD-HD-005` | PRD — Monitoring Hemodialisa | EXECUTION |

#### Gap terbuka (10)

| ID | Mode | PRD | Jenis | Status | Bukti |
|---|---|---|---|---|---|
| `AR-E970267EEEFDC8` | BUSINESS_CASES | `PRD-HD-001` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Order-Hemodialisa.md:119 |
| `AR-9003299A270BF6` | BUSINESS_CASES | `PRD-HD-001` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Order-Hemodialisa.md:150 |
| `AR-1D1CBFDB4D0CA3` | BUSINESS_CASES | `PRD-HD-001` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Order-Hemodialisa.md:151 |
| `AR-1B87A55B467BA1` | BUSINESS_CASES | `PRD-HD-001` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Order-Hemodialisa.md:152 |
| `AR-8C55E612FF6BD0` | BUSINESS_CASES | `PRD-HD-001` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Order-Hemodialisa.md:34 |
| `AR-EBFBAC762CFE8A` | BUSINESS_CASES | `PRD-HD-002` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-C7A87B577753B7` | BUSINESS_CASES | `PRD-HD-003` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-4B9865DE4A48E0` | BUSINESS_CASES | `PRD-HD-003` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-9349CFF038C97C` | BUSINESS_CASES | `PRD-HD-004` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-D3055839D62FB4` | BUSINESS_CASES | `PRD-HD-004` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |

#### Sudah diperbaiki dari source fact (4)

| ID | Mode | PRD | Jenis | Bukti literal |
|---|---|---|---|---|
| `AR-2E3B0421DA6E54` | BUSINESS_CASES | `PRD-HD-001` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Order-Hemodialisa.md:132 |
| `AR-C30ED0FA9661AE` | BUSINESS_CASES | `PRD-HD-003` | OUT_OF_SCOPE | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Dashboard-Hemodialisa (HD).md:83 |
| `AR-20196A3F4C357F` | BUSINESS_CASES | `PRD-HD-005` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Monitoring-HD.md:151 |
| `AR-D10DE0A32D7EFE` | BUSINESS_CASES | `PRD-HD-005` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Monitoring-HD.md:49 |

#### Keputusan terkonfirmasi (0)

Belum ada keputusan manusia yang tercatat.

### E2E-IBS | IBS dan Operasi

- Tujuan: Permintaan, penjadwalan, pelaksanaan, dan laporan operasi.
- PRD: **9** | relasi: 40 | lintas-domain: 26
- Gap terbuka: **16** | fix source fact: **13** | dikecualikan: **17**
- Sesi: belum ada

| Kode | PRD | Stage |
|---|---|---|
| `PRD-IBS-001` | PRD — Konfirmasi Order Jadwal Operasi | REQUEST |
| `PRD-IBS-002` | PRD — Permintaan Jadwal Operasi | REQUEST |
| `PRD-IBS-003` | PRD — Display Jadwal Operasi (N14) | SCHEDULING |
| `PRD-IBS-004` | PRD — Dashboard Pelayanan Operasi (Instalasi Bedah Sentral / IBS) | WORKLIST |
| `PRD-IBS-005` | PRD — Asesmen Awal Medis Bedah Non Trauma (N20) | ASSESSMENT |
| `PRD-IBS-006` | PRD — Asesmen Awal Medis Bedah Trauma (N21) | ASSESSMENT |
| `PRD-IBS-007` | PRD - Laporan Anestesi Neurovi v2 (Enhancement PKU) | EXECUTION |
| `PRD-IBS-008` | PRD Pondasi — Penundaan Operasi Pasien (N13) | EXECUTION |
| `PRD-IBS-009` | PRD — Laporan Operasi (N27) | OUTPUT |

#### Gap terbuka (16)

| ID | Mode | PRD | Jenis | Status | Bukti |
|---|---|---|---|---|---|
| `AR-35DCFC52B302CD` | BUSINESS_CASES | `PRD-IBS-001` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Konfirmasi-Order-Jadwal-Operasi.md:170 |
| `AR-348AAFACA28F5B` | BUSINESS_CASES | `PRD-IBS-001` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Konfirmasi-Order-Jadwal-Operasi.md:29 |
| `AR-9CF10E86130986` | BUSINESS_CASES | `PRD-IBS-002` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Permintaan-Jadwal-Operasi.md:128 |
| `AR-949B55A102B898` | BUSINESS_CASES | `PRD-IBS-003` | CASES_CONDITIONS | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-BCE3BC2533FB69` | BUSINESS_CASES | `PRD-IBS-003` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/N14__display-jadwal-operasi.md:322 |
| `AR-439E83740ABADB` | BUSINESS_CASES | `PRD-IBS-004` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-1C44E71B4A890F` | BUSINESS_CASES | `PRD-IBS-005` | ALTERNATE_CASE_CONTEXT | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-2F1E146854F945` | BUSINESS_CASES | `PRD-IBS-005` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-30845E523EF43D` | BUSINESS_CASES | `PRD-IBS-005` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-675698A2C341F3` | BUSINESS_CASES | `PRD-IBS-006` | ALTERNATE_CASE_CONTEXT | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-C724E839575CA3` | BUSINESS_CASES | `PRD-IBS-006` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-08A7257DBEB7FB` | BUSINESS_CASES | `PRD-IBS-008` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-CED89B409FA339` | BUSINESS_CASES | `PRD-IBS-008` | CASES_CONDITIONS | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-70B7DFB243E6C6` | BUSINESS_CASES | `PRD-IBS-008` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/N13__penundaan-operasi-pasien.md:332 |
| `AR-0E2FD4C7D01645` | BUSINESS_CASES | `PRD-IBS-009` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-673211D0F69890` | BUSINESS_CASES | `PRD-IBS-009` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |

#### Sudah diperbaiki dari source fact (13)

| ID | Mode | PRD | Jenis | Bukti literal |
|---|---|---|---|---|
| `AR-98AB455C6A2B05` | BUSINESS_CASES | `PRD-IBS-001` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Konfirmasi-Order-Jadwal-Operasi.md:192 |
| `AR-B7FEC85C70FD52` | BUSINESS_CASES | `PRD-IBS-001` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Konfirmasi-Order-Jadwal-Operasi.md:192 |
| `AR-83FCB5047CFDE4` | BUSINESS_CASES | `PRD-IBS-002` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Permintaan-Jadwal-Operasi.md:13 |
| `AR-650AE1E5842613` | BUSINESS_CASES | `PRD-IBS-002` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Permintaan-Jadwal-Operasi.md:144 |
| `AR-97DF192EC16E83` | BUSINESS_CASES | `PRD-IBS-003` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/N14__display-jadwal-operasi.md:330 |
| `AR-79851263BFC6A9` | BUSINESS_CASES | `PRD-IBS-003` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/N14__display-jadwal-operasi.md:304 |
| `AR-C2717296BF1CB8` | BUSINESS_CASES | `PRD-IBS-004` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Dashboard-IBS.md:114 |
| `AR-BEFB3696B7369B` | BUSINESS_CASES | `PRD-IBS-006` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Pelayanan (.md)/N21__asesmen-awal-medis-bedah-trauma.md:136 |
| `AR-F9107F748481DA` | BUSINESS_CASES | `PRD-IBS-006` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/N21__asesmen-awal-medis-bedah-trauma.md:190 |
| `AR-4B45FF3EF8E31E` | BUSINESS_CASES | `PRD-IBS-007` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Laporan-Anestesi-Neurovi-v2-v2.2.md:158 |
| `AR-6FD728F45FB6E3` | BUSINESS_CASES | `PRD-IBS-007` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Laporan-Anestesi-Neurovi-v2-v2.2.md:404 |
| `AR-CE4B919C850A3D` | BUSINESS_CASES | `PRD-IBS-008` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/N13__penundaan-operasi-pasien.md:209 |
| `AR-E5E19E7075023A` | BUSINESS_CASES | `PRD-IBS-009` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Pelayanan (.md)/N27__laporan-operasi.md:78 |

#### Keputusan terkonfirmasi (0)

Belum ada keputusan manusia yang tercatat.

### E2E-GIZI | Gizi

- Tujuan: Order makanan, pemakaian barang, dan pelayanan gizi.
- PRD: **4** | relasi: 6 | lintas-domain: 6
- Gap terbuka: **4** | fix source fact: **6** | dikecualikan: **1**
- Sesi: belum ada

| Kode | PRD | Stage |
|---|---|---|
| `PRD-GIZI-001` | PRD — Dashboard Gizi: Order Makanan Pasien | REQUEST |
| `PRD-GIZI-002` | PRD — Dashboard Rekap Order Gizi | REQUEST |
| `PRD-GIZI-003` | PRD — Skrining Gizi Lanjutan / Subjective Global Assessment (N25) | ASSESSMENT |
| `PRD-GIZI-004` | Product Requirement Document (PRD) - Penggunaan Barang Gizi (F9) | EXECUTION |

#### Gap terbuka (4)

| ID | Mode | PRD | Jenis | Status | Bukti |
|---|---|---|---|---|---|
| `AR-707FACBA41547B` | BUSINESS_CASES | `PRD-GIZI-002` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Dashboard-Rekap-Order-Gizi-Neurovi-v2.md:181 |
| `AR-4052F328E9CE4B` | BUSINESS_CASES | `PRD-GIZI-002` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Dashboard-Rekap-Order-Gizi-Neurovi-v2.md:26 |
| `AR-DBED5720AB6557` | BUSINESS_CASES | `PRD-GIZI-003` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-0C27EE30A04FD8` | BUSINESS_CASES | `PRD-GIZI-003` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |

#### Sudah diperbaiki dari source fact (6)

| ID | Mode | PRD | Jenis | Bukti literal |
|---|---|---|---|---|
| `AR-FF0978DC21154A` | BUSINESS_CASES | `PRD-GIZI-001` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Dashboard-Gizi-Order-Makanan-Pasien-Neurovi-v… |
| `AR-775C66218FDC70` | BUSINESS_CASES | `PRD-GIZI-002` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Dashboard-Rekap-Order-Gizi-Neurovi-v2.md:168 |
| `AR-6328485306F1AB` | BUSINESS_CASES | `PRD-GIZI-002` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Dashboard-Rekap-Order-Gizi-Neurovi-v2.md:199 |
| `AR-6ED0EA5BAAEA93` | BUSINESS_CASES | `PRD-GIZI-003` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Pelayanan (.md)/N25__skrining-gizi-lanjutan.md:260 |
| `AR-81BCAA8780F83A` | BUSINESS_CASES | `PRD-GIZI-004` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-penggunaan-barang-gizi.md:72 |
| `AR-94982CE26FA8BA` | BUSINESS_CASES | `PRD-GIZI-004` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-penggunaan-barang-gizi.md:528 |

#### Keputusan terkonfirmasi (0)

Belum ada keputusan manusia yang tercatat.

### E2E-FARMASI | Farmasi

- Tujuan: Pelayanan obat, retur, rekonsiliasi, dan pengaturan farmasi.
- PRD: **9** | relasi: 27 | lintas-domain: 25
- Gap terbuka: **17** | fix source fact: **10** | dikecualikan: **6**
- Sesi: belum ada

| Kode | PRD | Stage |
|---|---|---|
| `PRD-FARMASI-001` | PRD — Pengaturan Farmasi (A42) | FOUNDATION |
| `PRD-FARMASI-002` | PRD — Pengaturan Harga (A59) | FOUNDATION |
| `PRD-FARMASI-003` | PRD — Order Retur Obat dan Alat Kesehatan | REQUEST |
| `PRD-FARMASI-004` | F12 Farmasi manajemen rekonsiliasi obat | VALIDATION |
| `PRD-FARMASI-005` | IBS Catatan pemakaian obat | EXECUTION |
| `PRD-FARMASI-006` | PRD — Apotek Online BPJS (APOL) | EXECUTION |
| `PRD-FARMASI-007` | PRD — Integrasi BPJS Apotek Online (APOL) | EXECUTION |
| `PRD-FARMASI-008` | PRD — Iter Obat | EXECUTION |
| `PRD-FARMASI-009` | PRD — Penjualan Obat Bebas (Non-Kunjungan) — Modul Farmasi — v1.0 | EXECUTION |

#### Gap terbuka (17)

| ID | Mode | PRD | Jenis | Status | Bukti |
|---|---|---|---|---|---|
| `AR-D034578A15F510` | BUSINESS_CASES | `PRD-FARMASI-002` | ALTERNATE_CASE_CONTEXT | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-194F1D35F313BE` | BUSINESS_CASES | `PRD-FARMASI-002` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-87EC6886CFF2CB` | BUSINESS_CASES | `PRD-FARMASI-004` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-2C192ED6FE64C6` | BUSINESS_CASES | `PRD-FARMASI-004` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Farmasi/F12-Farmasi-manajemen-rekonsiliasi-obat.md:17 |
| `AR-7049DBCE95DE77` | BUSINESS_CASES | `PRD-FARMASI-004` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Farmasi/F12-Farmasi-manajemen-rekonsiliasi-obat.md:18 |
| `AR-F3E8EA87B37D68` | BUSINESS_CASES | `PRD-FARMASI-004` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Farmasi/F12-Farmasi-manajemen-rekonsiliasi-obat.md:182 |
| `AR-CE13582B7F1DDA` | BUSINESS_CASES | `PRD-FARMASI-004` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Farmasi/F12-Farmasi-manajemen-rekonsiliasi-obat.md:19 |
| `AR-34E93832B7683C` | BUSINESS_CASES | `PRD-FARMASI-004` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Farmasi/F12-Farmasi-manajemen-rekonsiliasi-obat.md:20 |
| `AR-9FD15F7756918A` | BUSINESS_CASES | `PRD-FARMASI-004` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Farmasi/F12-Farmasi-manajemen-rekonsiliasi-obat.md:21 |
| `AR-9D132C90B898DE` | BUSINESS_CASES | `PRD-FARMASI-004` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Farmasi/F12-Farmasi-manajemen-rekonsiliasi-obat.md:22 |
| `AR-B5A13433D89D5C` | BUSINESS_CASES | `PRD-FARMASI-004` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Farmasi/F12-Farmasi-manajemen-rekonsiliasi-obat.md:302 |
| `AR-14F5B09AACC717` | BUSINESS_CASES | `PRD-FARMASI-005` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-8E830E1DC9DE0F` | BUSINESS_CASES | `PRD-FARMASI-006` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Apotek-Online-BPJS.md:684 |
| `AR-3688D5E2AD65E0` | BUSINESS_CASES | `PRD-FARMASI-008` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-17C0B258F12021` | BUSINESS_CASES | `PRD-FARMASI-008` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Farmasi-Iter-Obat.md:219 |
| `AR-EDDDB9BB98CE8A` | BUSINESS_CASES | `PRD-FARMASI-008` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Farmasi-Iter-Obat.md:221 |
| `AR-F40518613A4CE5` | BUSINESS_CASES | `PRD-FARMASI-009` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |

#### Sudah diperbaiki dari source fact (10)

| ID | Mode | PRD | Jenis | Bukti literal |
|---|---|---|---|---|
| `AR-3AA6D552DD00D0` | BUSINESS_CASES | `PRD-FARMASI-001` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pengaturan (.md)/prd-pengaturan-farmasi.md:157 |
| `AR-1360FB815C8248` | BUSINESS_CASES | `PRD-FARMASI-001` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pengaturan (.md)/prd-pengaturan-farmasi.md:157 |
| `AR-5F7FC05C1551C2` | BUSINESS_CASES | `PRD-FARMASI-002` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pengaturan (.md)/prd-pengaturan-harga-obat.md:226 |
| `AR-177BC8CBBCF404` | BUSINESS_CASES | `PRD-FARMASI-003` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Order-Retur-Obat.md:157 |
| `AR-6187F4E370B322` | BUSINESS_CASES | `PRD-FARMASI-003` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Order-Retur-Obat.md:157 |
| `AR-AFC0F629F60D49` | BUSINESS_CASES | `PRD-FARMASI-004` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Farmasi/F12-Farmasi-manajemen-rekonsiliasi-obat.md:299 |
| `AR-D17910D51C3971` | BUSINESS_CASES | `PRD-FARMASI-006` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Apotek-Online-BPJS.md:90 |
| `AR-27658D3CFE0068` | BUSINESS_CASES | `PRD-FARMASI-007` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Integrasi-BPJS-Apotek-Online.md:299 |
| `AR-EF12E2C3E7E733` | BUSINESS_CASES | `PRD-FARMASI-008` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Farmasi-Iter-Obat.md:106 |
| `AR-6664CB82CA454B` | BUSINESS_CASES | `PRD-FARMASI-009` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Penjualan-Obat-Bebas-v1.0.md:195 |

#### Keputusan terkonfirmasi (0)

Belum ada keputusan manusia yang tercatat.

### E2E-TRANSFUSI | Transfusi Darah

- Tujuan: Order, konfirmasi, crossmatch, dan pelayanan transfusi darah.
- PRD: **4** | relasi: 13 | lintas-domain: 12
- Gap terbuka: **6** | fix source fact: **6** | dikecualikan: **3**
- Sesi: belum ada

| Kode | PRD | Stage |
|---|---|---|
| `PRD-TRANSFUSI-001` | PRD — Konfirmasi Order Transfusi Darah | REQUEST |
| `PRD-TRANSFUSI-002` | PRD — Order Permintaan Transfusi Darah | REQUEST |
| `PRD-TRANSFUSI-003` | Product Requirement Document (PRD) - Dashboard Transfusi Darah (F31) | WORKLIST |
| `PRD-TRANSFUSI-004` | Product Requirement Document (PRD) - Input Hasil Crossmatch Darah (F32) | OUTPUT |

#### Gap terbuka (6)

| ID | Mode | PRD | Jenis | Status | Bukti |
|---|---|---|---|---|---|
| `AR-6EC91AC4732F09` | BUSINESS_CASES | `PRD-TRANSFUSI-001` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Konfirmasi-Order-Transfusi-Darah-Neurovi-v2.m… |
| `AR-B51BFF7FC71D64` | BUSINESS_CASES | `PRD-TRANSFUSI-001` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Konfirmasi-Order-Transfusi-Darah-Neurovi-v2.m… |
| `AR-370509AC52CBB4` | BUSINESS_CASES | `PRD-TRANSFUSI-001` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Konfirmasi-Order-Transfusi-Darah-Neurovi-v2.m… |
| `AR-465CE0BBE9E3FC` | BUSINESS_CASES | `PRD-TRANSFUSI-002` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Order-Permintaan-Transfusi-Darah-Neurovi-v2.m… |
| `AR-D43AB5C5188F89` | BUSINESS_CASES | `PRD-TRANSFUSI-003` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-6E536EBE969EE8` | BUSINESS_CASES | `PRD-TRANSFUSI-004` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |

#### Sudah diperbaiki dari source fact (6)

| ID | Mode | PRD | Jenis | Bukti literal |
|---|---|---|---|---|
| `AR-D94B8DB4DF97BE` | BUSINESS_CASES | `PRD-TRANSFUSI-001` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Konfirmasi-Order-Transfusi-Darah-Neurovi-v2.m… |
| `AR-5C18365F2E93CC` | BUSINESS_CASES | `PRD-TRANSFUSI-002` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Order-Permintaan-Transfusi-Darah-Neurovi-v2.m… |
| `AR-F12A680966314C` | BUSINESS_CASES | `PRD-TRANSFUSI-002` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Order-Permintaan-Transfusi-Darah-Neurovi-v2.m… |
| `AR-259F8A1D1401B2` | BUSINESS_CASES | `PRD-TRANSFUSI-003` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-dashboard-transfusi-darah.md:204 |
| `AR-FE3C889C8D0134` | BUSINESS_CASES | `PRD-TRANSFUSI-004` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-input-hasil-crossmatch-transfusi-darah.md:66 |
| `AR-A7917C7B4731F5` | BUSINESS_CASES | `PRD-TRANSFUSI-004` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-input-hasil-crossmatch-transfusi-darah.md:260 |

#### Keputusan terkonfirmasi (0)

Belum ada keputusan manusia yang tercatat.

### E2E-AMBULANCE | Ambulance

- Tujuan: Order dan konfirmasi layanan ambulance.
- PRD: **2** | relasi: 11 | lintas-domain: 9
- Gap terbuka: **4** | fix source fact: **1** | dikecualikan: **0**
- Sesi: belum ada

| Kode | PRD | Stage |
|---|---|---|
| `PRD-AMBULANCE-001` | PRD — Order Ambulance (N7) | REQUEST |
| `PRD-AMBULANCE-002` | PRD — Konfirmasi Ambulance (N6) | VALIDATION |

#### Gap terbuka (4)

| ID | Mode | PRD | Jenis | Status | Bukti |
|---|---|---|---|---|---|
| `AR-B63CF61919B43A` | BUSINESS_CASES | `PRD-AMBULANCE-001` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-D07DDFEB26F201` | BUSINESS_CASES | `PRD-AMBULANCE-001` | CASES_CONDITIONS | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-5FD1C857F5BB83` | BUSINESS_CASES | `PRD-AMBULANCE-001` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-0EAFE25826CB25` | BUSINESS_CASES | `PRD-AMBULANCE-002` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |

#### Sudah diperbaiki dari source fact (1)

| ID | Mode | PRD | Jenis | Bukti literal |
|---|---|---|---|---|
| `AR-DF4EA448E5DE67` | BUSINESS_CASES | `PRD-AMBULANCE-002` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/N6__menu-ambulance.md:224 |

#### Keputusan terkonfirmasi (0)

Belum ada keputusan manusia yang tercatat.

### E2E-JENAZAH | Pemulasaraan Jenazah

- Tujuan: Pelayanan pemulasaraan jenazah.
- PRD: **1** | relasi: 9 | lintas-domain: 9
- Gap terbuka: **3** | fix source fact: **0** | dikecualikan: **0**
- Sesi: belum ada

| Kode | PRD | Stage |
|---|---|---|
| `PRD-JENAZAH-001` | PRD Pondasi — Pemulasaraan Jenazah (N8) | EXECUTION |

#### Gap terbuka (3)

| ID | Mode | PRD | Jenis | Status | Bukti |
|---|---|---|---|---|---|
| `AR-C5C69A91483E45` | BUSINESS_CASES | `PRD-JENAZAH-001` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-71A694E44633D6` | BUSINESS_CASES | `PRD-JENAZAH-001` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-E0971DA6B7AB63` | BUSINESS_CASES | `PRD-JENAZAH-001` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/N8__pemulasaraan-jenazah.md:325 |

#### Sudah diperbaiki dari source fact (0)

Belum ada fix pada cakupan register ini.

#### Keputusan terkonfirmasi (0)

Belum ada keputusan manusia yang tercatat.

## Kelompok: pelayanan-utama

### E2E-RJ | Rawat Jalan

- Tujuan: Alur kunjungan dan pelayanan rawat jalan.
- PRD: **12** | relasi: 74 | lintas-domain: 57
- Gap terbuka: **30** | fix source fact: **7** | dikecualikan: **11**
- Sesi: belum ada

| Kode | PRD | Stage |
|---|---|---|
| `PRD-RJ-001` | PRD — Antrian: APM (Check-In Mandiri) | ENTRY |
| `PRD-RJ-002` | PRD — Display Antrean (Antrean Pendaftaran / Loket Admisi) | ENTRY |
| `PRD-RJ-003` | PRD — General Consent Rawat Jalan | ENTRY |
| `PRD-RJ-004` | PRD — Pendaftaran Rawat Jalan | ENTRY |
| `PRD-RJ-005` | PRD — Pendaftaran Rawat Jalan (MERGED) | ENTRY |
| `PRD-RJ-006` | PRD — Pendaftaran Rawat Jalan (Versi B — berbasis gdoc) | ENTRY |
| `PRD-RJ-007` | PRD — Dashboard Pelayanan Rawat Jalan (Poliklinik) | WORKLIST |
| `PRD-RJ-008` | PRD — Dashboard Pelayanan Rawat Jalan (Poliklinik) | WORKLIST |
| `PRD-RJ-009` | PRD — Display Antrian & Pemanggilan Pasien Poliklinik | WORKLIST |
| `PRD-RJ-010` | PRD — Asesmen Rawat Jalan (Keperawatan & Dokter) | ASSESSMENT |
| `PRD-RJ-011` | PRD — Panel Riwayat Pasien (Riwayat Kunjungan, Riwayat Rujukan & Penunjang) — S… | ASSESSMENT |
| `PRD-RJ-012` | PRD — Data Pasien: Ringkasan Kesehatan Pasien / Ringkasan Pulang Rawat Jalan (D… | EXECUTION |

#### Gap terbuka (30)

| ID | Mode | PRD | Jenis | Status | Bukti |
|---|---|---|---|---|---|
| `AR-E6382C594AAE01` | BUSINESS_CASES | `PRD-RJ-001` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-6BCFCE19FA853F` | BUSINESS_CASES | `PRD-RJ-002` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-ED12805A8BA81B` | BUSINESS_CASES | `PRD-RJ-004` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-9DA1C43D9CC22B` | BUSINESS_CASES | `PRD-RJ-004` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-D5DAE851F4A2E0` | BUSINESS_CASES | `PRD-RJ-004` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-pendaftaran-pendaftaran-rawat-jalan.md:211 |
| `AR-3E51755D8B056C` | BUSINESS_CASES | `PRD-RJ-004` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-pendaftaran-pendaftaran-rawat-jalan.md:366 |
| `AR-0563AF0BD7566E` | BUSINESS_CASES | `PRD-RJ-004` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-pendaftaran-pendaftaran-rawat-jalan.md:43 |
| `AR-219B2A2839A59B` | BUSINESS_CASES | `PRD-RJ-005` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-0534D61977A448` | BUSINESS_CASES | `PRD-RJ-005` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-21AAED97DC2B2C` | BUSINESS_CASES | `PRD-RJ-005` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-pendaftaran-rawat-jalan-merged.md:17 |
| `AR-013DBF17029EF7` | BUSINESS_CASES | `PRD-RJ-005` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-pendaftaran-rawat-jalan-merged.md:271 |
| `AR-0EE1423CC19A02` | BUSINESS_CASES | `PRD-RJ-005` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-pendaftaran-rawat-jalan-merged.md:451 |
| `AR-6D5420722AA298` | BUSINESS_CASES | `PRD-RJ-005` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-pendaftaran-rawat-jalan-merged.md:65 |
| `AR-08A547662A2456` | BUSINESS_CASES | `PRD-RJ-005` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-pendaftaran-rawat-jalan-merged.md:88 |
| `AR-893E4CDA757092` | BUSINESS_CASES | `PRD-RJ-006` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-0175225F871DA6` | BUSINESS_CASES | `PRD-RJ-006` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-9358F661F6D097` | BUSINESS_CASES | `PRD-RJ-006` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-pendaftaran-rawat-jalan-versi-gdoc.md:310 |
| `AR-FFD2E4E85CB8EC` | BUSINESS_CASES | `PRD-RJ-006` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-pendaftaran-rawat-jalan-versi-gdoc.md:5 |
| `AR-D3A815F0844DD0` | BUSINESS_CASES | `PRD-RJ-006` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-pendaftaran-rawat-jalan-versi-gdoc.md:80 |
| `AR-973205D64EF61D` | BUSINESS_CASES | `PRD-RJ-007` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-164B36F43B9810` | BUSINESS_CASES | `PRD-RJ-008` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-2C750CCED964BB` | BUSINESS_CASES | `PRD-RJ-008` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-4E540CF12B6318` | BUSINESS_CASES | `PRD-RJ-009` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-550770ACC7BAB2` | BUSINESS_CASES | `PRD-RJ-009` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-F36A93BED10E50` | BUSINESS_CASES | `PRD-RJ-010` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-8AC26682C266AF` | BUSINESS_CASES | `PRD-RJ-010` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-E5A67B7FB17D30` | BUSINESS_CASES | `PRD-RJ-011` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-9D4939A952F466` | BUSINESS_CASES | `PRD-RJ-011` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-9561EEB95F80DF` | BUSINESS_CASES | `PRD-RJ-011` | VALIDATION_BEHAVIOR | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-03EF4CA024905F` | BUSINESS_CASES | `PRD-RJ-012` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |

#### Sudah diperbaiki dari source fact (7)

| ID | Mode | PRD | Jenis | Bukti literal |
|---|---|---|---|---|
| `AR-FC328E03234458` | BUSINESS_CASES | `PRD-RJ-001` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/[FIX] prd-antrian-apm.md:15 |
| `AR-76BD6AE615368E` | BUSINESS_CASES | `PRD-RJ-003` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-General-Consent-RJ-v2.0.md:129 |
| `AR-21FD7D50C05A32` | BUSINESS_CASES | `PRD-RJ-003` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-General-Consent-RJ-v2.0.md:129 |
| `AR-C6D8B49862C285` | BUSINESS_CASES | `PRD-RJ-004` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-pendaftaran-pendaftaran-rawat-jalan.md:169 |
| `AR-D6CD8BA87EB8EE` | BUSINESS_CASES | `PRD-RJ-005` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-pendaftaran-rawat-jalan-merged.md:220 |
| `AR-E38FAAE4A5638E` | BUSINESS_CASES | `PRD-RJ-007` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD Dashboard Pelayanan + INTEGRASI.md:225 |
| `AR-09AD0F72F4DC3E` | BUSINESS_CASES | `PRD-RJ-012` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-data-pasien-ringkasan-kesehatan-pasien-catata… |

#### Keputusan terkonfirmasi (0)

Belum ada keputusan manusia yang tercatat.

### E2E-RI | Rawat Inap

- Tujuan: Admisi, pelayanan, perpindahan, dan keluarnya pasien rawat inap.
- PRD: **19** | relasi: 62 | lintas-domain: 44
- Gap terbuka: **29** | fix source fact: **26** | dikecualikan: **6**
- Sesi: belum ada

| Kode | PRD | Stage |
|---|---|---|
| `PRD-RI-001` | PRD — Pendaftaran Rawat Inap (TPPRI) Neurovi v2 | ENTRY |
| `PRD-RI-002` | PRD — Surat Perintah Rawat Inap (SPRI) | REQUEST |
| `PRD-RI-003` | PRD — Dashboard Pelayanan Rawat Inap Neurovi v2 | WORKLIST |
| `PRD-RI-004` | PRD — Asesmen Awal Keperawatan Rawat Inap Anak | ASSESSMENT |
| `PRD-RI-005` | PRD — Asesmen Awal Keperawatan Rawat Inap Dewasa | ASSESSMENT |
| `PRD-RI-006` | PRD — Asesmen Awal Keperawatan Rawat Inap Neonatus | ASSESSMENT |
| `PRD-RI-007` | PRD — Asesmen Awal Medis Rawat Inap Anak (N22) | ASSESSMENT |
| `PRD-RI-008` | PRD — Asesmen Awal Medis Rawat Inap Neonatus (N23) | ASSESSMENT |
| `PRD-RI-009` | PRD — Asesmen Awal Medis Rawat Inap Non Bedah (N19) | ASSESSMENT |
| `PRD-RI-010` | PRD — Asesmen Bina Rohani (N24) | ASSESSMENT |
| `PRD-RI-011` | PRD — Early Warning Scoring System (EWS) Anak | ASSESSMENT |
| `PRD-RI-012` | PRD — Early Warning Scoring System (EWS) Dewasa | ASSESSMENT |
| `PRD-RI-013` | PRD — Early Warning Scoring System (EWS) Neonatus | ASSESSMENT |
| `PRD-RI-014` | PRD — Titip Kelas Rawat Inap | EXECUTION |
| `PRD-RI-015` | PRD — Transfer Internal | EXECUTION |
| `PRD-RI-016` | PRD — Ubah DPJP Rawat Inap | EXECUTION |
| `PRD-RI-017` | PRD — Update Ketersediaan Bed | EXECUTION |
| `PRD-RI-018` | Product Requirement Document (PRD) - Ganti Bed (E15) | EXECUTION |
| `PRD-RI-019` | Product Requirement Document (PRD) — E13 Discharge Pasien | OUTPUT |

#### Gap terbuka (29)

| ID | Mode | PRD | Jenis | Status | Bukti |
|---|---|---|---|---|---|
| `AR-82E1C012C83DFF` | BUSINESS_CASES | `PRD-RI-001` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/NV-176-PRD-Pendaftaran-Rawat-Inap-TPPRI-Neurovi-v… |
| `AR-34BD5C55FA501F` | BUSINESS_CASES | `PRD-RI-001` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/NV-176-PRD-Pendaftaran-Rawat-Inap-TPPRI-Neurovi-v… |
| `AR-E6741FEE7B0561` | BUSINESS_CASES | `PRD-RI-001` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/NV-176-PRD-Pendaftaran-Rawat-Inap-TPPRI-Neurovi-v… |
| `AR-99B174241909E8` | BUSINESS_CASES | `PRD-RI-001` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/NV-176-PRD-Pendaftaran-Rawat-Inap-TPPRI-Neurovi-v… |
| `AR-D40BF860989340` | BUSINESS_CASES | `PRD-RI-001` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/NV-176-PRD-Pendaftaran-Rawat-Inap-TPPRI-Neurovi-v… |
| `AR-5D25DBCD57720C` | BUSINESS_CASES | `PRD-RI-001` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/NV-176-PRD-Pendaftaran-Rawat-Inap-TPPRI-Neurovi-v… |
| `AR-837C24403FA737` | BUSINESS_CASES | `PRD-RI-001` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/NV-176-PRD-Pendaftaran-Rawat-Inap-TPPRI-Neurovi-v… |
| `AR-26F1EEC8D8CC02` | BUSINESS_CASES | `PRD-RI-002` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-D8C0461D61CE3D` | BUSINESS_CASES | `PRD-RI-003` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/NV-171-PRD-Dashboard-Pelayanan-Rawat-Inap-Neurovi… |
| `AR-542FFEC225DEFC` | BUSINESS_CASES | `PRD-RI-003` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/NV-171-PRD-Dashboard-Pelayanan-Rawat-Inap-Neurovi… |
| `AR-0B3A8D6116CCFC` | BUSINESS_CASES | `PRD-RI-003` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/NV-171-PRD-Dashboard-Pelayanan-Rawat-Inap-Neurovi… |
| `AR-E6239887F5767B` | BUSINESS_CASES | `PRD-RI-003` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/NV-171-PRD-Dashboard-Pelayanan-Rawat-Inap-Neurovi… |
| `AR-807A8B2D555535` | BUSINESS_CASES | `PRD-RI-003` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/NV-171-PRD-Dashboard-Pelayanan-Rawat-Inap-Neurovi… |
| `AR-B8361C970F6FCF` | BUSINESS_CASES | `PRD-RI-003` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/NV-171-PRD-Dashboard-Pelayanan-Rawat-Inap-Neurovi… |
| `AR-F5E75545D9657A` | BUSINESS_CASES | `PRD-RI-007` | ALTERNATE_CASE_CONTEXT | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-FFE9B4B054B2BD` | BUSINESS_CASES | `PRD-RI-007` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-0A767DE3043429` | BUSINESS_CASES | `PRD-RI-007` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-AC562EB2D45BE5` | BUSINESS_CASES | `PRD-RI-008` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-565032100574AB` | BUSINESS_CASES | `PRD-RI-008` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-3DC460341A80CD` | BUSINESS_CASES | `PRD-RI-009` | ALTERNATE_CASE_CONTEXT | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-49A5C00A40209E` | BUSINESS_CASES | `PRD-RI-009` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-8671E237FA193A` | BUSINESS_CASES | `PRD-RI-009` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-04EA2B45AB219A` | BUSINESS_CASES | `PRD-RI-010` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-71A31D27DFE757` | BUSINESS_CASES | `PRD-RI-015` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-24777AB664FBE6` | BUSINESS_CASES | `PRD-RI-015` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-A89B469D0A55A4` | BUSINESS_CASES | `PRD-RI-016` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-827F7FA2E07274` | BUSINESS_CASES | `PRD-RI-016` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-7BBC92EB14B8AA` | BUSINESS_CASES | `PRD-RI-016` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Ubah-DPJP.md:36 |
| `AR-7E90C5A5A224CC` | BUSINESS_CASES | `PRD-RI-019` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Discharge-Pasien.md:631 |

#### Sudah diperbaiki dari source fact (26)

| ID | Mode | PRD | Jenis | Bukti literal |
|---|---|---|---|---|
| `AR-375530758F2380` | BUSINESS_CASES | `PRD-RI-001` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/NV-176-PRD-Pendaftaran-Rawat-Inap-TPPRI-Neurovi-v… |
| `AR-7557A2F0364247` | BUSINESS_CASES | `PRD-RI-002` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-SPRI.md:110 |
| `AR-46240E72036EB6` | BUSINESS_CASES | `PRD-RI-003` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/NV-171-PRD-Dashboard-Pelayanan-Rawat-Inap-Neurovi… |
| `AR-6369462EF4A856` | BUSINESS_CASES | `PRD-RI-003` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/NV-171-PRD-Dashboard-Pelayanan-Rawat-Inap-Neurovi… |
| `AR-B628AA1AD51A05` | BUSINESS_CASES | `PRD-RI-004` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/N16__asesmen-awal-keperawatan-rawat-inap-anak.md:… |
| `AR-C553F6B5318423` | BUSINESS_CASES | `PRD-RI-004` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Pelayanan (.md)/N16__asesmen-awal-keperawatan-rawat-inap-anak.md:… |
| `AR-F5AC1CB9ED12DF` | BUSINESS_CASES | `PRD-RI-005` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/N17__asesmen-awal-keperawatan-rawat-inap-dewasa.m… |
| `AR-0CA1B7F9BB8B03` | BUSINESS_CASES | `PRD-RI-005` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Pelayanan (.md)/N17__asesmen-awal-keperawatan-rawat-inap-dewasa.m… |
| `AR-B851522FEFC6EE` | BUSINESS_CASES | `PRD-RI-005` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/N17__asesmen-awal-keperawatan-rawat-inap-dewasa.m… |
| `AR-2E0A948635B949` | BUSINESS_CASES | `PRD-RI-006` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/N18__asesmen-awal-keperawatan-rawat-inap-neonatus… |
| `AR-B6B58F887A39BD` | BUSINESS_CASES | `PRD-RI-006` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Pelayanan (.md)/N18__asesmen-awal-keperawatan-rawat-inap-neonatus… |
| `AR-A3A9A9601C9A88` | BUSINESS_CASES | `PRD-RI-006` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/N18__asesmen-awal-keperawatan-rawat-inap-neonatus… |
| `AR-332B1D2D055745` | BUSINESS_CASES | `PRD-RI-011` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-EWS-Anak.md:170 |
| `AR-D102D9F6824BF4` | BUSINESS_CASES | `PRD-RI-011` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-EWS-Anak.md:170 |
| `AR-151F0CEB8254D9` | BUSINESS_CASES | `PRD-RI-012` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-EWS-Dewasa.md:261 |
| `AR-1CC411B4832D03` | BUSINESS_CASES | `PRD-RI-012` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-EWS-Dewasa.md:208 |
| `AR-584E3613A801C0` | BUSINESS_CASES | `PRD-RI-013` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-EWS-Neonatus.md:142 |
| `AR-CF08B911269655` | BUSINESS_CASES | `PRD-RI-013` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-EWS-Neonatus.md:142 |
| `AR-C9123E70AFE9FC` | BUSINESS_CASES | `PRD-RI-014` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Titip-Kelas-Rawat-Inap-Neurovi-v2.md:168 |
| `AR-FA0F67F4AD68A0` | BUSINESS_CASES | `PRD-RI-017` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Update-Ketersediaan-Bed-Neurovi-v2-Rev.1.md:1… |
| `AR-207C17D993D053` | BUSINESS_CASES | `PRD-RI-017` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Update-Ketersediaan-Bed-Neurovi-v2-Rev.1.md:1… |
| `AR-E719740CB08C52` | BUSINESS_CASES | `PRD-RI-018` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-pindah-bed.md:209 |
| `AR-68075A0DB93372` | BUSINESS_CASES | `PRD-RI-018` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-pindah-bed.md:55 |
| `AR-65C099FD77BCB2` | BUSINESS_CASES | `PRD-RI-018` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-pindah-bed.md:209 |
| `AR-4219D5D3CB4522` | BUSINESS_CASES | `PRD-RI-019` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Discharge-Pasien.md:499 |
| `AR-A79A5CDCD37015` | MAIN_FLOW | `PRD-RI-007` | handoff | PRD/PRD Generator (.md)/Pelayanan (.md)/N22__asesmen-awal-medis-rawat-inap-anak.md:184 |

#### Keputusan terkonfirmasi (0)

Belum ada keputusan manusia yang tercatat.

### E2E-IGD | IGD

- Tujuan: Pendaftaran, asesmen, observasi, dan pelayanan gawat darurat.
- PRD: **9** | relasi: 53 | lintas-domain: 36
- Gap terbuka: **26** | fix source fact: **9** | dikecualikan: **4**
- Sesi: belum ada

| Kode | PRD | Stage |
|---|---|---|
| `PRD-IGD-001` | PRD — Pendaftaran IGD | ENTRY |
| `PRD-IGD-002` | Dashboard Pelayanan IGD | WORKLIST |
| `PRD-IGD-003` | PRD — Dashboard Retur Farmasi IGD dan Rawat Inap | WORKLIST |
| `PRD-IGD-004` | PRD — Asesmen Dokter IGD | ASSESSMENT |
| `PRD-IGD-005` | PRD — Asesmen Perawat IGD | ASSESSMENT |
| `PRD-IGD-006` | PRD — EMR RJ: Asesmen Perawat dan Dokter IGD | ASSESSMENT |
| `PRD-IGD-007` | PRD — Observasi IGD (Tab "Observasi Pasien" — Modul Asesmen Gawat Darurat) | ASSESSMENT |
| `PRD-IGD-008` | igd catatan pemberian obat | EXECUTION |
| `PRD-IGD-009` | PRD — CPPT IGD (Catatan Perkembangan Pasien Terintegrasi — Instalasi Gawat Daru… | EXECUTION |

#### Gap terbuka (26)

| ID | Mode | PRD | Jenis | Status | Bukti |
|---|---|---|---|---|---|
| `AR-A5EFDD4AD7851C` | BUSINESS_CASES | `PRD-IGD-001` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-E5F981D6599ADE` | BUSINESS_CASES | `PRD-IGD-001` | BUSINESS_RULES | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-A04CC5409E5B2F` | BUSINESS_CASES | `PRD-IGD-001` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-FB666FFCF48B66` | BUSINESS_CASES | `PRD-IGD-001` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-pendaftaran-pendaftaran-igd.md:50 |
| `AR-C51B6D94FAC142` | BUSINESS_CASES | `PRD-IGD-002` | ALTERNATE_CASE_CONTEXT | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-C22CDE2630267B` | BUSINESS_CASES | `PRD-IGD-002` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-F0CFFD90247FAA` | BUSINESS_CASES | `PRD-IGD-002` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-57D4E645C2A126` | BUSINESS_CASES | `PRD-IGD-004` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Asesmen-Dokter-IGD-v2.md:233 |
| `AR-28EEC954D04118` | BUSINESS_CASES | `PRD-IGD-005` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-655FAF2C15CF06` | BUSINESS_CASES | `PRD-IGD-005` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Asesmen-Perawat-IGD-v2_0.md:306 |
| `AR-89E8CCBD0E58FE` | BUSINESS_CASES | `PRD-IGD-005` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Asesmen-Perawat-IGD-v2_0.md:31 |
| `AR-E3136CEE29BA76` | BUSINESS_CASES | `PRD-IGD-005` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Asesmen-Perawat-IGD-v2_0.md:95 |
| `AR-B22CC7878A56DC` | BUSINESS_CASES | `PRD-IGD-006` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-DA5DE4FEA3FFD2` | BUSINESS_CASES | `PRD-IGD-006` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-F6330DBBAABCC8` | BUSINESS_CASES | `PRD-IGD-006` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-F11996D1BD6936` | BUSINESS_CASES | `PRD-IGD-006` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-emr-rj-asesmen-perawat-dan-dokter-igd (1).md:… |
| `AR-2391541BFDBB7A` | BUSINESS_CASES | `PRD-IGD-008` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-C6046537BFC620` | BUSINESS_CASES | `PRD-IGD-008` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-21CCCE802E7241` | BUSINESS_CASES | `PRD-IGD-008` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-igd-catatan-pemberian-obat.md:18 |
| `AR-5C45A8E0807632` | BUSINESS_CASES | `PRD-IGD-008` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-igd-catatan-pemberian-obat.md:19 |
| `AR-C33083D98FF5FB` | BUSINESS_CASES | `PRD-IGD-008` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-igd-catatan-pemberian-obat.md:20 |
| `AR-A5808CECE49B30` | BUSINESS_CASES | `PRD-IGD-008` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-igd-catatan-pemberian-obat.md:21 |
| `AR-09DFEC1A13FA65` | BUSINESS_CASES | `PRD-IGD-008` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-igd-catatan-pemberian-obat.md:22 |
| `AR-2D9935E2A26B90` | BUSINESS_CASES | `PRD-IGD-008` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-igd-catatan-pemberian-obat.md:23 |
| `AR-8DC84D77604567` | BUSINESS_CASES | `PRD-IGD-009` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-05D6C37B5C33AC` | BUSINESS_CASES | `PRD-IGD-009` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-CPPT-IGD.md:15 |

#### Sudah diperbaiki dari source fact (9)

| ID | Mode | PRD | Jenis | Bukti literal |
|---|---|---|---|---|
| `AR-070A4D95D71F41` | BUSINESS_CASES | `PRD-IGD-003` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Dashboard-Retur-Farmasi-IGD-Rawat-Inap.md:164 |
| `AR-081A49C7B45413` | BUSINESS_CASES | `PRD-IGD-003` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Dashboard-Retur-Farmasi-IGD-Rawat-Inap.md:164 |
| `AR-3E59704E462210` | BUSINESS_CASES | `PRD-IGD-004` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Asesmen-Dokter-IGD-v2.md:163 |
| `AR-874BF99DDB010E` | BUSINESS_CASES | `PRD-IGD-004` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Asesmen-Dokter-IGD-v2.md:147 |
| `AR-7186F20260097E` | BUSINESS_CASES | `PRD-IGD-005` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Asesmen-Perawat-IGD-v2_0.md:173 |
| `AR-71BFA470357650` | BUSINESS_CASES | `PRD-IGD-007` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Observasi-IGD.md:148 |
| `AR-64EC70B835CD5A` | BUSINESS_CASES | `PRD-IGD-007` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-Observasi-IGD.md:147 |
| `AR-147C24D07ED2B3` | BUSINESS_CASES | `PRD-IGD-008` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-igd-catatan-pemberian-obat.md:158 |
| `AR-4661273FA430C6` | BUSINESS_CASES | `PRD-IGD-009` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Pelayanan (.md)/PRD-CPPT-IGD.md:154 |

#### Keputusan terkonfirmasi (0)

Belum ada keputusan manusia yang tercatat.

### E2E-VK | VK dan Kebidanan

- Tujuan: Order tindakan dan pelayanan VK/kebidanan.
- PRD: **3** | relasi: 17 | lintas-domain: 15
- Gap terbuka: **3** | fix source fact: **3** | dikecualikan: **4**
- Sesi: belum ada

| Kode | PRD | Stage |
|---|---|---|
| `PRD-VK-001` | Order Tindakan VK | REQUEST |
| `PRD-VK-002` | PRD — Dashboard VK (E7a) | WORKLIST |
| `PRD-VK-003` | Product Requirement Document — E19 Surat Kontrol V1/V2 & PRB | EXECUTION |

#### Gap terbuka (3)

| ID | Mode | PRD | Jenis | Status | Bukti |
|---|---|---|---|---|---|
| `AR-11295D387BE991` | BUSINESS_CASES | `PRD-VK-002` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-216E47E366B66D` | BUSINESS_CASES | `PRD-VK-002` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-76AFB37F8BFD86` | BUSINESS_CASES | `PRD-VK-003` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |

#### Sudah diperbaiki dari source fact (3)

| ID | Mode | PRD | Jenis | Bukti literal |
|---|---|---|---|---|
| `AR-7184EBCE9CE476` | BUSINESS_CASES | `PRD-VK-001` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-Order-Tindakan-VK.md:72 |
| `AR-DA9297BB869621` | BUSINESS_CASES | `PRD-VK-002` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-Dashboard-VK.md:69 |
| `AR-3B55C56E4EAD90` | BUSINESS_CASES | `PRD-VK-003` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Pelayanan (.md)/prd-RI-RJ-VK-Surat Kontrol.md:81 |

#### Keputusan terkonfirmasi (0)

Belum ada keputusan manusia yang tercatat.

### E2E-MCU | Medical Check Up

- Tujuan: Pendaftaran dan paket pelayanan MCU.
- PRD: **1** | relasi: 11 | lintas-domain: 11
- Gap terbuka: **3** | fix source fact: **0** | dikecualikan: **1**
- Sesi: belum ada

| Kode | PRD | Stage |
|---|---|---|
| `PRD-MCU-001` | PRD — Pendaftaran MCU | ENTRY |

#### Gap terbuka (3)

| ID | Mode | PRD | Jenis | Status | Bukti |
|---|---|---|---|---|---|
| `AR-892923CB7AA5F1` | BUSINESS_CASES | `PRD-MCU-001` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-6916EBF8237ABD` | BUSINESS_CASES | `PRD-MCU-001` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-42CA15F1769517` | BUSINESS_CASES | `PRD-MCU-001` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |

#### Sudah diperbaiki dari source fact (0)

Belum ada fix pada cakupan register ini.

#### Keputusan terkonfirmasi (0)

Belum ada keputusan manusia yang tercatat.

## Kelompok: platform

### E2E-MASTER | Master Data dan Access Control

- Tujuan: Siklus master data, konfigurasi, pengguna, role, dan akses.
- PRD: **72** | relasi: 193 | lintas-domain: 103
- Gap terbuka: **141** | fix source fact: **78** | dikecualikan: **28**
- Sesi: belum ada

| Kode | PRD | Stage |
|---|---|---|
| `PRD-MASTER-001` | A19 — Master Data Instalasi | FOUNDATION |
| `PRD-MASTER-002` | A21 master data sediaan barang | FOUNDATION |
| `PRD-MASTER-003` | A23 master data spesialisasi dokter | FOUNDATION |
| `PRD-MASTER-004` | A24 master data aturan pakai | FOUNDATION |
| `PRD-MASTER-005` | A33 master data kategori barang (1) | FOUNDATION |
| `PRD-MASTER-006` | A34 master data hari libur | FOUNDATION |
| `PRD-MASTER-007` | A42 master data gudang dan farmasi new | FOUNDATION |
| `PRD-MASTER-008` | A53 admin rbac | FOUNDATION |
| `PRD-MASTER-009` | A55 master data jabatan | FOUNDATION |
| `PRD-MASTER-010` | Master Data Akses Menu | FOUNDATION |
| `PRD-MASTER-011` | Master Data Aset | FOUNDATION |
| `PRD-MASTER-012` | Master Data Barang Gizi | FOUNDATION |
| `PRD-MASTER-013` | Master Data Barang Rumah Tangga | FOUNDATION |
| `PRD-MASTER-014` | Master Data Hari Libur | FOUNDATION |
| `PRD-MASTER-015` | Master Data Kas dan Bank | FOUNDATION |
| `PRD-MASTER-016` | Master Data Sediaan | FOUNDATION |
| `PRD-MASTER-017` | Master Data Supplier | FOUNDATION |
| `PRD-MASTER-018` | PRD - Master Data: Paket Pelayanan MCU (A44) | FOUNDATION |
| `PRD-MASTER-019` | PRD — A35 Master Data: Farmaco (Golongan Farmakologi) — Tanpa UI | FOUNDATION |
| `PRD-MASTER-020` | PRD — Master Data / Integrasi SATUSEHAT BPJS V1 V2 — Procedure (ICD-9-CM) | FOUNDATION |
| `PRD-MASTER-021` | PRD — Master Data / Integrasi SATUSEHAT BPJS V1 V2 — Procedure (ICD-9-CM) | FOUNDATION |
| `PRD-MASTER-022` | PRD — Master Data / Integrasi SATUSEHAT BPJS V1 V2 — Procedure (ICD-9-CM) | FOUNDATION |
| `PRD-MASTER-023` | PRD — Master Data / Integrasi SATUSEHAT BPJS V1 V2 — Staff | FOUNDATION |
| `PRD-MASTER-024` | PRD — Master Data / Integrasi SATUSEHAT BPJS V2 — Item Pemeriksaan Laboratorium | FOUNDATION |
| `PRD-MASTER-025` | PRD — Master Data / Integrasi SATUSEHAT BPJS V2 — Item Pemeriksaan Laboratorium | FOUNDATION |
| `PRD-MASTER-026` | PRD — Master Data / Integrasi SATUSEHAT BPJS V2 — Item Pemeriksaan Laboratorium… | FOUNDATION |
| `PRD-MASTER-027` | PRD — Master Data / Integrasi SATUSEHAT Terminology V2 — ROA Obat | FOUNDATION |
| `PRD-MASTER-028` | PRD — Master Data / Integrasi SATUSEHAT Terminology V2: ROA Obat (A40) | FOUNDATION |
| `PRD-MASTER-029` | PRD — Master Data Anjuran Sukon (Anjuran Surat Kontrol) | FOUNDATION |
| `PRD-MASTER-030` | PRD — Master Data Barang Farmasi | FOUNDATION |
| `PRD-MASTER-031` | PRD — Master Data Bed (Control Panel) | FOUNDATION |
| `PRD-MASTER-032` | PRD — Master Data Diagnosa (A11) | FOUNDATION |
| `PRD-MASTER-033` | PRD — Master Data Diagnosa Perawat (Diagnosis Keperawatan) | FOUNDATION |
| `PRD-MASTER-034` | PRD — Master Data Diagnosa Perawat (SDKI) | FOUNDATION |
| `PRD-MASTER-035` | PRD — Master Data Diagnosa Perawat / SDKI (A12) | FOUNDATION |
| `PRD-MASTER-036` | PRD — Master Data Grup Obat | FOUNDATION |
| `PRD-MASTER-037` | PRD — Master Data Item Pemeriksaan Radiologi (New) | FOUNDATION |
| `PRD-MASTER-038` | PRD — Master Data Kamar | FOUNDATION |
| `PRD-MASTER-039` | PRD — Master Data Kamar (A16) | FOUNDATION |
| `PRD-MASTER-040` | PRD — Master Data Kelas (A58) | FOUNDATION |
| `PRD-MASTER-041` | PRD — Master Data Konfigurasi Tarif Pendaftaran | FOUNDATION |
| `PRD-MASTER-042` | PRD — Master Data Master Penomoran Surat | FOUNDATION |
| `PRD-MASTER-043` | PRD — Master Data Master Program Terapi | FOUNDATION |
| `PRD-MASTER-044` | PRD — Master Data Pabrikan (A54) | FOUNDATION |
| `PRD-MASTER-045` | PRD — Master Data Pemeriksaan Radiologi (A29, Integrasi SATUSEHAT BPJS V2) | FOUNDATION |
| `PRD-MASTER-046` | PRD — Master Data Pemeriksaan Radiologi (A29, Integrasi SATUSEHAT BPJS V2) | FOUNDATION |
| `PRD-MASTER-047` | PRD — Master Data Profesi (A57) | FOUNDATION |
| `PRD-MASTER-048` | PRD — Master Data Profil Rumah Sakit | FOUNDATION |
| `PRD-MASTER-049` | PRD — Master Data Rumah Sakit (N5) | FOUNDATION |
| `PRD-MASTER-050` | PRD — Master Data Satuan & Kemasan | FOUNDATION |
| `PRD-MASTER-051` | PRD — Master Data Standar Tarif Kamar (A43) | FOUNDATION |
| `PRD-MASTER-052` | PRD — Master Data Tindakan Operasi (N26) | FOUNDATION |
| `PRD-MASTER-053` | PRD — Master Data User (New) | FOUNDATION |
| `PRD-MASTER-054` | PRD — Master Data: Aturan Umum (New) | FOUNDATION |
| `PRD-MASTER-055` | PRD — Master Data: Instansi Rekanan | FOUNDATION |
| `PRD-MASTER-056` | PRD — Master Data: Kas dan Bank (A38) | FOUNDATION |
| `PRD-MASTER-057` | PRD — Master Data: Kategori Barang | FOUNDATION |
| `PRD-MASTER-058` | PRD — Master Data: Manajemen Loket & Antrean (Meja Antrian) | FOUNDATION |
| `PRD-MASTER-059` | PRD — Master Data: Menu Makanan | FOUNDATION |
| `PRD-MASTER-060` | PRD — Master Data: Paket Pelayanan MCU | FOUNDATION |
| `PRD-MASTER-061` | PRD — Master Data: Role (A18) | FOUNDATION |
| `PRD-MASTER-062` | PRD — Master Data: Ruang IBS (Instalasi Bedah Sentral) (A39) | FOUNDATION |
| `PRD-MASTER-063` | PRD — Master Data: Tarif Layanan (A10) | FOUNDATION |
| `PRD-MASTER-064` | PRD — Master Data: Tipe Penjamin (New) | FOUNDATION |
| `PRD-MASTER-065` | PRD — Master Data: Tipe Penjamin (New) | FOUNDATION |
| `PRD-MASTER-066` | PRD — Master Data: Unit (A3) | FOUNDATION |
| `PRD-MASTER-067` | Product Requirement Document (PRD) | FOUNDATION |
| `PRD-MASTER-068` | Product Requirement Document (PRD) — Jadwal Praktik | FOUNDATION |
| `PRD-MASTER-069` | Product Requirement Document (PRD) — Master Data Anjuran Sukon (Anjuran Surat K… | FOUNDATION |
| `PRD-MASTER-070` | Product Requirement Document (PRD) — Master Data Bed | FOUNDATION |
| `PRD-MASTER-071` | Product Requirement Document — Master Data Satuan dan Kemasan | FOUNDATION |
| `PRD-MASTER-072` | Product Requirement Document — Master Data Tipe Penjamin | FOUNDATION |

#### Gap terbuka (141)

| ID | Mode | PRD | Jenis | Status | Bukti |
|---|---|---|---|---|---|
| `AR-964F54F17186A0` | BUSINESS_CASES | `PRD-MASTER-003` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/A23__master-data-spesialisasi-dokter.md:90 |
| `AR-716DFC4FB8CD71` | BUSINESS_CASES | `PRD-MASTER-008` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-3CEEC612AAF588` | BUSINESS_CASES | `PRD-MASTER-010` | ALTERNATE_CASE_CONTEXT | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-E25E2E4DF1F1DD` | BUSINESS_CASES | `PRD-MASTER-010` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-6FE16D982FAD4D` | BUSINESS_CASES | `PRD-MASTER-010` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-85967A8DCB9436` | BUSINESS_CASES | `PRD-MASTER-011` | BUSINESS_RULES | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-A3AE65FF2D4D28` | BUSINESS_CASES | `PRD-MASTER-011` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-BC37D597CBA4F3` | BUSINESS_CASES | `PRD-MASTER-012` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-0EE941A0ED11EF` | BUSINESS_CASES | `PRD-MASTER-013` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-24B5030F1B0A4F` | BUSINESS_CASES | `PRD-MASTER-014` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-4DC00415138D36` | BUSINESS_CASES | `PRD-MASTER-014` | OUT_OF_SCOPE | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-C6148A7AB5DC0B` | BUSINESS_CASES | `PRD-MASTER-015` | BUSINESS_RULES | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-B9A38D19A52220` | BUSINESS_CASES | `PRD-MASTER-016` | BUSINESS_RULES | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-91669D1E170FBD` | BUSINESS_CASES | `PRD-MASTER-017` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-6F598B5AD88095` | BUSINESS_CASES | `PRD-MASTER-017` | BUSINESS_RULES | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-7E601A9BEF6088` | BUSINESS_CASES | `PRD-MASTER-017` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-62A06994F5773A` | BUSINESS_CASES | `PRD-MASTER-020` | ALTERNATE_CASE_CONTEXT | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-21F7B9B9F89F3E` | BUSINESS_CASES | `PRD-MASTER-020` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-73276F6DFAC506` | BUSINESS_CASES | `PRD-MASTER-021` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-B9A3D8FE97057A` | BUSINESS_CASES | `PRD-MASTER-022` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-F322C9C23F1EC5` | BUSINESS_CASES | `PRD-MASTER-024` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-7CAF3B9875A2AD` | BUSINESS_CASES | `PRD-MASTER-024` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-CABA55CB20B3AC` | BUSINESS_CASES | `PRD-MASTER-024` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-4F754FA26C6E4B` | BUSINESS_CASES | `PRD-MASTER-025` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-B21040218CF10B` | BUSINESS_CASES | `PRD-MASTER-025` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-94008C10F15A3F` | BUSINESS_CASES | `PRD-MASTER-027` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-CD65DDF63B1F29` | BUSINESS_CASES | `PRD-MASTER-027` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-51B3581B80BE8B` | BUSINESS_CASES | `PRD-MASTER-027` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-integrasi-satusehat-terminology… |
| `AR-08345D71C7297A` | BUSINESS_CASES | `PRD-MASTER-027` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-integrasi-satusehat-terminology… |
| `AR-E9695381A8B9DC` | BUSINESS_CASES | `PRD-MASTER-028` | ALTERNATE_CASE_CONTEXT | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-EA070D01363EC4` | BUSINESS_CASES | `PRD-MASTER-028` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-3036DEBCFE031E` | BUSINESS_CASES | `PRD-MASTER-028` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-B496E056B042EF` | BUSINESS_CASES | `PRD-MASTER-028` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-integrasi-satusehat-terminology… |
| `AR-9366A4FA6903F0` | BUSINESS_CASES | `PRD-MASTER-028` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-integrasi-satusehat-terminology… |
| `AR-28E2366E500B95` | BUSINESS_CASES | `PRD-MASTER-028` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-integrasi-satusehat-terminology… |
| `AR-BBFD181E7BE01C` | BUSINESS_CASES | `PRD-MASTER-028` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-integrasi-satusehat-terminology… |
| `AR-2F9C6F9E4BE51D` | BUSINESS_CASES | `PRD-MASTER-029` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-5D8FF2B9174059` | BUSINESS_CASES | `PRD-MASTER-029` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-24A97E857DD11B` | BUSINESS_CASES | `PRD-MASTER-029` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-B543AD6B2A9DC3` | BUSINESS_CASES | `PRD-MASTER-030` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-B33FE36335005F` | BUSINESS_CASES | `PRD-MASTER-030` | BUSINESS_RULES | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-DB798D9D1BE9CE` | BUSINESS_CASES | `PRD-MASTER-031` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-D6C2BDA338AE89` | BUSINESS_CASES | `PRD-MASTER-031` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-A8F12BD0167F68` | BUSINESS_CASES | `PRD-MASTER-031` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-468C4F7BC25578` | BUSINESS_CASES | `PRD-MASTER-031` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-bed (1).md:125 |
| `AR-30C65DE3BDA570` | BUSINESS_CASES | `PRD-MASTER-031` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-bed (1).md:142 |
| `AR-299AF87CDA2EF2` | BUSINESS_CASES | `PRD-MASTER-031` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-bed (1).md:144 |
| `AR-32A6D8F1BA8B2C` | BUSINESS_CASES | `PRD-MASTER-031` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-bed (1).md:172 |
| `AR-99D78252904B37` | BUSINESS_CASES | `PRD-MASTER-031` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-bed (1).md:173 |
| `AR-211CB4E3CB7A29` | BUSINESS_CASES | `PRD-MASTER-031` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-bed (1).md:180 |
| `AR-B109B14F2A35A1` | BUSINESS_CASES | `PRD-MASTER-031` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-bed (1).md:188 |
| `AR-352F3A605A70F9` | BUSINESS_CASES | `PRD-MASTER-031` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-bed (1).md:19 |
| `AR-5026F90595C23C` | BUSINESS_CASES | `PRD-MASTER-031` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-bed (1).md:20 |
| `AR-E6166DE6C537D1` | BUSINESS_CASES | `PRD-MASTER-031` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-bed (1).md:203 |
| `AR-6E8392393EFE44` | BUSINESS_CASES | `PRD-MASTER-031` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-bed (1).md:204 |
| `AR-A855C47A0C5F71` | BUSINESS_CASES | `PRD-MASTER-031` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-bed (1).md:225 |
| `AR-C351B9C135D1EB` | BUSINESS_CASES | `PRD-MASTER-031` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-bed (1).md:227 |
| `AR-41EFAB0FAD37FF` | BUSINESS_CASES | `PRD-MASTER-031` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-bed (1).md:252 |
| `AR-4F9F6D03254D7E` | BUSINESS_CASES | `PRD-MASTER-031` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-bed (1).md:33 |
| `AR-713D18B7B38155` | BUSINESS_CASES | `PRD-MASTER-031` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-bed (1).md:42 |
| `AR-D86A9934C5003D` | BUSINESS_CASES | `PRD-MASTER-031` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-bed (1).md:43 |
| `AR-FE8865B8C02FE0` | BUSINESS_CASES | `PRD-MASTER-031` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-bed (1).md:59 |
| `AR-D719012D63E21B` | BUSINESS_CASES | `PRD-MASTER-031` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-bed (1).md:60 |
| `AR-C69EC2A829BD34` | BUSINESS_CASES | `PRD-MASTER-031` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-bed (1).md:86 |
| `AR-3C22E23BAD2DEC` | BUSINESS_CASES | `PRD-MASTER-033` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-B1B2704183F07F` | BUSINESS_CASES | `PRD-MASTER-034` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-859C4752C96935` | BUSINESS_CASES | `PRD-MASTER-034` | ALTERNATE_CASE_CONTEXT | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-851734FA90EC7D` | BUSINESS_CASES | `PRD-MASTER-034` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-60DB282E16EA1C` | BUSINESS_CASES | `PRD-MASTER-034` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-20083417ACF591` | BUSINESS_CASES | `PRD-MASTER-035` | ALTERNATE_CASE_CONTEXT | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-225E8EF7DB025D` | BUSINESS_CASES | `PRD-MASTER-035` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-9C80409C207F09` | BUSINESS_CASES | `PRD-MASTER-035` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-1D0B1494E53CE5` | BUSINESS_CASES | `PRD-MASTER-036` | BUSINESS_RULES | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-7A8D6FEA359BA8` | BUSINESS_CASES | `PRD-MASTER-036` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-031E2CEE50AEBE` | BUSINESS_CASES | `PRD-MASTER-037` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-3DD9A8B9F9A008` | BUSINESS_CASES | `PRD-MASTER-038` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-95317D00A77AAB` | BUSINESS_CASES | `PRD-MASTER-038` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-331B25BAC9D6EC` | BUSINESS_CASES | `PRD-MASTER-039` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-7E8AB21170E791` | BUSINESS_CASES | `PRD-MASTER-040` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-41CED24EEECFF4` | BUSINESS_CASES | `PRD-MASTER-040` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-B4147A1517C5C2` | BUSINESS_CASES | `PRD-MASTER-042` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-80FC18B24C0209` | BUSINESS_CASES | `PRD-MASTER-043` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-C4D7C04447B3A8` | BUSINESS_CASES | `PRD-MASTER-043` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-3D73363007A0F9` | BUSINESS_CASES | `PRD-MASTER-044` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-2675C90F67E544` | BUSINESS_CASES | `PRD-MASTER-045` | ALTERNATE_CASE_CONTEXT | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-761CC1E2B30A27` | BUSINESS_CASES | `PRD-MASTER-045` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-8B20C524F2B88B` | BUSINESS_CASES | `PRD-MASTER-046` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-040B248CBA41EF` | BUSINESS_CASES | `PRD-MASTER-046` | ALTERNATE_CASE_CONTEXT | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-409CCA6C375697` | BUSINESS_CASES | `PRD-MASTER-046` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-86ACF12D32A73B` | BUSINESS_CASES | `PRD-MASTER-047` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-7BC98C332D1ED3` | BUSINESS_CASES | `PRD-MASTER-048` | ALTERNATE_CASE_CONTEXT | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-42ECFEB7B5D552` | BUSINESS_CASES | `PRD-MASTER-048` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-1F34E9960A4532` | BUSINESS_CASES | `PRD-MASTER-048` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-43AADA03D1DDE2` | BUSINESS_CASES | `PRD-MASTER-049` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-CD805AADCCAFF7` | BUSINESS_CASES | `PRD-MASTER-049` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-75A4D7DF2DF618` | BUSINESS_CASES | `PRD-MASTER-050` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-17C7B150CA03CA` | BUSINESS_CASES | `PRD-MASTER-050` | BUSINESS_RULES | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-B0A26ACD246378` | BUSINESS_CASES | `PRD-MASTER-050` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-56003D306EE849` | BUSINESS_CASES | `PRD-MASTER-051` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-7E9F8889F6E6AC` | BUSINESS_CASES | `PRD-MASTER-051` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-36A3E121048694` | BUSINESS_CASES | `PRD-MASTER-052` | ALTERNATE_CASE_CONTEXT | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-D1A15FF02B2BB7` | BUSINESS_CASES | `PRD-MASTER-052` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-0809082D77BC72` | BUSINESS_CASES | `PRD-MASTER-053` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-D56900081AD920` | BUSINESS_CASES | `PRD-MASTER-053` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-14B31C2C7E0D73` | BUSINESS_CASES | `PRD-MASTER-054` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-AEEA9F991CAD35` | BUSINESS_CASES | `PRD-MASTER-055` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-3CDB9BFE214687` | BUSINESS_CASES | `PRD-MASTER-055` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-BE8A08A28E87EC` | BUSINESS_CASES | `PRD-MASTER-055` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-2544089704AE16` | BUSINESS_CASES | `PRD-MASTER-056` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-649BF00A6BD702` | BUSINESS_CASES | `PRD-MASTER-056` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-4E7612FEC58FCC` | BUSINESS_CASES | `PRD-MASTER-057` | ALTERNATE_CASE_CONTEXT | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-F6EB957DA39922` | BUSINESS_CASES | `PRD-MASTER-057` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-4E11808579D04D` | BUSINESS_CASES | `PRD-MASTER-058` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-E31A96AD00783A` | BUSINESS_CASES | `PRD-MASTER-058` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-32FB37FB8EFE96` | BUSINESS_CASES | `PRD-MASTER-058` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-30CA5CFB3B7F47` | BUSINESS_CASES | `PRD-MASTER-059` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-571EFC684CC0BE` | BUSINESS_CASES | `PRD-MASTER-060` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-A59CA45ACF6B4E` | BUSINESS_CASES | `PRD-MASTER-060` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-99E7293A6A161B` | BUSINESS_CASES | `PRD-MASTER-060` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-paket-pelayanan-mcu_f.md:25 |
| `AR-2BB21E87748520` | BUSINESS_CASES | `PRD-MASTER-062` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-71EC65E840B077` | BUSINESS_CASES | `PRD-MASTER-063` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-89C00A1B4E9D06` | BUSINESS_CASES | `PRD-MASTER-063` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-B78F30BB4BEA07` | BUSINESS_CASES | `PRD-MASTER-064` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-7413C219092811` | BUSINESS_CASES | `PRD-MASTER-065` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-5EC9008B810BEF` | BUSINESS_CASES | `PRD-MASTER-066` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-1E4E2002DE0EAB` | BUSINESS_CASES | `PRD-MASTER-067` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd.md:230 |
| `AR-C0E8DFE1B3A35F` | BUSINESS_CASES | `PRD-MASTER-067` | OUT_OF_SCOPE | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-6A3B313D739933` | BUSINESS_CASES | `PRD-MASTER-068` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/PRD_Jadwal_Praktik.md:5 |
| `AR-D00B5BDB7BDB86` | BUSINESS_CASES | `PRD-MASTER-069` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-B43782EC799B02` | BUSINESS_CASES | `PRD-MASTER-070` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-867637D95771AF` | BUSINESS_CASES | `PRD-MASTER-070` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-bed.md:210 |
| `AR-96D05D74E2489C` | BUSINESS_CASES | `PRD-MASTER-070` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-bed.md:217 |
| `AR-7E40C0DCD9EA2B` | BUSINESS_CASES | `PRD-MASTER-070` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-bed.md:227 |
| `AR-E274108A9C7A3E` | BUSINESS_CASES | `PRD-MASTER-070` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-bed.md:340 |
| `AR-CE843B0CBBDD7D` | BUSINESS_CASES | `PRD-MASTER-070` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-bed.md:429 |
| `AR-21C36B65E1DA58` | BUSINESS_CASES | `PRD-MASTER-071` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-100B5EA00ABAAC` | BUSINESS_CASES | `PRD-MASTER-071` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-F159F7FE9A6D89` | BUSINESS_CASES | `PRD-MASTER-071` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-289BC71F10A613` | BUSINESS_CASES | `PRD-MASTER-072` | ACCEPTANCE_CRITERIA | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-65E679F18D9CFC` | BUSINESS_CASES | `PRD-MASTER-072` | ALTERNATE_FLOW | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |
| `AR-9FB719EA2582B8` | BUSINESS_CASES | `PRD-MASTER-072` | ERROR_EXCEPTION | OPEN_INSUFFICIENT_SOURCE_EVIDENCE | - |

#### Sudah diperbaiki dari source fact (78)

| ID | Mode | PRD | Jenis | Bukti literal |
|---|---|---|---|---|
| `AR-DCD16D469DA431` | BUSINESS_CASES | `PRD-MASTER-001` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-instalasi-fix.md:204 |
| `AR-A9AC988AB78B7D` | BUSINESS_CASES | `PRD-MASTER-001` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-instalasi-fix.md:165 |
| `AR-891FC87834ECBD` | BUSINESS_CASES | `PRD-MASTER-002` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Master Data (.md)/A21__master-data-sediaan-barang.md:185 |
| `AR-BE3F5B6FBFC8E7` | BUSINESS_CASES | `PRD-MASTER-002` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/A21__master-data-sediaan-barang.md:132 |
| `AR-6DEB85BA21F728` | BUSINESS_CASES | `PRD-MASTER-003` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Master Data (.md)/A23__master-data-spesialisasi-dokter.md:150 |
| `AR-DC237D703A8530` | BUSINESS_CASES | `PRD-MASTER-003` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/A23__master-data-spesialisasi-dokter.md:150 |
| `AR-98F1A9AF413605` | BUSINESS_CASES | `PRD-MASTER-004` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Master Data (.md)/A24__master-data-aturan-pakai.md:193 |
| `AR-D70480E240B314` | BUSINESS_CASES | `PRD-MASTER-004` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/A24__master-data-aturan-pakai.md:132 |
| `AR-1E520894DF60DD` | BUSINESS_CASES | `PRD-MASTER-005` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Master Data (.md)/A33__master-data-kategori-barang (1).md:187 |
| `AR-246EEB236A1754` | BUSINESS_CASES | `PRD-MASTER-005` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/A33__master-data-kategori-barang (1).md:131 |
| `AR-78CDF19433E380` | BUSINESS_CASES | `PRD-MASTER-006` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Master Data (.md)/A34__master-data-hari-libur.md:178 |
| `AR-7DC560699A437F` | BUSINESS_CASES | `PRD-MASTER-006` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Master Data (.md)/A34__master-data-hari-libur.md:70 |
| `AR-0DC1CC0914D173` | BUSINESS_CASES | `PRD-MASTER-006` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/A34__master-data-hari-libur.md:120 |
| `AR-A087BC67CEDED7` | BUSINESS_CASES | `PRD-MASTER-007` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Master Data (.md)/A42__master-data-gudang-dan-farmasi-new.md:55 |
| `AR-42F8F85600D52B` | BUSINESS_CASES | `PRD-MASTER-007` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/A42__master-data-gudang-dan-farmasi-new.md:213 |
| `AR-C248C0F4CE7A3A` | BUSINESS_CASES | `PRD-MASTER-008` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Master Data (.md)/A53__admin-rbac.md:161 |
| `AR-73B3A3179AC272` | BUSINESS_CASES | `PRD-MASTER-008` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Master Data (.md)/A53__admin-rbac.md:371 |
| `AR-94F7DA570FA7D3` | BUSINESS_CASES | `PRD-MASTER-009` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Master Data (.md)/A55__master-data-jabatan.md:184 |
| `AR-5CE16EA998CB28` | BUSINESS_CASES | `PRD-MASTER-009` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/A55__master-data-jabatan.md:305 |
| `AR-0F2F4C8930F5E1` | BUSINESS_CASES | `PRD-MASTER-010` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Master Data (.md)/PRD_Master_Data_Akses_Menu.md:302 |
| `AR-C4B8E2A454578F` | BUSINESS_CASES | `PRD-MASTER-011` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Master Data (.md)/PRD_Master_Data_Aset.md:174 |
| `AR-41BFB14FDC9F40` | BUSINESS_CASES | `PRD-MASTER-012` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/PRD_Master_Data_Barang_Gizi.md:179 |
| `AR-94AF6E93E590D7` | BUSINESS_CASES | `PRD-MASTER-013` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/PRD_Master_Data_Barang_Rumah_Tangga.md:186 |
| `AR-EEE80CF20182A6` | BUSINESS_CASES | `PRD-MASTER-014` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Master Data (.md)/PRD_Master_ Data_Hari_Libur.md:161 |
| `AR-66940965E31AB6` | BUSINESS_CASES | `PRD-MASTER-014` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/PRD_Master_ Data_Hari_Libur.md:130 |
| `AR-6D3676028859C4` | BUSINESS_CASES | `PRD-MASTER-015` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Master Data (.md)/PRD_Master_Data_Kas_dan_Bank.md:198 |
| `AR-389EA3827B64D7` | BUSINESS_CASES | `PRD-MASTER-015` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/PRD_Master_Data_Kas_dan_Bank.md:198 |
| `AR-1BF9990194568E` | BUSINESS_CASES | `PRD-MASTER-016` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Master Data (.md)/PRD_Master_Data_Sediaan.md:179 |
| `AR-9011F203286B63` | BUSINESS_CASES | `PRD-MASTER-016` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/PRD_Master_Data_Sediaan.md:179 |
| `AR-C7E254249827AC` | BUSINESS_CASES | `PRD-MASTER-018` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-paket-pelayanan.md:541 |
| `AR-F8ADE653C05252` | BUSINESS_CASES | `PRD-MASTER-018` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-paket-pelayanan.md:592 |
| `AR-56AA939201C14F` | BUSINESS_CASES | `PRD-MASTER-019` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Master Data (.md)/A35__master-data-farmaco.md:122 |
| `AR-219C7D0A2ABA41` | BUSINESS_CASES | `PRD-MASTER-019` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/A35__master-data-farmaco.md:121 |
| `AR-D34B8FA91BE33B` | BUSINESS_CASES | `PRD-MASTER-020` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/A13__master-data-procedure.md:104 |
| `AR-95F32DEAD76F0B` | BUSINESS_CASES | `PRD-MASTER-021` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-procedure-FIX.md:220 |
| `AR-1D4E2B741C300B` | BUSINESS_CASES | `PRD-MASTER-021` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-procedure-FIX.md:139 |
| `AR-69CA0FAA43AE16` | BUSINESS_CASES | `PRD-MASTER-022` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-procedure.md:190 |
| `AR-1C933722DFF4D3` | BUSINESS_CASES | `PRD-MASTER-022` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-procedure.md:124 |
| `AR-1F11A4D9CB3B1D` | BUSINESS_CASES | `PRD-MASTER-023` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-integrasi-satusehat-bpjs-v1-v2-… |
| `AR-9CFE72A3E99E5C` | BUSINESS_CASES | `PRD-MASTER-026` | ALTERNATE_CASE_CONTEXT | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-item-pemeriksaan-laboratorium -… |
| `AR-4FD42BADB6CF9C` | BUSINESS_CASES | `PRD-MASTER-026` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-item-pemeriksaan-laboratorium -… |
| `AR-F3C5C2B1017DC2` | BUSINESS_CASES | `PRD-MASTER-026` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-item-pemeriksaan-laboratorium -… |
| `AR-AAC2634D86C9ED` | BUSINESS_CASES | `PRD-MASTER-026` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-item-pemeriksaan-laboratorium -… |
| `AR-38E9495A6C8549` | BUSINESS_CASES | `PRD-MASTER-030` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/PRD_Master_Data_Barang_Farmasi.md:443 |
| `AR-A27B0339844EDE` | BUSINESS_CASES | `PRD-MASTER-032` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-diagnosa.md:254 |
| `AR-E3A05EB9949052` | BUSINESS_CASES | `PRD-MASTER-033` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Master Data (.md)/A12__master-data-diagnosa-perawat.md:265 |
| `AR-86CF9061F2A57F` | BUSINESS_CASES | `PRD-MASTER-033` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/A12__master-data-diagnosa-perawat.md:315 |
| `AR-AA1BA8DDF66BEE` | BUSINESS_CASES | `PRD-MASTER-036` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Master Data (.md)/Draft/PRD_Master_Data_Grup_Obat.md:164 |
| `AR-18EA3D005EE758` | BUSINESS_CASES | `PRD-MASTER-037` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Master Data (.md)/A29__master-data-item-pemeriksaan-radiologi.md:… |
| `AR-EEBE63BCD2D06C` | BUSINESS_CASES | `PRD-MASTER-037` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/A29__master-data-item-pemeriksaan-radiologi.md:… |
| `AR-8E7CF69775D618` | BUSINESS_CASES | `PRD-MASTER-038` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-kamar.md:138 |
| `AR-DF0E9BD0D6B24A` | BUSINESS_CASES | `PRD-MASTER-039` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Master Data (.md)/PRD_Master_Data_Kamar_Template New.md:167 |
| `AR-BB5740323220D5` | BUSINESS_CASES | `PRD-MASTER-039` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/PRD_Master_Data_Kamar_Template New.md:177 |
| `AR-E1509B0A7F2DF3` | BUSINESS_CASES | `PRD-MASTER-041` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/N1__master-data-konfigurasi-tarif-pendaftaran.m… |
| `AR-D4C389F5F1C98D` | BUSINESS_CASES | `PRD-MASTER-042` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Master Data (.md)/N3__master-data-master-penomoran-surat.md:106 |
| `AR-BF39D2711CDF6F` | BUSINESS_CASES | `PRD-MASTER-042` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/N3__master-data-master-penomoran-surat.md:145 |
| `AR-65A26D6CFB8252` | BUSINESS_CASES | `PRD-MASTER-045` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/master-data-integrasi-satusehat-bpjs-v2-item-pe… |
| `AR-0D50FBC96BDA44` | BUSINESS_CASES | `PRD-MASTER-046` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-integrasi-satusehat-bpjs-v2-ite… |
| `AR-1955531B8D1946` | BUSINESS_CASES | `PRD-MASTER-047` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-profesi.md:192 |
| `AR-C80682F75EC9C4` | BUSINESS_CASES | `PRD-MASTER-048` | CASES_CONDITIONS | PRD/PRD Generator (.md)/Master Data (.md)/N4__master-data-profil-rumah-sakit.md:43 |
| `AR-67F184FDDF2609` | BUSINESS_CASES | `PRD-MASTER-052` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/N26__master-data-tindakan-operasi.md:89 |
| `AR-E95625F7894A4D` | BUSINESS_CASES | `PRD-MASTER-054` | ALTERNATE_CASE_CONTEXT | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-aturan-umum-new- (2).md:162 |
| `AR-04AFCF57A1D37F` | BUSINESS_CASES | `PRD-MASTER-054` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-aturan-umum-new- (2).md:162 |
| `AR-220D49E509AEBB` | BUSINESS_CASES | `PRD-MASTER-054` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-aturan-umum-new- (2).md:200 |
| `AR-DBA5CEBC6111F9` | BUSINESS_CASES | `PRD-MASTER-057` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-kategori-barang.md:138 |
| `AR-BD420AB9B68B70` | BUSINESS_CASES | `PRD-MASTER-059` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-menu-makanan.md:149 |
| `AR-972C09EC316580` | BUSINESS_CASES | `PRD-MASTER-060` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-paket-pelayanan-mcu_f.md:139 |
| `AR-EF5574A88638D4` | BUSINESS_CASES | `PRD-MASTER-061` | ALTERNATE_CASE_CONTEXT | PRD/PRD Generator (.md)/Master Data (.md)/A18_master_data_role.md:209 |
| `AR-17AD2B487ABB50` | BUSINESS_CASES | `PRD-MASTER-061` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Master Data (.md)/A18_master_data_role.md:209 |
| `AR-972E74868F02B5` | BUSINESS_CASES | `PRD-MASTER-061` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/A18_master_data_role.md:101 |
| `AR-78F59E41834313` | BUSINESS_CASES | `PRD-MASTER-062` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-ruang-ibs.md:319 |
| `AR-3E478C4129F2C2` | BUSINESS_CASES | `PRD-MASTER-065` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-tipe-penjamin-new-.md:195 |
| `AR-EDB7A559CFA29C` | BUSINESS_CASES | `PRD-MASTER-067` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Master Data (.md)/prd.md:190 |
| `AR-4DB5A74B219119` | BUSINESS_CASES | `PRD-MASTER-067` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/prd.md:134 |
| `AR-340973A7950459` | BUSINESS_CASES | `PRD-MASTER-069` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Master Data (.md)/PRD_MASTER_DATA_ANJURAN_SUKON.md:44 |
| `AR-FAFDD56963F5B5` | MAIN_FLOW | `PRD-MASTER-010` | output | PRD/PRD Generator (.md)/Master Data (.md)/PRD_Master_Data_Akses_Menu.md:24 |
| `AR-7D8C47BE357EE0` | MAIN_FLOW | `PRD-MASTER-019` | output | PRD/PRD Generator (.md)/Master Data (.md)/A35__master-data-farmaco.md:34 |
| `AR-C4C6F5FADB6FFC` | MAIN_FLOW | `PRD-MASTER-072` | output | PRD/PRD Generator (.md)/Master Data (.md)/prd-master-data-tipe-penjamin.md:190 |

#### Keputusan terkonfirmasi (0)

Belum ada keputusan manusia yang tercatat.

### E2E-INTEGRASI | Integrasi Eksternal

- Tujuan: Pertukaran data dengan BPJS, SATUSEHAT, dan sistem eksternal.
- PRD: **1** | relasi: 1 | lintas-domain: 1
- Gap terbuka: **1** | fix source fact: **2** | dikecualikan: **1**
- Sesi: belum ada

| Kode | PRD | Stage |
|---|---|---|
| `PRD-INTEGRASI-001` | PRD I5 - Integrasi Aplicare BPJS | SUPPORTING |

#### Gap terbuka (1)

| ID | Mode | PRD | Jenis | Status | Bukti |
|---|---|---|---|---|---|
| `AR-786B8F59642429` | BUSINESS_CASES | `PRD-INTEGRASI-001` | EXPLICIT_UNRESOLVED_MARKER | OPEN_SOURCE_EXPLICIT_GAP | PRD/PRD Generator (.md)/Integrasi/prd-integrasi-aplicare-bpjs.md:202 |

#### Sudah diperbaiki dari source fact (2)

| ID | Mode | PRD | Jenis | Bukti literal |
|---|---|---|---|---|
| `AR-A10131E93B7131` | BUSINESS_CASES | `PRD-INTEGRASI-001` | ALTERNATE_FLOW | PRD/PRD Generator (.md)/Integrasi/prd-integrasi-aplicare-bpjs.md:101 |
| `AR-DB64CCC92C1D36` | BUSINESS_CASES | `PRD-INTEGRASI-001` | ERROR_EXCEPTION | PRD/PRD Generator (.md)/Integrasi/prd-integrasi-aplicare-bpjs.md:127 |

#### Keputusan terkonfirmasi (0)

Belum ada keputusan manusia yang tercatat.

