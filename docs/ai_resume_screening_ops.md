# AI Resume Screening — Ops Notes

Provider-owned bulk resume screening. Batches, resumes, and reports live under private storage and are never public URLs.

## Environment quotas

| Variable | Default | Purpose |
|---|---|---|
| `SCREENING_MAX_RESUMES_PER_BATCH` | `500` | Hard cap per batch |
| `SCREENING_MAX_CONCURRENT_BATCHES` | `3` | Active (queued/processing/uploading) per provider |
| `SCREENING_MAX_FILE_MB` | `10` | Per-file upload limit |
| `SCREENING_MONTHLY_RESUME_LIMIT` | `2000` | Uploaded resumes per provider calendar month |
| `SCREENING_CHUNK_SIZE` | `25` | Pipeline progress chunk size |
| `SCREENING_PARSER_VERSION` | `rm-screening-1.0` | Stored on profiles |
| `SCREENING_SCORING_VERSION` | `1.0` | Stored on matches |
| `SCREENING_RETENTION_DAYS` | `90` | Hard-delete age for expired batches |
| `TESSERACT_CMD` | _(empty)_ | Optional absolute path to `tesseract` |

There is no separate screening subscription SKU yet — quotas are env-only.

## Celery

| Task | Queue | Schedule |
|---|---|---|
| `process_screening_batch_task` | `ai_and_heavy` | On demand (start / retry) |
| `generate_screening_report_task` | `ai_and_heavy` | On demand |
| `purge_expired_screening_batches_task` | `default` | Daily **03:15 Asia/Kolkata** (beat) |

Workers that consume `ai_and_heavy` must be running for parse/match/report. Beat must be running for retention. After deploying new beat tasks, restart **celery-worker** and **celery-beat**.

## Private storage path

```
{UPLOAD_DIR}/private/screening/{provider_id}/{batch_id}/
  ├── {uuid}.pdf|docx|doc|txt     # resumes
  └── reports/{report_id}.{csv|xlsx|pdf}
```

- Keys are relative to `private/screening` and resolved with path-traversal checks.
- Retention deletes storage keys then the batch directory, then hard-deletes the DB row (cascade).
- Active statuses `queued` / `processing` / `uploading` are never purged mid-run.

## Migration

- Revision ID: **`v8w9x0y1z2a3`**
- File: `migrations/versions/20261027_1200_v8w9x0y1z2a3_add_ai_resume_screening_tables.py`
- Tables: `screening_batches`, `screening_batch_resumes`, `screening_resume_profiles`, `screening_jds`, `screening_candidate_matches`, `screening_task_events`, `screening_reports`

## Host dependencies (OCR / legacy DOC)

Parsing reuses `app.shared.services.resume_parser`:

- **PDF**: PyMuPDF; scanned PDFs fall back to **pypdfium2 + pytesseract** when Tesseract is installed.
- **DOCX**: python-docx.
- **DOC (legacy)**: optional **`antiword`** on `PATH`; without it, `.doc` extraction is weak/empty.
- **TXT**: plain read.

Install Tesseract (`TESSERACT_CMD` if not on PATH) and `antiword` on worker images that must handle scanned PDFs / `.doc`. OCR is best-effort — failures mark the resume failed/poor quality rather than crashing the batch.

## Security / product limitations

- **No antivirus scanning** of uploads. Rely on type/MIME/size checks and private storage only. Plan AV or malware scanning before exposing higher trust surfaces.
- Ownership is enforced in the service layer (`get_owned_batch`: `provider_id == current user`). Cross-provider batch IDs return 404.
- Matching is deterministic skill/experience scoring (not LLM hiring decisions). Scores can be wrong on sparse OCR text.
- Password-protected PDFs are rejected at upload.
- Images (`.jpg`/`.png`) are not accepted as screening uploads (use PDF/DOCX/TXT/DOC).
- Retention is **hard-delete** (DB + files). There is no soft-delete / recycle bin.
- Reports may contain candidate PII extracted from resumes — treat downloads as sensitive.
