"""
File-level caching system to avoid rereading unchanged documents.
Uses file modification timestamps to detect changes.
"""

import os
import json
import logging
import hashlib
from pathlib import Path
from typing import Optional, Any, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FileCache:
    """
    Simple file cache with modification time tracking.
    Stores metadata and content to avoid rereading unchanged files.
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize cache. Use default .cache/ic_agent or custom path."""
        if cache_dir is None:
            cache_dir = os.path.expanduser("~/.cache/ic_agent")
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.cache_dir / "file_cache_metadata.json"
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load cache metadata from disk."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache metadata: {e}")
        return {}
    
    def _save_metadata(self):
        """Save cache metadata to disk."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache metadata: {e}")
    
    def _get_file_hash(self, file_path: str) -> str:
        """Get hash of file for change detection."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    def _get_cache_key(self, file_id: str, file_name: str) -> str:
        """Generate unique cache key for file."""
        return hashlib.md5(f"{file_id}_{file_name}".encode()).hexdigest()
    
    def get(self, file_id: str, file_name: str, current_hash: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get cached file content if available and unchanged.
        
        Args:
            file_id: Google Drive file ID
            file_name: File name for identification
            current_hash: Current file hash (optional, for validation)
            
        Returns:
            Cached file data or None if not found/invalid/expired
        """
        cache_key = self._get_cache_key(file_id, file_name)
        
        if cache_key not in self.metadata:
            return None
        
        meta = self.metadata[cache_key]
        
        # Check if cache is expired (older than 24 hours)
        cached_time = datetime.fromisoformat(meta.get("cached_at", "1970-01-01"))
        if datetime.now() - cached_time > timedelta(hours=24):
            logger.debug(f"Cache expired for {file_name}")
            return None
        
        # Check if file hash matches (if provided)
        if current_hash and meta.get("file_hash") != current_hash:
            logger.debug(f"File hash mismatch for {file_name} - invalidating cache")
            return None
        
        # Load from disk
        cache_file = self.cache_dir / meta["cache_file"]
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return {
                        "content": f.read(),
                        "cached_at": meta["cached_at"],
                        "readable": meta.get("readable", True)
                    }
            except Exception as e:
                logger.warning(f"Failed to read cache file {cache_file}: {e}")
        
        return None
    
    def set(self, file_id: str, file_name: str, content: str, file_hash: Optional[str] = None):
        """
        Cache file content.
        
        Args:
            file_id: Google Drive file ID
            file_name: File name
            content: File content to cache
            file_hash: File hash for change detection
        """
        cache_key = self._get_cache_key(file_id, file_name)
        cache_file_name = f"{cache_key}.txt"
        cache_file = self.cache_dir / cache_file_name
        
        try:
            # Write content to cache file
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Update metadata
            self.metadata[cache_key] = {
                "file_id": file_id,
                "file_name": file_name,
                "cache_file": cache_file_name,
                "cached_at": datetime.now().isoformat(),
                "file_hash": file_hash or "",
                "readable": bool(content.strip())
            }
            self._save_metadata()
            logger.debug(f"Cached {file_name} ({len(content)} bytes)")
        except Exception as e:
            logger.warning(f"Failed to cache {file_name}: {e}")
    
    def clear(self):
        """Clear all cached files."""
        try:
            for cache_file in self.cache_dir.glob("*.txt"):
                cache_file.unlink()
            self.metadata = {}
            self._save_metadata()
            logger.info("Cache cleared")
        except Exception as e:
            logger.warning(f"Failed to clear cache: {e}")
    
    def clear_expired(self):
        """Remove expired cache entries."""
        expired_keys = []
        for key, meta in self.metadata.items():
            cached_time = datetime.fromisoformat(meta.get("cached_at", "1970-01-01"))
            if datetime.now() - cached_time > timedelta(hours=24):
                expired_keys.append(key)
        
        for key in expired_keys:
            cache_file = self.cache_dir / self.metadata[key]["cache_file"]
            if cache_file.exists():
                cache_file.unlink()
            del self.metadata[key]
        
        if expired_keys:
            self._save_metadata()
            logger.info(f"Cleared {len(expired_keys)} expired cache entries")


class AnalysisCache:
    """
    Cache for analysis results indexed by (project_id, file_hash).
    Invalidates automatically when files change.
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize analysis cache."""
        if cache_dir is None:
            cache_dir = os.path.expanduser("~/.cache/ic_agent")
        
        self.cache_dir = Path(cache_dir) / "analysis"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.cache_dir / "analysis_metadata.json"
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load analysis cache metadata."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load analysis cache: {e}")
        return {}
    
    def _save_metadata(self):
        """Save analysis cache metadata."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save analysis cache: {e}")
    
    def _get_cache_key(self, project_name: str, file_hashes: Dict[str, str]) -> str:
        """Generate cache key from project name and file hashes."""
        combined = f"{project_name}_" + "_".join(
            f"{name}:{hash_val}" 
            for name, hash_val in sorted(file_hashes.items())
        )
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def get(self, project_name: str, file_hashes: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Get cached analysis if files unchanged."""
        cache_key = self._get_cache_key(project_name, file_hashes)
        
        if cache_key not in self.metadata:
            return None
        
        meta = self.metadata[cache_key]
        
        # Check expiration (48 hours)
        cached_time = datetime.fromisoformat(meta.get("cached_at", "1970-01-01"))
        if datetime.now() - cached_time > timedelta(hours=48):
            logger.debug(f"Analysis cache expired for {project_name}")
            return None
        
        # Load analysis result
        cache_file = self.cache_dir / meta["analysis_file"]
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read analysis cache: {e}")
        
        return None
    
    def set(self, project_name: str, file_hashes: Dict[str, str], analysis: Dict[str, Any]):
        """Cache analysis result."""
        cache_key = self._get_cache_key(project_name, file_hashes)
        analysis_file_name = f"{cache_key}.json"
        analysis_file = self.cache_dir / analysis_file_name
        
        try:
            with open(analysis_file, 'w') as f:
                json.dump(analysis, f, indent=2)
            
            self.metadata[cache_key] = {
                "project_name": project_name,
                "analysis_file": analysis_file_name,
                "cached_at": datetime.now().isoformat(),
                "file_count": len(file_hashes)
            }
            self._save_metadata()
            logger.debug(f"Cached analysis for {project_name}")
        except Exception as e:
            logger.warning(f"Failed to cache analysis: {e}")
    
    def clear(self):
        """Clear all analysis cache."""
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                if cache_file.name != "analysis_metadata.json":
                    cache_file.unlink()
            self.metadata = {}
            self._save_metadata()
            logger.info("Analysis cache cleared")
        except Exception as e:
            logger.warning(f"Failed to clear analysis cache: {e}")


# Global cache instances
_file_cache: Optional[FileCache] = None
_analysis_cache: Optional[AnalysisCache] = None


def get_file_cache() -> FileCache:
    """Get or create global file cache."""
    global _file_cache
    if _file_cache is None:
        _file_cache = FileCache()
    return _file_cache


def get_analysis_cache() -> AnalysisCache:
    """Get or create global analysis cache."""
    global _analysis_cache
    if _analysis_cache is None:
        _analysis_cache = AnalysisCache()
    return _analysis_cache
