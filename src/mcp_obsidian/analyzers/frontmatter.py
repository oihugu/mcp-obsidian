import logging
logger = logging.getLogger(__name__)
"""
Frontmatter analyzer.

Analyzes frontmatter patterns across notes to infer schemas
and suggest improvements.
"""

from typing import Dict, List, Optional, Any, Set
from collections import defaultdict, Counter

from ..obsidian import Obsidian


class FrontmatterAnalyzer:
    """Analyzes frontmatter patterns and suggests schemas."""

    def __init__(self, obsidian_client: Obsidian):
        """
        Initialize frontmatter analyzer.

        Args:
            obsidian_client: Obsidian API client
        """
        self.client = obsidian_client

    def analyze_frontmatter_in_folder(
        self,
        folder_path: str,
        sample_size: int = 20
    ) -> Dict[str, Any]:
        """
        Analyze frontmatter patterns in a specific folder.

        Args:
            folder_path: Path to folder to analyze
            sample_size: Number of files to sample

        Returns:
            Dictionary with frontmatter analysis
        """
        try:
            # Get list of markdown files in folder
            result = self.client.list_files_in_directory(folder_path)
            files = [
                f for f in result.get("files", [])
                if f.endswith(".md") and not f.endswith("/")
            ]

            if not files:
                return {"error": "No markdown files found in folder"}

            # Sample files
            sample_files = files[:min(sample_size, len(files))]
            frontmatters = []

            for filename in sample_files:
                filepath = f"{folder_path}/{filename}"
                note_data = self._get_note_metadata(filepath)
                if note_data:
                    frontmatter = note_data.get("frontmatter", {})
                    if frontmatter:  # Only include notes with frontmatter
                        frontmatters.append({
                            "file": filename,
                            "frontmatter": frontmatter
                        })

            if not frontmatters:
                return {
                    "total_files": len(files),
                    "files_with_frontmatter": 0,
                    "schema": {},
                    "suggestions": ["Consider adding frontmatter to organize note metadata"]
                }

            # Analyze collected frontmatter
            schema = self._build_schema(frontmatters)
            suggestions = self._generate_suggestions(schema, frontmatters)
            common_fields = self._find_common_fields(frontmatters)
            missing_fields = self._find_missing_fields(frontmatters, common_fields)

            return {
                "total_files": len(files),
                "files_sampled": len(sample_files),
                "files_with_frontmatter": len(frontmatters),
                "schema": schema,
                "common_fields": common_fields,
                "missing_fields": missing_fields,
                "suggestions": suggestions
            }

        except Exception as e:
            return {"error": str(e)}

    def suggest_frontmatter_for_note(
        self,
        note_path: str,
        similar_notes_folder: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest frontmatter for a specific note based on similar notes.

        Args:
            note_path: Path to the note
            similar_notes_folder: Folder containing similar notes (for schema reference)

        Returns:
            Dictionary with suggestions
        """
        try:
            # Get current note
            note_data = self._get_note_metadata(note_path)
            if not note_data:
                return {"error": "Could not read note"}

            current_frontmatter = note_data.get("frontmatter", {})

            # Determine folder if not specified
            if similar_notes_folder is None:
                # Use parent folder of note
                similar_notes_folder = "/".join(note_path.split("/")[:-1])

            # Analyze similar notes
            folder_analysis = self.analyze_frontmatter_in_folder(similar_notes_folder)

            if "error" in folder_analysis:
                return folder_analysis

            schema = folder_analysis.get("schema", {})
            common_fields = folder_analysis.get("common_fields", [])

            # Generate suggestions for this specific note
            suggestions = []
            missing_recommended_fields = []

            for field in common_fields:
                if field not in current_frontmatter:
                    field_info = schema.get(field, {})
                    missing_recommended_fields.append({
                        "field": field,
                        "type": field_info.get("type", "string"),
                        "frequency": field_info.get("frequency", 0),
                        "example": field_info.get("example_value")
                    })

            if missing_recommended_fields:
                suggestions.append({
                    "type": "add_fields",
                    "message": "Consider adding these common fields",
                    "fields": missing_recommended_fields
                })

            # Check for fields with wrong types
            type_mismatches = []
            for field, value in current_frontmatter.items():
                if field in schema:
                    expected_type = schema[field].get("type")
                    actual_type = type(value).__name__
                    if expected_type and expected_type != actual_type:
                        type_mismatches.append({
                            "field": field,
                            "current_type": actual_type,
                            "expected_type": expected_type,
                            "current_value": value
                        })

            if type_mismatches:
                suggestions.append({
                    "type": "type_mismatch",
                    "message": "These fields have unexpected types",
                    "fields": type_mismatches
                })

            return {
                "note_path": note_path,
                "current_frontmatter": current_frontmatter,
                "reference_schema": schema,
                "suggestions": suggestions
            }

        except Exception as e:
            return {"error": str(e)}

    def _get_note_metadata(self, filepath: str) -> Optional[Dict[str, Any]]:
        """Get note metadata including frontmatter."""
        try:
            return self.client.get_file_contents(filepath, return_json=True)
        except Exception as e:
            logger.debug(f"Error getting note metadata for {filepath}: {e}")
            return None

    def _build_schema(self, frontmatters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build schema from multiple frontmatter examples.

        Args:
            frontmatters: List of dicts containing file and frontmatter

        Returns:
            Schema dictionary
        """
        field_counter = Counter()
        field_types = defaultdict(Counter)
        field_examples = defaultdict(list)

        total_notes = len(frontmatters)

        for item in frontmatters:
            fm = item["frontmatter"]
            for key, value in fm.items():
                field_counter[key] += 1

                # Track type
                value_type = self._get_value_type(value)
                field_types[key][value_type] += 1

                # Save example value
                if len(field_examples[key]) < 3:  # Keep up to 3 examples
                    field_examples[key].append(value)

        # Build schema
        schema = {}
        for field, count in field_counter.items():
            frequency = count / total_notes
            most_common_type = field_types[field].most_common(1)[0][0]

            schema[field] = {
                "type": most_common_type,
                "frequency": frequency,
                "present_in": count,
                "total": total_notes,
                "example_value": field_examples[field][0] if field_examples[field] else None
            }

        return schema

    def _get_value_type(self, value: Any) -> str:
        """Get semantic type of value."""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "number"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        else:
            return "string"

    def _find_common_fields(
        self,
        frontmatters: List[Dict[str, Any]],
        threshold: float = 0.5
    ) -> List[str]:
        """
        Find fields that appear in at least threshold% of notes.

        Args:
            frontmatters: List of frontmatter dicts
            threshold: Minimum frequency (0-1) to be considered common

        Returns:
            List of common field names
        """
        field_counter = Counter()
        total = len(frontmatters)

        for item in frontmatters:
            for key in item["frontmatter"].keys():
                field_counter[key] += 1

        common = [
            field for field, count in field_counter.items()
            if (count / total) >= threshold
        ]

        return sorted(common)

    def _find_missing_fields(
        self,
        frontmatters: List[Dict[str, Any]],
        common_fields: List[str]
    ) -> Dict[str, List[str]]:
        """
        Find which files are missing common fields.

        Args:
            frontmatters: List of frontmatter dicts
            common_fields: List of common field names

        Returns:
            Dict mapping field names to list of files missing that field
        """
        missing = defaultdict(list)

        for item in frontmatters:
            filename = item["file"]
            fm = item["frontmatter"]

            for field in common_fields:
                if field not in fm:
                    missing[field].append(filename)

        return dict(missing)

    def _generate_suggestions(
        self,
        schema: Dict[str, Any],
        frontmatters: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Generate improvement suggestions based on schema analysis.

        Args:
            schema: Analyzed schema
            frontmatters: List of frontmatter examples

        Returns:
            List of suggestion strings
        """
        suggestions = []

        # Check for low-frequency fields that might be typos or inconsistent
        rare_fields = [
            field for field, info in schema.items()
            if info["frequency"] < 0.2  # Appears in less than 20% of notes
        ]

        if rare_fields:
            suggestions.append(
                f"These fields are rarely used and might be inconsistent: {', '.join(rare_fields)}"
            )

        # Check for fields that could be standardized
        if "tags" in schema or "tag" in schema:
            if "tags" in schema and "tag" in schema:
                suggestions.append(
                    "Both 'tag' and 'tags' fields exist. Consider standardizing to 'tags' (array)."
                )

        # Suggest date fields if none exist
        date_fields = [f for f in schema.keys() if "date" in f.lower()]
        if not date_fields:
            suggestions.append(
                "Consider adding a 'date' or 'created' field to track note creation."
            )

        # Check for fields with type inconsistencies
        for field, info in schema.items():
            types = list(info.get("type", ""))
            if len(types) > 1:
                suggestions.append(
                    f"Field '{field}' has inconsistent types across notes: {', '.join(types)}"
                )

        return suggestions
