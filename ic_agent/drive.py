import io
import logging
import os
import re
from typing import Any
import time
import random

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from ic_agent.config import GOOGLE_CREDENTIALS_PATH


logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
_drive_service = None


def _get_drive_service():
	"""Get or build a Google Drive service, with explicit, friendly errors.

	Raises FileNotFoundError for missing credentials and logs API/credential errors.
	"""
	global _drive_service
	if _drive_service is None:
		if not os.path.exists(GOOGLE_CREDENTIALS_PATH):
			logger.error("Google credentials file not found: %s", GOOGLE_CREDENTIALS_PATH)
			raise FileNotFoundError(f"Credentials file not found: {GOOGLE_CREDENTIALS_PATH}")

		try:
			credentials = service_account.Credentials.from_service_account_file(
				GOOGLE_CREDENTIALS_PATH,
				scopes=SCOPES,
			)
		except Exception as exc:
			logger.exception("Failed to load service account credentials: %s", exc)
			raise

		try:
			_drive_service = build("drive", "v3", credentials=credentials, cache_discovery=False)
		except Exception as exc:
			logger.exception("Failed to build Google Drive service: %s", exc)
			raise
	return _drive_service


def _with_retries(fn, *args, attempts: int = 3, base_delay: float = 1.0, **kwargs):
	last_exc = None
	for attempt in range(1, attempts + 1):
		try:
			return fn(*args, **kwargs)
		except Exception as exc:
			last_exc = exc
			wait = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
			logger.warning("Attempt %d/%d failed for %s: %s — retrying in %.1fs", attempt, attempts, getattr(fn, '__name__', str(fn)), exc, wait)
			time.sleep(wait)
	logger.exception("All %d attempts failed for %s", attempts, getattr(fn, '__name__', str(fn)))
	raise last_exc


def list_student_files(folder_id: str) -> list[dict[str, Any]]:
	"""List files directly under `folder_id`.

	For convenience keep this function but prefer `list_files_recursive` when
	you want to include files inside subfolders.
	"""
	service = _get_drive_service()
	query = f"'{folder_id}' in parents and trashed = false"

	def _call_list():
		return (
			service.files()
			.list(
				q=query,
				fields="files(id,name,mimeType,parents,modifiedTime)",
				pageSize=100,
				supportsAllDrives=True,
				includeItemsFromAllDrives=True,
			)
			.execute()
		)

	response = _with_retries(_call_list, attempts=3)
	return response.get("files", [])


def list_files_recursive(folder_id: str) -> list[dict[str, Any]]:
	"""Recursively list files under `folder_id`.

	Returns items with keys: id, name, mimeType, parents and parent_folder_name
	(immediate parent folder's name as discovered during traversal).
	"""
	service = _get_drive_service()

	def _get_meta(fid: str) -> dict[str, Any]:
		return (
			service.files()
			.get(fileId=fid, fields="id,name,mimeType", supportsAllDrives=True)
			.execute()
		)

	results: list[dict[str, Any]] = []
	stack: list[tuple[str, str]] = []

	# get starting folder name if possible
	try:
		root_meta = _with_retries(lambda: _get_meta(folder_id), attempts=2)
		root_name = root_meta.get("name", "")
	except Exception:
		root_name = ""

	stack.append((folder_id, root_name))
	seen: set[str] = set()

	while stack:
		fid, fname = stack.pop()
		if fid in seen:
			continue
		seen.add(fid)

		query = f"'{fid}' in parents and trashed = false"

		def _call_list():
			return (
				service.files()
				.list(
					q=query,
					fields="files(id,name,mimeType,parents,modifiedTime)",
					pageSize=200,
					supportsAllDrives=True,
					includeItemsFromAllDrives=True,
				)
				.execute()
			)

		resp = _with_retries(_call_list, attempts=3)
		for item in resp.get("files", []):
			item.setdefault("parents", [])
			item["parent_folder_name"] = fname
			results.append(item)
			if item.get("mimeType") == "application/vnd.google-apps.folder":
				# push folder to stack (use its name discovered in this listing)
				stack.append((item["id"], item.get("name", "")))

	return results


def _download_bytes(file_id: str) -> bytes:
	service = _get_drive_service()
	request = service.files().get_media(fileId=file_id, supportsAllDrives=True)

	def _do_download():
		stream = io.BytesIO()
		downloader = MediaIoBaseDownload(stream, request)
		done = False
		while not done:
			_, done = downloader.next_chunk()
		stream.seek(0)
		return stream.read()

	return _with_retries(_do_download, attempts=3)


def _export_google_doc_as_text(file_id: str) -> str:
	service = _get_drive_service()
	request = service.files().export_media(fileId=file_id, mimeType="text/plain")

	def _do_export():
		stream = io.BytesIO()
		downloader = MediaIoBaseDownload(stream, request)
		done = False
		while not done:
			_, done = downloader.next_chunk()
		stream.seek(0)
		return stream.read().decode("utf-8", errors="ignore")

	return _with_retries(_do_export, attempts=3)


def _extract_pdf_text(pdf_bytes: bytes) -> str:
	# Prefer robust extraction if an optional PDF parser is available.
	try:
		from pypdf import PdfReader  # type: ignore

		reader = PdfReader(io.BytesIO(pdf_bytes))
		text_chunks: list[str] = []
		for page in reader.pages:
			text_chunks.append(page.extract_text() or "")
		combined = "\n".join(text_chunks).strip()
		if combined:
			return combined
	except Exception as exc:
		logger.warning("Optional PDF parser unavailable or failed: %s", exc)

	# Lightweight fallback: recover printable text-like segments.
	candidates = re.findall(rb"\(([^\)]{2,400})\)", pdf_bytes)
	extracted = []
	for raw in candidates:
		cleaned = raw.replace(b"\\n", b" ").replace(b"\\r", b" ").replace(b"\\t", b" ")
		text = cleaned.decode("latin-1", errors="ignore").strip()
		if text:
			extracted.append(text)
	fallback = "\n".join(extracted).strip()
	if fallback:
		return fallback

	return "Unable to extract text from PDF content."


def read_file_content(file_id: str) -> str:
	service = _get_drive_service()
	metadata = (
		service.files()
		.get(fileId=file_id, fields="id,name,mimeType", supportsAllDrives=True)
		.execute()
	)

	name = metadata.get("name", "")
	mime_type = metadata.get("mimeType", "")

	if mime_type == "application/vnd.google-apps.document":
		return _export_google_doc_as_text(file_id)

	raw_content = _download_bytes(file_id)

	if mime_type == "application/pdf" or name.lower().endswith(".pdf"):
		return _extract_pdf_text(raw_content)

	return raw_content.decode("utf-8", errors="ignore")

