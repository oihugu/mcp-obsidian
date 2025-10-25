"""
Semantic search engine using FAISS for similarity search.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

from .embeddings import EmbeddingsManager

logger = logging.getLogger(__name__)


class SemanticSearchEngine:
    """Semantic search engine using FAISS for vector similarity."""

    def __init__(
        self,
        embeddings_manager: EmbeddingsManager,
        cache_dir: str = ".mcp-obsidian",
    ):
        """
        Initialize search engine.

        Args:
            embeddings_manager: EmbeddingsManager instance
            cache_dir: Directory for caching index
        """
        self.embeddings_manager = embeddings_manager
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        self.index_file = self.cache_dir / "faiss-index.bin"
        self.metadata_file = self.cache_dir / "index-metadata.json"

        self._index = None
        self._metadata = None

        logger.info("SemanticSearchEngine initialized")

    @property
    def index(self):
        """Lazy load FAISS index."""
        if self._index is None:
            self._load_or_create_index()
        return self._index

    def _load_or_create_index(self):
        """Load existing index or create new one."""
        try:
            import faiss
        except ImportError:
            raise ImportError(
                "faiss-cpu not installed. Install with: pip install faiss-cpu"
            )

        if self.index_file.exists() and self.metadata_file.exists():
            try:
                # Load index
                self._index = faiss.read_index(str(self.index_file))

                # Load metadata
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    self._metadata = json.load(f)

                logger.info(
                    f"Loaded FAISS index with {self._metadata.get('total_notes', 0)} notes"
                )
                return
            except Exception as e:
                logger.warning(f"Failed to load index: {e}. Creating new index.")

        # Create new index
        dimension = self.embeddings_manager.get_dimension()
        self._index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
        self._metadata = {
            "total_notes": 0,
            "note_paths": [],
            "dimension": dimension,
        }

        logger.info(f"Created new FAISS index with dimension {dimension}")

    def build_index(
        self, notes: List[Dict[str, str]], force: bool = False
    ) -> Dict[str, Any]:
        """
        Build or rebuild the search index.

        Args:
            notes: List of dicts with 'filepath' and 'content'
            force: Force rebuild even if embeddings are cached

        Returns:
            Dict with build statistics
        """
        import faiss

        logger.info(f"Building index for {len(notes)} notes (force={force})")

        # Generate embeddings
        embeddings_data = self.embeddings_manager.batch_generate_embeddings(
            notes, show_progress=True
        )

        # Filter out failed embeddings
        valid_embeddings = [
            e for e in embeddings_data if e.get("embedding") is not None
        ]

        if not valid_embeddings:
            logger.error("No valid embeddings generated")
            return {"success": False, "error": "No valid embeddings"}

        # Create embedding matrix
        embeddings_matrix = np.array(
            [e["embedding"] for e in valid_embeddings], dtype=np.float32
        )

        # Normalize for cosine similarity (FAISS uses inner product)
        faiss.normalize_L2(embeddings_matrix)

        # Create new index
        dimension = embeddings_matrix.shape[1]
        self._index = faiss.IndexFlatIP(dimension)

        # Add vectors
        self._index.add(embeddings_matrix)

        # Store metadata
        self._metadata = {
            "total_notes": len(valid_embeddings),
            "note_paths": [e["filepath"] for e in valid_embeddings],
            "dimension": dimension,
            "model": self.embeddings_manager.model_name,
            "last_rebuild": embeddings_data[0].get("timestamp")
            if embeddings_data
            else None,
        }

        # Save index and metadata
        self._save_index()

        logger.info(f"Index built successfully with {len(valid_embeddings)} notes")

        return {
            "success": True,
            "total_notes": len(valid_embeddings),
            "failed": len(embeddings_data) - len(valid_embeddings),
        }

    def _save_index(self):
        """Save FAISS index and metadata to disk."""
        try:
            import faiss

            # Save index
            faiss.write_index(self._index, str(self.index_file))

            # Save metadata
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(self._metadata, f, indent=2)

            logger.debug("Index saved successfully")

        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            raise

    def search(
        self,
        query: str,
        top_k: int = 10,
        min_similarity: float = 0.0,
        folder: Optional[str] = None,
        include_content: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Search for notes by semantic similarity to query.

        Args:
            query: Search query
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold (0-1)
            folder: Optional folder filter
            include_content: Include note content in results

        Returns:
            List of search results with similarity scores
        """
        if self._metadata is None or self._metadata.get("total_notes", 0) == 0:
            logger.warning("Index is empty. Build index first.")
            return []

        # Generate query embedding
        query_embedding = self.embeddings_manager.generate_embedding(query)
        query_embedding = query_embedding.reshape(1, -1).astype(np.float32)

        # Normalize for cosine similarity
        import faiss

        faiss.normalize_L2(query_embedding)

        # Search
        # Request more results if we need to filter by folder
        search_k = top_k * 3 if folder else top_k
        similarities, indices = self._index.search(query_embedding, search_k)

        # Build results
        results = []
        for idx, similarity in zip(indices[0], similarities[0]):
            if idx == -1:  # FAISS returns -1 for unfound results
                continue

            if similarity < min_similarity:
                continue

            filepath = self._metadata["note_paths"][idx]

            # Apply folder filter
            if folder and not filepath.startswith(folder):
                continue

            result = {
                "filepath": filepath,
                "similarity": float(similarity),
                "title": Path(filepath).stem,
            }

            # Add snippet if requested
            if include_content:
                result["snippet"] = self._generate_snippet(filepath, query)

            results.append(result)

            if len(results) >= top_k:
                break

        return results

    def search_by_note(
        self,
        filepath: str,
        content: str,
        top_k: int = 10,
        min_similarity: float = 0.6,
    ) -> List[Dict[str, Any]]:
        """
        Find notes similar to a given note.

        Args:
            filepath: Path to the reference note
            content: Content of the reference note
            top_k: Number of results
            min_similarity: Minimum similarity threshold

        Returns:
            List of similar notes
        """
        # Generate embedding for the note
        embedding = self.embeddings_manager.update_embedding(filepath, content)

        # Search using this embedding
        return self.search_by_embedding(
            embedding, top_k=top_k + 1, min_similarity=min_similarity, exclude=filepath
        )

    def search_by_embedding(
        self,
        embedding: np.ndarray,
        top_k: int = 10,
        min_similarity: float = 0.0,
        exclude: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search by embedding vector.

        Args:
            embedding: Embedding vector
            top_k: Number of results
            min_similarity: Minimum similarity threshold
            exclude: Optional filepath to exclude from results

        Returns:
            List of search results
        """
        if self._metadata is None or self._metadata.get("total_notes", 0) == 0:
            return []

        # Prepare embedding
        query_embedding = embedding.reshape(1, -1).astype(np.float32)

        # Normalize
        import faiss

        faiss.normalize_L2(query_embedding)

        # Search (request extra if we're excluding)
        search_k = top_k + 1 if exclude else top_k
        similarities, indices = self._index.search(query_embedding, search_k)

        # Build results
        results = []
        for idx, similarity in zip(indices[0], similarities[0]):
            if idx == -1:
                continue

            if similarity < min_similarity:
                continue

            filepath = self._metadata["note_paths"][idx]

            # Skip excluded note
            if exclude and filepath == exclude:
                continue

            results.append(
                {
                    "filepath": filepath,
                    "similarity": float(similarity),
                    "title": Path(filepath).stem,
                }
            )

            if len(results) >= top_k:
                break

        return results

    def _generate_snippet(
        self, filepath: str, query: str, max_length: int = 200
    ) -> str:
        """
        Generate a snippet from note content relevant to query.

        Args:
            filepath: Path to note
            query: Search query
            max_length: Maximum snippet length

        Returns:
            Relevant snippet from note
        """
        try:
            # Get note from cache
            cache = self.embeddings_manager.load_cache()
            note_data = cache.get("notes", {}).get(filepath)

            if not note_data:
                return ""

            # For now, just return truncated content
            # TODO: Implement smarter snippet extraction based on query
            title = note_data.get("title", "")
            snippet = f"{title}..."

            return snippet[:max_length]

        except Exception as e:
            logger.error(f"Failed to generate snippet for {filepath}: {e}")
            return ""

    def get_all_embeddings(self) -> Dict[str, np.ndarray]:
        """
        Get all embeddings from the index.

        Returns:
            Dict mapping filepath to embedding
        """
        if self._metadata is None:
            return {}

        cache = self.embeddings_manager.load_cache()
        notes_cache = cache.get("notes", {})

        embeddings = {}
        for filepath in self._metadata.get("note_paths", []):
            if filepath in notes_cache:
                embedding = notes_cache[filepath].get("embedding")
                if embedding:
                    embeddings[filepath] = np.array(embedding)

        return embeddings

    def get_similarity_matrix(self, filepaths: Optional[List[str]] = None) -> np.ndarray:
        """
        Compute pairwise similarity matrix for notes.

        Args:
            filepaths: Optional list of filepaths. If None, uses all notes in index.

        Returns:
            Similarity matrix (n x n)
        """
        if filepaths is None:
            filepaths = self._metadata.get("note_paths", [])

        if not filepaths:
            return np.array([])

        # Get embeddings
        embeddings_dict = self.get_all_embeddings()
        embeddings_list = [
            embeddings_dict[fp] for fp in filepaths if fp in embeddings_dict
        ]

        if not embeddings_list:
            return np.array([])

        embeddings_matrix = np.array(embeddings_list, dtype=np.float32)

        # Normalize
        import faiss

        faiss.normalize_L2(embeddings_matrix)

        # Compute cosine similarity (inner product of normalized vectors)
        similarity_matrix = np.dot(embeddings_matrix, embeddings_matrix.T)

        return similarity_matrix

    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the search index."""
        if self._metadata is None:
            return {
                "indexed": False,
                "total_notes": 0,
            }

        return {
            "indexed": True,
            "total_notes": self._metadata.get("total_notes", 0),
            "dimension": self._metadata.get("dimension"),
            "model": self._metadata.get("model"),
            "last_rebuild": self._metadata.get("last_rebuild"),
            "index_file": str(self.index_file),
        }
