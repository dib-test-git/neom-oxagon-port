# customs-fasah

Pre-clearance submissions to **Saudi Customs (Fasah)** for vessels and containers berthing at Oxagon.

Tracks [KAN-36](https://neom.atlassian.net/browse/KAN-36). Active P1 bug: [KAN-53](https://neom.atlassian.net/browse/KAN-53) — Fasah submissions time out for vessels > 8000 TEU. See `src/chunker.py` for the in-flight workaround.

## How it works

1. SAP shipment-master events land on `oxagon.shipments.master.v1`.
2. `preclearance.py` enriches each shipment with HS codes, importer info, and tenant manifest.
3. `fasah_client.py` submits a `PreClearanceManifest` document to Fasah's REST API and stores the resulting `FasahReferenceNumber`.
4. Fasah responds asynchronously via webhook; status transitions are written to the `customs_status` table.

## Configuration

```
FASAH_BASE_URL=https://api.fasah.sa/customs/v2
FASAH_CLIENT_ID=...
FASAH_CLIENT_SECRET=...
FASAH_MAX_CONTAINERS_PER_SUBMISSION=2500   # see chunker.py
```

## Run

```bash
pip install -r requirements.txt
python -m src.preclearance
```
