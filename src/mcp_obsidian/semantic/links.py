"""
Link suggestion engine for discovering potential connections between notes.
"""

import logging
import re
from typing import Dict, List, Optional, Any, Set
from pathlib import Path

from .relationships import RelationshipAnalyzer

logger = logging.getLogger(__name__)


class LinkSuggestionEngine:
    """Suggest links between notes based on semantic similarity and mentions."""

    def __init__(self, relationship_analyzer: RelationshipAnalyzer):
        """
        Initialize link suggestion engine.

        Args:
            relationship_analyzer: RelationshipAnalyzer instance
        """
        self.relationship_analyzer = relationship_analyzer
        self.search_engine = relationship_analyzer.search_engine
        logger.info("LinkSuggestionEngine initialized")

    def suggest_links_for_note(
        self,
        filepath: str,
        content: str,
        max_suggestions: int = 10,
        min_similarity: float = 0.7,
        check_existing: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Suggest links to add to a note.

        Args:
            filepath: Path to the note
            content: Note content
            max_suggestions: Maximum number of suggestions
            min_similarity: Minimum similarity threshold
            check_existing: Don't suggest already linked notes

        Returns:
            List of link suggestions
        """
        logger.info(f"Generating link suggestions for {filepath}")

        # Extract existing links if needed
        existing_links = set()
        if check_existing:
            existing_links = self._extract_existing_links(content)

        # Find related notes
        related = self.relationship_analyzer.find_related_notes(
            filepath=filepath,
            content=content,
            top_k=max_suggestions * 2,  # Get more, filter later
            min_similarity=min_similarity,
        )

        # Filter out existing links
        if check_existing:
            related = [r for r in related if r["filepath"] not in existing_links]

        # Check for unlinked mentions
        mentions = self.find_unlinked_mentions(filepath, content)

        # Combine and prioritize suggestions
        suggestions = []

        # Add mentions first (higher priority)
        for mention in mentions[:max_suggestions]:
            suggestions.append(
                {
                    "target": mention["filepath"],
                    "title": mention["title"],
                    "reason": "unlinked_mention",
                    "similarity": mention.get("similarity", 0.0),
                    "context": mention.get("context", ""),
                    "mention_text": mention.get("mention_text", ""),
                }
            )

        # Add semantic suggestions
        for related_note in related:
            if len(suggestions) >= max_suggestions:
                break

            # Skip if already added as mention
            if any(s["target"] == related_note["filepath"] for s in suggestions):
                continue

            suggestions.append(
                {
                    "target": related_note["filepath"],
                    "title": related_note["title"],
                    "reason": "semantic_similarity",
                    "similarity": related_note["similarity"],
                    "context": self._get_suggestion_context(
                        related_note["filepath"], related_note["similarity"]
                    ),
                }
            )

        logger.info(f"Generated {len(suggestions)} link suggestions")
        return suggestions[:max_suggestions]

    def find_unlinked_mentions(
        self, filepath: str, content: str
    ) -> List[Dict[str, Any]]:
        """
        Find potential note mentions in text that aren't linked.

        Args:
            filepath: Path to the note
            content: Note content

        Returns:
            List of unlinked mentions
        """
        # Get all note titles from index
        metadata = self.search_engine._metadata
        if not metadata:
            return []

        all_paths = metadata.get("note_paths", [])
        note_titles = {Path(p).stem: p for p in all_paths if p != filepath}

        # Extract existing links
        existing_links = self._extract_existing_links(content)

        # Find mentions in text
        mentions = []

        # Remove frontmatter for mention detection
        _, body = self._extract_frontmatter(content)

        for title, note_path in note_titles.items():
            # Skip if already linked
            if note_path in existing_links:
                continue

            # Search for title mentions (case insensitive, whole word)
            pattern = r"\b" + re.escape(title) + r"\b"
            matches = list(re.finditer(pattern, body, re.IGNORECASE))

            if matches:
                # Get context around first mention
                first_match = matches[0]
                context = self._extract_context(body, first_match.start(), first_match.end())

                mentions.append(
                    {
                        "filepath": note_path,
                        "title": title,
                        "mention_text": first_match.group(),
                        "occurrences": len(matches),
                        "context": context,
                    }
                )

        # Sort by number of occurrences
        mentions.sort(key=lambda x: x["occurrences"], reverse=True)

        logger.debug(f"Found {len(mentions)} unlinked mentions in {filepath}")
        return mentions

    def suggest_bidirectional_links(
        self, filepath: str, content: str, min_similarity: float = 0.75
    ) -> List[Dict[str, Any]]:
        """
        Suggest bidirectional links (where both notes should link to each other).

        Args:
            filepath: Path to the note
            content: Note content
            min_similarity: Minimum similarity for bidirectional link

        Returns:
            List of bidirectional link suggestions
        """
        # Find highly related notes
        related = self.relationship_analyzer.find_related_notes(
            filepath=filepath,
            content=content,
            top_k=20,
            min_similarity=min_similarity,
        )

        bidirectional = []

        for note in related:
            bidirectional.append(
                {
                    "filepath": note["filepath"],
                    "title": note["title"],
                    "similarity": note["similarity"],
                    "suggestion": f"Add bidirectional link between {Path(filepath).stem} ↔ {note['title']}",
                }
            )

        return bidirectional

    def _extract_existing_links(self, content: str) -> Set[str]:
        """
        Extract existing wiki-style links from content.

        Args:
            content: Note content

        Returns:
            Set of linked filepaths
        """
        links = set()

        # Match [[link]] and [[link|alias]]
        pattern = r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]"

        for match in re.finditer(pattern, content):
            link_text = match.group(1).strip()

            # Convert link text to filepath
            # Simple heuristic: assume link is filename without extension
            # In a real implementation, would need to resolve link properly
            links.add(link_text)

        return links

    def _extract_frontmatter(self, content: str) -> tuple:
        """Extract frontmatter and body from content."""
        if not content.startswith("---"):
            return {}, content

        try:
            parts = content.split("---", 2)
            if len(parts) >= 3:
                import yaml

                frontmatter = yaml.safe_load(parts[1]) or {}
                body = parts[2].strip()
                return frontmatter, body
        except Exception:
            pass

        return {}, content

    def _extract_context(
        self, text: str, start: int, end: int, context_length: int = 100
    ) -> str:
        """
        Extract context around a text match.

        Args:
            text: Full text
            start: Match start position
            end: Match end position
            context_length: Characters to include on each side

        Returns:
            Context string
        """
        context_start = max(0, start - context_length)
        context_end = min(len(text), end + context_length)

        context = text[context_start:context_end].strip()

        # Add ellipsis if truncated
        if context_start > 0:
            context = "..." + context
        if context_end < len(text):
            context = context + "..."

        return context

    def _get_suggestion_context(self, filepath: str, similarity: float) -> str:
        """
        Generate context for a link suggestion.

        Args:
            filepath: Target note path
            similarity: Similarity score

        Returns:
            Context description
        """
        folder = Path(filepath).parent.name

        if similarity > 0.9:
            return f"Very closely related note in {folder}"
        elif similarity > 0.8:
            return f"Closely related note in {folder}"
        elif similarity > 0.7:
            return f"Related note in {folder}"
        else:
            return f"Potentially related note in {folder}"

    def analyze_vault_connectivity(
        self, min_similarity: float = 0.7
    ) -> Dict[str, Any]:
        """
        Analyze overall vault connectivity and suggest improvements.

        Args:
            min_similarity: Similarity threshold

        Returns:
            Analysis with improvement suggestions
        """
        # Get isolated notes
        isolated = self.relationship_analyzer.find_isolated_notes(
            min_similarity=min_similarity
        )

        # Get vault graph
        graph = self.relationship_analyzer.get_vault_graph(min_similarity=min_similarity)

        # Calculate statistics
        total_notes = len(graph)
        total_connections = sum(len(conns) for conns in graph.values())
        avg_connections = total_connections / total_notes if total_notes else 0

        # Find notes with most potential for new links
        improvement_candidates = []

        for note_path in isolated[:10]:  # Top 10 isolated notes
            filepath = note_path["filepath"]

            # Get cache to access content
            cache = self.search_engine.embeddings_manager.load_cache()
            note_data = cache.get("notes", {}).get(filepath)

            if note_data:
                # Note: we don't have content here, would need to fetch
                # For now, just record the filepath
                improvement_candidates.append(
                    {
                        "filepath": filepath,
                        "current_connections": note_path["num_connections"],
                        "recommendation": "Find related notes and add links",
                    }
                )

        return {
            "total_notes": total_notes,
            "total_connections": total_connections,
            "avg_connections_per_note": round(avg_connections, 2),
            "isolated_notes": len(isolated),
            "improvement_candidates": improvement_candidates,
            "recommendations": [
                "Add links to isolated notes to improve discoverability",
                "Consider bidirectional links for closely related notes",
                "Review unlinked mentions and convert to links",
            ],
        }
