"""
Embeddings generation and management for semantic search.
"""

import json
import hashlib
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingsManager:
    """Manages embedding generation and caching for vault notes."""

    def __init__(
        self,
        cache_dir: str = ".mcp-obsidian",
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        """
        Initialize the embeddings manager.

        Args:
            cache_dir: Directory for caching embeddings
            model_name: Sentence transformer model to use
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        self.cache_file = self.cache_dir / "embeddings-cache.json"
        self.model_name = model_name

        # Lazy load model to avoid loading on import
        self._model = None
        self._cache: Optional[Dict[str, Any]] = None

        logger.info(f"EmbeddingsManager initialized with model: {model_name}")

    @property
    def model(self):
        """Lazy load the sentence transformer model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                logger.info(f"Loading sentence transformer model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
                logger.info("Model loaded successfully")
            except ImportError:
                raise ImportError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                raise

        return self._model

    def _compute_content_hash(self, content: str) -> str:
        """Compute hash of note content for cache invalidation."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def _extract_frontmatter(self, content: str) -> Tuple[Dict[str, Any], str]:
        """
        Extract frontmatter and body from note content.

        Returns:
            Tuple of (frontmatter_dict, body_text)
        """
        if not content.startswith("---"):
            return {}, content

        try:
            parts = content.split("---", 2)
            if len(parts) >= 3:
                import yaml

                frontmatter = yaml.safe_load(parts[1]) or {}
                body = parts[2].strip()
                return frontmatter, body
        except Exception as e:
            logger.warning(f"Failed to parse frontmatter: {e}")

        return {}, content

    def _clean_markdown(self, text: str) -> str:
        """
        Clean markdown text for embedding generation.

        Removes:
        - Wiki links [[...]]
        - Markdown links [text](url)
        - Images ![...]
        - Code blocks
        - Excessive whitespace
        """
        # Remove code blocks
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        text = re.sub(r"`[^`]+`", "", text)

        # Remove images
        text = re.sub(r"!\[.*?\]\(.*?\)", "", text)

        # Convert wiki links to plain text
        text = re.sub(r"\[\[(.*?)\]\]", r"\1", text)

        # Convert markdown links to plain text
        text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)

        # Remove headers markers but keep text
        text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)

        # Remove excessive whitespace
        text = re.sub(r"\n\s*\n", "\n\n", text)
        text = text.strip()

        return text

    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for text.

        Args:
            text: Input text

        Returns:
            Normalized embedding vector
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return np.zeros(self.model.get_sentence_embedding_dimension())

        embedding = self.model.encode(
            text, normalize_embeddings=True, show_progress_bar=False
        )

        return embedding

    def generate_note_embedding(
        self, filepath: str, content: str
    ) -> Dict[str, Any]:
        """
        Generate embedding for a note with metadata.

        Args:
            filepath: Path to the note
            content: Note content

        Returns:
            Dict with embedding, hash, and metadata
        """
        # Extract frontmatter and body
        frontmatter, body = self._extract_frontmatter(content)

        # Clean markdown
        clean_body = self._clean_markdown(body)

        # Build contextual text for embedding
        # Include title and tags for better semantic understanding
        note_name = Path(filepath).stem

        title = (
            frontmatter.get("name")
            or frontmatter.get("project")
            or frontmatter.get("title")
            or note_name
        )

        tags = frontmatter.get("tags", [])
        if isinstance(tags, list):
            tags_text = " ".join(f"#{tag}" for tag in tags)
        else:
            tags_text = ""

        # Combine for embedding
        contextual_text = f"{title}\n\n{tags_text}\n\n{clean_body}"

        # Generate embedding
        embedding = self.generate_embedding(contextual_text)

        # Compute content hash
        content_hash = self._compute_content_hash(content)

        return {
            "embedding": embedding.tolist(),
            "hash": content_hash,
            "timestamp": datetime.now().isoformat(),
            "filepath": filepath,
            "title": title,
            "tags": tags if isinstance(tags, list) else [],
        }

    def batch_generate_embeddings(
        self, notes: List[Dict[str, str]], show_progress: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Generate embeddings for multiple notes efficiently.

        Args:
            notes: List of dicts with 'filepath' and 'content'
            show_progress: Show progress bar

        Returns:
            List of embedding dicts
        """
        results = []

        if show_progress:
            try:
                from tqdm import tqdm

                notes_iter = tqdm(notes, desc="Generating embeddings")
            except ImportError:
                notes_iter = notes
                logger.info(f"Processing {len(notes)} notes...")
        else:
            notes_iter = notes

        for note in notes_iter:
            try:
                result = self.generate_note_embedding(
                    note["filepath"], note["content"]
                )
                results.append(result)
            except Exception as e:
                logger.error(
                    f"Failed to generate embedding for {note['filepath']}: {e}"
                )
                # Add placeholder for failed note
                results.append(
                    {
                        "filepath": note["filepath"],
                        "error": str(e),
                        "embedding": None,
                    }
                )

        return results

    def load_cache(self) -> Dict[str, Dict[str, Any]]:
        """Load embeddings cache from disk."""
        if self._cache is not None:
            return self._cache

        if not self.cache_file.exists():
            self._cache = {
                "model": self.model_name,
                "dimension": self.model.get_sentence_embedding_dimension(),
                "notes": {},
            }
            return self._cache

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Check if model changed
            if data.get("model") != self.model_name:
                logger.warning(
                    f"Model changed from {data.get('model')} to {self.model_name}. "
                    "Cache will be rebuilt."
                )
                self._cache = {
                    "model": self.model_name,
                    "dimension": self.model.get_sentence_embedding_dimension(),
                    "notes": {},
                }
            else:
                self._cache = data

            logger.info(f"Loaded cache with {len(self._cache.get('notes', {}))} notes")
            return self._cache

        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            self._cache = {
                "model": self.model_name,
                "dimension": self.model.get_sentence_embedding_dimension(),
                "notes": {},
            }
            return self._cache

    def save_cache(self, embeddings: Optional[Dict[str, Dict[str, Any]]] = None):
        """
        Save embeddings cache to disk.

        Args:
            embeddings: Optional embeddings dict to save. If None, saves current cache.
        """
        if embeddings is not None:
            self._cache = {
                "model": self.model_name,
                "dimension": self.model.get_sentence_embedding_dimension(),
                "notes": embeddings,
                "last_updated": datetime.now().isoformat(),
            }

        if self._cache is None:
            logger.warning("No cache to save")
            return

        try:
            # Save to temporary file first
            temp_file = self.cache_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)

            # Atomic replace
            temp_file.replace(self.cache_file)

            logger.info(f"Saved cache with {len(self._cache.get('notes', {}))} notes")

        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
            raise

    def get_cached_embedding(
        self, filepath: str, content_hash: str
    ) -> Optional[np.ndarray]:
        """
        Get cached embedding if available and valid.

        Args:
            filepath: Path to note
            content_hash: Current content hash

        Returns:
            Cached embedding or None if not available/invalid
        """
        cache = self.load_cache()
        notes_cache = cache.get("notes", {})

        if filepath not in notes_cache:
            return None

        cached = notes_cache[filepath]

        # Check if hash matches
        if cached.get("hash") != content_hash:
            logger.debug(f"Cache miss for {filepath}: content changed")
            return None

        embedding = cached.get("embedding")
        if embedding is None:
            return None

        return np.array(embedding)

    def update_embedding(
        self, filepath: str, content: str, force: bool = False
    ) -> np.ndarray:
        """
        Update embedding for a note (with caching).

        Args:
            filepath: Path to note
            content: Note content
            force: Force regeneration even if cached

        Returns:
            Embedding vector
        """
        content_hash = self._compute_content_hash(content)

        # Check cache
        if not force:
            cached = self.get_cached_embedding(filepath, content_hash)
            if cached is not None:
                logger.debug(f"Cache hit for {filepath}")
                return cached

        # Generate new embedding
        logger.debug(f"Generating new embedding for {filepath}")
        result = self.generate_note_embedding(filepath, content)

        # Update cache
        cache = self.load_cache()
        cache["notes"][filepath] = result
        self.save_cache()

        return np.array(result["embedding"])

    def clear_cache(self):
        """Clear the embeddings cache."""
        self._cache = {
            "model": self.model_name,
            "dimension": self.model.get_sentence_embedding_dimension(),
            "notes": {},
        }
        self.save_cache()
        logger.info("Cache cleared")

    def remove_note_from_cache(self, filepath: str):
        """Remove a specific note from cache."""
        cache = self.load_cache()
        if filepath in cache.get("notes", {}):
            del cache["notes"][filepath]
            self.save_cache()
            logger.debug(f"Removed {filepath} from cache")

    def get_dimension(self) -> int:
        """Get embedding dimension."""
        return self.model.get_sentence_embedding_dimension()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cache."""
        cache = self.load_cache()
        notes = cache.get("notes", {})

        return {
            "total_notes": len(notes),
            "model": cache.get("model"),
            "dimension": cache.get("dimension"),
            "cache_file": str(self.cache_file),
            "last_updated": cache.get("last_updated"),
        }
