"""
Relationship analysis between notes using semantic similarity.
"""

import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from pathlib import Path
import numpy as np

from .search import SemanticSearchEngine

logger = logging.getLogger(__name__)


class RelationshipAnalyzer:
    """Analyze semantic relationships between notes."""

    def __init__(self, search_engine: SemanticSearchEngine):
        """
        Initialize relationship analyzer.

        Args:
            search_engine: SemanticSearchEngine instance
        """
        self.search_engine = search_engine
        logger.info("RelationshipAnalyzer initialized")

    def find_related_notes(
        self,
        filepath: str,
        content: str,
        top_k: int = 10,
        min_similarity: float = 0.6,
    ) -> List[Dict[str, Any]]:
        """
        Find notes related to a given note.

        Args:
            filepath: Path to the reference note
            content: Content of the reference note
            top_k: Number of related notes to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of related notes with similarity scores
        """
        return self.search_engine.search_by_note(
            filepath=filepath,
            content=content,
            top_k=top_k,
            min_similarity=min_similarity,
        )

    def analyze_note_clusters(
        self,
        min_similarity: float = 0.7,
        folder: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find clusters of semantically related notes.

        Args:
            min_similarity: Minimum similarity to consider notes related
            folder: Optional folder to limit analysis

        Returns:
            List of clusters with their notes
        """
        metadata = self.search_engine._metadata
        if not metadata:
            logger.warning("No index metadata available")
            return []

        # Get filepaths to analyze
        all_paths = metadata.get("note_paths", [])

        if folder:
            all_paths = [p for p in all_paths if p.startswith(folder)]

        if not all_paths:
            return []

        logger.info(f"Analyzing clusters for {len(all_paths)} notes")

        # Get similarity matrix
        similarity_matrix = self.search_engine.get_similarity_matrix(all_paths)

        if similarity_matrix.size == 0:
            return []

        # Find connected components (clusters)
        adjacency = similarity_matrix >= min_similarity
        clusters = self._find_connected_components(adjacency)

        # Build cluster information
        cluster_info = []
        for cluster_indices in clusters:
            if len(cluster_indices) < 2:  # Skip singleton clusters
                continue

            cluster_paths = [all_paths[i] for i in cluster_indices]

            # Calculate average similarity within cluster
            cluster_similarities = []
            for i in range(len(cluster_indices)):
                for j in range(i + 1, len(cluster_indices)):
                    idx_i, idx_j = cluster_indices[i], cluster_indices[j]
                    cluster_similarities.append(similarity_matrix[idx_i, idx_j])

            avg_similarity = (
                np.mean(cluster_similarities) if cluster_similarities else 0.0
            )

            cluster_info.append(
                {
                    "size": len(cluster_paths),
                    "notes": cluster_paths,
                    "avg_similarity": float(avg_similarity),
                    "theme": self._infer_cluster_theme(cluster_paths),
                }
            )

        # Sort by size
        cluster_info.sort(key=lambda x: x["size"], reverse=True)

        logger.info(f"Found {len(cluster_info)} clusters")
        return cluster_info

    def _find_connected_components(self, adjacency: np.ndarray) -> List[List[int]]:
        """
        Find connected components in an adjacency matrix.

        Args:
            adjacency: Boolean adjacency matrix

        Returns:
            List of lists containing node indices for each component
        """
        n = len(adjacency)
        visited = set()
        components = []

        def dfs(node: int, component: List[int]):
            """Depth-first search to find component."""
            visited.add(node)
            component.append(node)

            for neighbor in range(n):
                if adjacency[node, neighbor] and neighbor not in visited:
                    dfs(neighbor, component)

        for node in range(n):
            if node not in visited:
                component = []
                dfs(node, component)
                components.append(component)

        return components

    def _infer_cluster_theme(self, filepaths: List[str]) -> str:
        """
        Infer a theme/topic for a cluster of notes.

        Args:
            filepaths: List of note paths in the cluster

        Returns:
            Inferred theme description
        """
        # Simple heuristic: use common folder and note titles
        folders = [Path(fp).parent.name for fp in filepaths]

        # Find most common folder
        from collections import Counter

        folder_counts = Counter(folders)
        if folder_counts:
            common_folder = folder_counts.most_common(1)[0][0]
            return f"Notes in {common_folder}"

        return "Related notes"

    def get_vault_graph(
        self, min_similarity: float = 0.7, folder: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """
        Build a graph of note relationships.

        Args:
            min_similarity: Minimum similarity for edge
            folder: Optional folder filter

        Returns:
            Dict mapping filepath to list of related filepaths
        """
        metadata = self.search_engine._metadata
        if not metadata:
            return {}

        all_paths = metadata.get("note_paths", [])

        if folder:
            all_paths = [p for p in all_paths if p.startswith(folder)]

        if not all_paths:
            return {}

        # Get similarity matrix
        similarity_matrix = self.search_engine.get_similarity_matrix(all_paths)

        if similarity_matrix.size == 0:
            return {}

        # Build adjacency list
        graph = {}
        for i, filepath in enumerate(all_paths):
            related = []
            for j, other_path in enumerate(all_paths):
                if i != j and similarity_matrix[i, j] >= min_similarity:
                    related.append(other_path)

            graph[filepath] = related

        return graph

    def find_bridge_notes(
        self, min_similarity: float = 0.7, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find notes that bridge different clusters.

        Bridge notes are notes that connect otherwise disconnected groups.

        Args:
            min_similarity: Minimum similarity threshold
            folder: Optional folder filter

        Returns:
            List of bridge notes with their connections
        """
        # First find clusters
        clusters = self.analyze_note_clusters(
            min_similarity=min_similarity, folder=folder
        )

        if len(clusters) < 2:
            return []

        # Build cluster membership map
        note_to_cluster = {}
        for i, cluster in enumerate(clusters):
            for note in cluster["notes"]:
                note_to_cluster[note] = i

        # Get graph
        graph = self.get_vault_graph(min_similarity=min_similarity, folder=folder)

        # Find bridge notes
        bridges = []
        for note, connections in graph.items():
            if not connections:
                continue

            # Check if this note connects different clusters
            cluster_id = note_to_cluster.get(note)
            if cluster_id is None:
                continue

            connected_clusters = set()
            for connected_note in connections:
                other_cluster = note_to_cluster.get(connected_note)
                if other_cluster is not None and other_cluster != cluster_id:
                    connected_clusters.add(other_cluster)

            if len(connected_clusters) >= 2:
                bridges.append(
                    {
                        "filepath": note,
                        "title": Path(note).stem,
                        "home_cluster": cluster_id,
                        "bridges_to": list(connected_clusters),
                        "num_connections": len(connections),
                    }
                )

        # Sort by number of clusters bridged
        bridges.sort(key=lambda x: len(x["bridges_to"]), reverse=True)

        logger.info(f"Found {len(bridges)} bridge notes")
        return bridges

    def find_isolated_notes(
        self, min_similarity: float = 0.6, folder: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find notes that have few or no semantic connections.

        Args:
            min_similarity: Similarity threshold for connections
            folder: Optional folder filter

        Returns:
            List of isolated notes
        """
        graph = self.get_vault_graph(min_similarity=min_similarity, folder=folder)

        isolated = []
        for filepath, connections in graph.items():
            if len(connections) <= 1:  # 0 or 1 connection
                isolated.append(
                    {
                        "filepath": filepath,
                        "title": Path(filepath).stem,
                        "num_connections": len(connections),
                        "connected_to": connections,
                    }
                )

        # Sort by number of connections (ascending)
        isolated.sort(key=lambda x: x["num_connections"])

        logger.info(f"Found {len(isolated)} isolated notes")
        return isolated

    def analyze_folder_relationships(
        self, folder: str, min_similarity: float = 0.7
    ) -> Dict[str, Any]:
        """
        Comprehensive relationship analysis for a folder.

        Args:
            folder: Folder path to analyze
            min_similarity: Similarity threshold

        Returns:
            Dict with comprehensive analysis
        """
        metadata = self.search_engine._metadata
        if not metadata:
            return {}

        # Get notes in folder
        all_paths = metadata.get("note_paths", [])
        folder_paths = [p for p in all_paths if p.startswith(folder)]

        if not folder_paths:
            return {"error": f"No notes found in folder: {folder}"}

        # Run various analyses
        clusters = self.analyze_note_clusters(
            min_similarity=min_similarity, folder=folder
        )

        bridges = self.find_bridge_notes(min_similarity=min_similarity, folder=folder)

        isolated = self.find_isolated_notes(min_similarity=min_similarity, folder=folder)

        graph = self.get_vault_graph(min_similarity=min_similarity, folder=folder)

        # Calculate statistics
        total_connections = sum(len(conns) for conns in graph.values())
        avg_connections = total_connections / len(graph) if graph else 0

        return {
            "folder": folder,
            "total_notes": len(folder_paths),
            "clusters": {
                "count": len(clusters),
                "largest": clusters[0] if clusters else None,
            },
            "bridge_notes": len(bridges),
            "isolated_notes": len(isolated),
            "connectivity": {
                "total_connections": total_connections,
                "avg_connections_per_note": round(avg_connections, 2),
            },
            "min_similarity": min_similarity,
        }

    def suggest_connections_for_note(
        self,
        filepath: str,
        content: str,
        max_suggestions: int = 5,
        min_similarity: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        Suggest potential connections for a note.

        Similar to find_related_notes but with additional context.

        Args:
            filepath: Path to note
            content: Note content
            max_suggestions: Number of suggestions
            min_similarity: Minimum similarity

        Returns:
            List of connection suggestions with reasons
        """
        related = self.find_related_notes(
            filepath=filepath,
            content=content,
            top_k=max_suggestions,
            min_similarity=min_similarity,
        )

        # Add suggestion reasons
        for note in related:
            note["reason"] = self._determine_connection_reason(
                filepath, note["filepath"], note["similarity"]
            )

        return related

    def _determine_connection_reason(
        self, source: str, target: str, similarity: float
    ) -> str:
        """
        Determine why two notes should be connected.

        Args:
            source: Source note path
            target: Target note path
            similarity: Similarity score

        Returns:
            Human-readable reason
        """
        source_folder = Path(source).parent.name
        target_folder = Path(target).parent.name

        if source_folder == target_folder:
            return f"Related note in same folder ({source_folder})"

        if similarity > 0.85:
            return "Highly similar content"
        elif similarity > 0.75:
            return "Similar topics"
        else:
            return "Potentially related"
