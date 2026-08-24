# Neurovi PRD MCP Server

Remote MCP untuk memberi agent konteks implementasi dari immutable original PRD
dan, bila diaktifkan secara eksplisit, memperbarui workspace rekonsiliasi melalui
reconciliation-agent yang terisolasi. Server menggunakan authenticated
Streamable HTTP dan mengembalikan source reference serta status bukti agar
mechanical candidate tidak disalahartikan sebagai requirement yang disetujui.

## Security Boundary

- Bearer authentication wajib untuk setiap MCP request.
- Checkout `neurovi-prd` tetap di-mount read-only pada container MCP; semua
  update diteruskan ke reconciliation-agent melalui URL tetap yang dikonfigurasi.
- Setiap pembacaan PRD original diverifikasi terhadap SHA-256 di document index
  dan canonical manifest.
- Tidak ada arbitrary path, shell, Git mutation, baseline publish, database,
  Graphify mutation, atau URL fetch yang ditentukan caller. Update hanya memakai
  capability reconciliation yang di-whitelist pada gateway tetap.
- DNS-rebinding protection hanya menerima authority endpoint yang dikonfigurasi
  serta local health check.
- Container berjalan tanpa Linux capabilities, memakai
  `no-new-privileges`, dan dibatasi 128 PID.

Plain HTTP mengirim bearer token tanpa enkripsi TLS. Gunakan hanya pada private
LAN yang dibatasi firewall. Gunakan HTTPS reverse proxy atau private VPN bila
traffic melewati network yang tidak dipercaya.

## Safe Network Layout

MCP memakai file deployment terpisah, `compose.mcp.yaml`; deployment utama hanya
membuka reconciliation-agent pada loopback agar update gateway dapat dijangkau.
MCP memakai:

- `network_mode: host` untuk menghindari pembuatan bridge route/subnet baru;
- bind ke private IPv4 atau loopback yang eksplisit, bukan `0.0.0.0`;
- default port `8767`, terpisah dari Neurovi Documentation MCP pada `8766`;
- pemeriksaan port sebelum instalasi agar tidak mengambil listener existing;
- tanpa deklarasi `ports:` atau `networks:` di Compose.

## Install for Remote Clients

Pasang pada private LAN IP milik server, bukan pada IP client dan bukan pada
`127.0.0.1`:

```bash
./setup-prd-mcp.sh \
  --host-ip 192.168.1.20 \
  --host-port 8767 \
  --repository ./neurovi-prd
```

Pada server ini endpoint yang digunakan adalah:

```text
http://172.31.254.107:8767/mcp
```

Bind `127.0.0.1` hanya sesuai untuk development localhost atau bila MCP berada
di belakang reverse proxy lokal.

Installer menyimpan token dengan mode `0600` di
`~/.config/neurovi-prd-mcp/server.env`, atau
`/etc/neurovi-prd-mcp/server.env` bila dijalankan sebagai root.

Batasi akses firewall ke subnet client yang dibutuhkan:

```bash
sudo ufw allow from 192.168.1.0/24 to any port 8767 proto tcp
```

Health check tidak memerlukan bearer token:

```bash
curl http://192.168.1.20:8767/healthz
docker logs neurovi-prd-mcp
```

## Enable Controlled Reconciliation Updates

Default deployment tetap mengekspos enam read tools. Tujuh update tools baru
didaftarkan hanya bila seluruh konfigurasi gateway tersedia. Jalankan
reconciliation-agent dari deployment utama; port host-nya hanya dibuka pada
loopback:

```bash
docker compose up -d reconciliation-agent
```

Pastikan nilai `NEUROVI_AGENT_GATEWAY_TOKEN` dan
`NEUROVI_DISCORD_RECONCILE_ROLE_IDS` sudah terisi pada `.env` deployment utama.
Role ID yang sama dipakai sebagai actor role MCP. Tambahkan konfigurasi berikut
ke file environment MCP yang dibuat installer:

```env
NEUROVI_PRD_MCP_AGENT_GATEWAY_URL=http://127.0.0.1:8080/invoke
NEUROVI_PRD_MCP_AGENT_GATEWAY_TOKEN=<same-internal-gateway-token>
NEUROVI_PRD_MCP_AGENT_GATEWAY_TIMEOUT_SECONDS=180
NEUROVI_PRD_MCP_ACTOR_ID=mcp-operator
NEUROVI_PRD_MCP_ACTOR_NAME=Codex MCP Operator
NEUROVI_PRD_MCP_ACTOR_ROLE_IDS=<allowed-reconciliation-role-id>
```

