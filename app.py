"""PDF Convert — a small web app for Word -> PDF and PDF -> Word conversion.

Word -> PDF uses LibreOffice (headless). PDF -> Word uses pdf2docx.
Uploaded files are processed in a temporary directory and deleted after
the response is sent; nothing is stored.
"""

import io
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "25"))
CONVERT_TIMEOUT = int(os.environ.get("CONVERT_TIMEOUT", "120"))
SOFFICE = os.environ.get("SOFFICE_BIN") or shutil.which("soffice") or shutil.which("libreoffice")

WORD_EXTS = {".doc", ".docx", ".odt", ".rtf"}
PDF_EXTS = {".pdf"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
log = logging.getLogger("pdf-convert")
logging.basicConfig(level=logging.INFO)


class ConversionError(Exception):
    pass


def word_to_pdf(src: Path, out_dir: Path) -> Path:
    if not SOFFICE:
        raise ConversionError("LibreOffice is not installed on the server.")
    # A private profile dir lets concurrent conversions run without locking each other.
    profile = out_dir / "lo-profile"
    cmd = [
        SOFFICE,
        f"-env:UserInstallation=file://{profile}",
        "--headless", "--norestore", "--nologo",
        "--convert-to", "pdf",
        "--outdir", str(out_dir),
        str(src),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=CONVERT_TIMEOUT)
    except subprocess.TimeoutExpired:
        raise ConversionError("Conversion timed out.")
    out = out_dir / (src.stem + ".pdf")
    if proc.returncode != 0 or not out.exists():
        log.error("soffice failed: %s %s", proc.stdout, proc.stderr)
        raise ConversionError("Could not convert this document. Is it a valid Word file?")
    return out


def pdf_to_word(src: Path, out_dir: Path) -> Path:
    from pdf2docx import Converter

    out = out_dir / (src.stem + ".docx")
    try:
        cv = Converter(str(src))
        try:
            cv.convert(str(out))
        finally:
            cv.close()
    except Exception as exc:  # pdf2docx raises a variety of errors on bad input
        log.exception("pdf2docx failed")
        raise ConversionError("Could not convert this PDF. It may be damaged or encrypted.") from exc
    if not out.exists():
        raise ConversionError("Conversion produced no output.")
    return out


MODES = {
    "word-to-pdf": (WORD_EXTS, word_to_pdf, "application/pdf"),
    "pdf-to-word": (
        PDF_EXTS,
        pdf_to_word,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),
}


@app.get("/")
def index():
    return render_template("index.html", max_mb=MAX_UPLOAD_MB)


@app.get("/healthz")
def healthz():
    return {"ok": True, "libreoffice": bool(SOFFICE)}


@app.post("/api/convert/<mode>")
def convert(mode):
    if mode not in MODES:
        return jsonify(error="Unknown conversion."), 404
    allowed, fn, mimetype = MODES[mode]

    upload = request.files.get("file")
    if not upload or not upload.filename:
        return jsonify(error="No file uploaded."), 400

    name = secure_filename(upload.filename) or "document"
    ext = Path(name).suffix.lower()
    if ext not in allowed:
        return jsonify(error=f"Please upload a {', '.join(sorted(allowed))} file."), 400

    work = Path(tempfile.mkdtemp(prefix="convert-"))
    try:
        src = work / name
        upload.save(src)
        try:
            out = fn(src, work)
        except ConversionError as exc:
            return jsonify(error=str(exc)), 422
        data = io.BytesIO(out.read_bytes())
        download_name = out.name
    finally:
        shutil.rmtree(work, ignore_errors=True)

    return send_file(data, mimetype=mimetype, as_attachment=True, download_name=download_name)


@app.errorhandler(413)
def too_large(_):
    return jsonify(error=f"File is too large. The limit is {MAX_UPLOAD_MB} MB."), 413


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), debug=False)
