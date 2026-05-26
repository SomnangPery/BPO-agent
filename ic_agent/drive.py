import io
import logging
import os
import re
import zipfile
from typing import Any
import time
import random

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from ic_agent.config import GOOGLE_CREDENTIALS_PATH
from ic_agent.fuzzy import classify_file_by_name


logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
_drive_service = None


def _get_drive_service():
	global _drive_service
	if _drive_service is None:
		if not os.path.exists(GOOGLE_CREDENTIALS_PATH):
			raise FileNotFoundError(f"Credentials file not found: {GOOGLE_CREDENTIALS_PATH}")
		credentials = service_account.Credentials.from_service_account_file(
			GOOGLE_CREDENTIALS_PATH,
			scopes=SCOPES,
		)
		_drive_service = build("drive", "v3", credentials=credentials, cache_discovery=False)
	return _drive_service


def _with_retries(fn, *args, attempts: int = 3, base_delay: float = 1.0, **kwargs):
	last_exc = None
	for attempt in range(1, attempts + 1):
		try:
			return fn(*args, **kwargs)
		except Exception as exc:
			last_exc = exc
			wait = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
			time.sleep(wait)
	raise last_exc

def get_all_projects(root_folder_id: str) -> list[dict[str, Any]]:
	"""Returns all subfolders in root IC folder as projects."""
	service = _get_drive_service()
	query = f"'{root_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
	
	results = service.files().list(
		q=query,
		fields="files(id, name)",
		pageSize=1000,
		supportsAllDrives=True,
		includeItemsFromAllDrives=True,
	).execute()

	projects = []
	for folder in results.get("files", []):
		projects.append({
			"project_name": folder["name"],
			"folder_id": folder["id"]
		})
	return projects

def _download_bytes(file_id: str) -> bytes:
	service = _get_drive_service()
	request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
	stream = io.BytesIO()
	downloader = MediaIoBaseDownload(stream, request)
	done = False
	while not done:
		_, done = downloader.next_chunk()
	stream.seek(0)
	return stream.read()

def _extract_pdf_text(pdf_bytes: bytes) -> str:
	try:
		from pypdf import PdfReader
		reader = PdfReader(io.BytesIO(pdf_bytes))
		return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
	except Exception:
		return "Unreadable PDF"

def _export_google_doc_as_text(file_id: str) -> str:
	service = _get_drive_service()
	return service.files().export_media(fileId=file_id, mimeType="text/plain").execute().decode("utf-8")

def read_file_content(file_id: str, mime_type: str = "") -> str:
	try:
		if mime_type == "application/vnd.google-apps.document":
			return _export_google_doc_as_text(file_id)
		
		raw = _download_bytes(file_id)
		if "pdf" in mime_type or file_id.endswith(".pdf"):
			return _extract_pdf_text(raw)
			
		return raw.decode("utf-8", errors="ignore")
	except Exception:
		return ""

def classify_project_files(folder_id: str) -> dict[str, Any]:
	"""Lists all files in project folder and classifies them."""
	service = _get_drive_service()
	query = f"'{folder_id}' in parents and trashed=false"
	
	results = service.files().list(
		q=query,
		fields="files(id, name, mimeType)",
		pageSize=200,
		supportsAllDrives=True,
		includeItemsFromAllDrives=True,
	).execute()

	classified = {"oppm": None, "srs": None, "reports": []}

	for f in results.get("files", []):
		content = read_file_content(f["id"], f["mimeType"])
		
		info = {
			"file_id": f["id"],
			"file_name": f["name"],
			"mime_type": f["mimeType"],
			"content": content,
			"readable": bool(content.strip())
		}

		# Use fuzzy matching to classify file
		category, confidence = classify_file_by_name(f["name"])
		
		if category == "oppm" and confidence >= 75:
			if classified["oppm"] is None:
				classified["oppm"] = info
				logger.info(f"Classified '{f['name']}' as OPPM (confidence: {confidence}%)")
			elif confidence > 90:  # Replace if higher confidence
				classified["oppm"] = info
		elif category == "srs" and confidence >= 75:
			if classified["srs"] is None:
				classified["srs"] = info
				logger.info(f"Classified '{f['name']}' as SRS (confidence: {confidence}%)")
			elif confidence > 90:  # Replace if higher confidence
				classified["srs"] = info
		else:
			# Default to reports if category is "report" or no confident match
			classified["reports"].append(info)
			if category != "report":
				logger.debug(f"File '{f['name']}' classified as report (category: {category}, confidence: {confidence}%)")

	return classified


# ============================================================================
# Compatibility wrappers for web.py (maps student to project terminology)
# ============================================================================

def list_student_files(folder_id: str) -> list[dict[str, Any]]:
	"""Compatibility wrapper: list all files in a student/project folder."""
	service = _get_drive_service()
	query = f"'{folder_id}' in parents and trashed=false"
	
	results = service.files().list(
		q=query,
		fields="files(id, name, mimeType, createdTime, modifiedTime)",
		pageSize=200,
		supportsAllDrives=True,
		includeItemsFromAllDrives=True,
	).execute()
	
	return [
		{
			"id": f["id"],
			"name": f["name"],
			"mime_type": f["mimeType"],
			"created": f.get("createdTime"),
			"modified": f.get("modifiedTime"),
		}
		for f in results.get("files", [])
	]

def list_files_recursive(folder_id: str) -> list[dict[str, Any]]:
	"""Compatibility wrapper: list all files recursively in a folder."""
	service = _get_drive_service()
	all_files = []
	
	def _recurse(parent_id: str):
		query = f"'{parent_id}' in parents and trashed=false"
		results = service.files().list(
			q=query,
			fields="files(id, name, mimeType, createdTime, modifiedTime)",
			pageSize=200,
			supportsAllDrives=True,
			includeItemsFromAllDrives=True,
		).execute()
		
		for f in results.get("files", []):
			all_files.append({
				"id": f["id"],
				"name": f["name"],
				"mime_type": f["mimeType"],
				"created": f.get("createdTime"),
				"modified": f.get("modifiedTime"),
			})
			# If it's a folder, recurse into it
			if f["mimeType"] == "application/vnd.google-apps.folder":
				_recurse(f["id"])
	
	_recurse(folder_id)
	return all_files

def get_all_students(root_folder_id: str) -> list[dict[str, Any]]:
	"""Compatibility wrapper: get all students (projects)."""
	return get_all_projects(root_folder_id)

def classify_student_files(folder_id: str) -> dict[str, Any]:
	"""Compatibility wrapper: classify student files (projects)."""
	return classify_project_files(folder_id)
