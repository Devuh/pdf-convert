# PDF Convert

A small website for converting **Word → PDF** and **PDF → Word**.

- Word → PDF (`.doc`, `.docx`, `.odt`, `.rtf`) uses headless LibreOffice, so layout, fonts and tables are kept.
- PDF → Word (`.docx`) uses [pdf2docx](https://github.com/ArtifexSoftware/pdf2docx). This works for PDFs with real text; scanned (image-only) PDFs come out as images, since there is no OCR.
- Uploads are converted in a temp folder and deleted right away. Nothing is stored.

## Run with Docker (recommended)

```bash
docker build -t pdf-convert .
docker run -p 8000:8000 pdf-convert
```

Open http://localhost:8000.

## Run locally

Needs Python 3.10+ and LibreOffice (`soffice` on your PATH).

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

## Settings (environment variables)

| Variable          | Default | Meaning                                |
|-------------------|---------|----------------------------------------|
| `PORT`            | `8000`  | Port to listen on                      |
| `MAX_UPLOAD_MB`   | `25`    | Largest upload accepted                |
| `CONVERT_TIMEOUT` | `120`   | Seconds before a Word → PDF job aborts |
| `SOFFICE_BIN`     | auto    | Path to the LibreOffice binary         |

## API

`POST /api/convert/word-to-pdf` or `POST /api/convert/pdf-to-word` with a multipart `file` field. Returns the converted file, or JSON `{"error": "..."}` on failure.

```bash
curl -F file=@report.docx localhost:8000/api/convert/word-to-pdf -o report.pdf
```