Restart MCP setelah konfigurasi berubah:

```bash
docker compose \
  --project-name neurovi-prd-mcp \
  --env-file ~/.config/neurovi-prd-mcp/server.env \
  -f compose.mcp.yaml \
  up -d --build
```

Actor dan role berasal dari environment server, bukan parameter tool, sehingga
client tidak dapat mengaku sebagai actor lain. URL gateway harus berupa private
IPv4 atau loopback dan berakhir dengan `/invoke`. Jika konfigurasi hanya
sebagian, server gagal start; jika seluruh variabel kosong, server tetap
read-only.

Update tools hanya menulis session, register keputusan, referensi, dan audit
melalui reconciliation-agent. Mereka tidak mengedit `source/original/`, tidak
menjalankan `reconcile.finish`, dan tidak membuat commit, tag, push, atau
baseline release.

## Codex Client

Simpan token di environment client:

```bash
export NEUROVI_PRD_MCP_TOKEN='token-from-server'
```

Register remote MCP:

```bash
codex mcp add neurovi_prd \
  --url http://192.168.1.20:8767/mcp \
  --bearer-token-env-var NEUROVI_PRD_MCP_TOKEN
```

Konfigurasi `~/.codex/config.toml` yang setara:

```toml
[mcp_servers.neurovi_prd]
url = "http://192.168.1.20:8767/mcp"
bearer_token_env_var = "NEUROVI_PRD_MCP_TOKEN"
startup_timeout_sec = 20
tool_timeout_sec = 90
```

## Tools

### `prd_status`

Mengembalikan status authority, canonical baseline, jumlah PRD/E2E/relasi, dan
security capabilities efektif, termasuk apakah update workspace diaktifkan.

### `search_prds`

Mencari eligible original PRD berdasarkan kode, document ID, judul, filename,
path, dan literal source content. Pencarian dapat dibatasi ke satu E2E.

### `get_prd`

Membaca original Markdown secara checksum-verified. Konten lengkap tersedia
secara bertahap melalui `offset` dan `nextOffset`, atau per heading melalui
parameter `section`.

### `get_e2e_context`

Mengembalikan owner worklist, flow coverage, dan relation evidence untuk satu
E2E. Worklist besar dipaginasi dengan `document_offset` dan
`nextDocumentOffset`.

### `get_task_context`

Menyusun konteks task dari literal original sections untuk family purpose,
scope, flow, business rules, logical data, cases/exceptions, dan acceptance.
Hasil juga memuat inferred E2E ownership serta relasi terkait. Bila fragment
terpotong, lanjutkan dengan `get_prd`.

### `trace_prd_relations`

Menelusuri incoming/outgoing relation satu atau dua hop. Filter
`source-explicit` memisahkan evidence yang sudah source-explicit dari
`review-required` mechanical candidates.

Tool berikut hanya tersedia ketika controlled updates diaktifkan:

### `start_prd_reconciliation`

Memulai atau melanjutkan sesi untuk satu E2E dengan mode `main-flow` atau
`business-cases`. Kedua mode tetap memiliki workspace dan audit terpisah.

### `get_prd_reconciliation_status`

Mengembalikan status, workspace, event count, dan `current_question` terstruktur
untuk sesi yang sudah ada.

### `answer_prd_reconciliation`

Menyimpan jawaban atas pertanyaan aktif. Jawaban belum menjadi keputusan
semantik sampai dikonfirmasi melalui tool keputusan.

### `control_prd_reconciliation`

Menyimpan kontrol `SKIP`, `DEFER`, atau `UNKNOWN` tanpa mengarang jawaban.

### `add_prd_reconciliation_reference`

Mendaftarkan referensi pendukung. Referensi tidak berubah menjadi source fact
atau primary reconciliation source.

### `confirm_prd_reconciliation_decision`

Mencatat keputusan `USER_CONFIRMED`. Caller wajib mengirim
`confirmation=USER_CONFIRMED`; keputusan masuk ke register audit sebelum agent
melanjutkan proses.

### `stop_prd_reconciliation`

Mengakhiri working session sambil mempertahankan pertanyaan terbuka dan audit.
Caller wajib mengirim `confirmation=STOP_SESSION`. Tool ini tidak publish.

## Development Validation

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 src/neurovi_prd_server/mcp_server.py --repo neurovi-prd validate --deep
docker compose --env-file prd-mcp.env.example -f compose.mcp.yaml config --quiet
docker build -f Dockerfile.mcp -t neurovi-prd-mcp:test .
python3 scripts/build_structure.py validate \
  --source neurovi-prd/source/original \
  --target neurovi-prd
```
