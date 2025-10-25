"""
Vault structure analyzer.

Analyzes the folder structure of an Obsidian vault to detect
patterns and organizational schemes.
"""

import re
from typing import Dict, List, Optional, Any
from collections import defaultdict, Counter
from pathlib import Path

from ..obsidian import Obsidian


class VaultStructureAnalyzer:
    """Analyzes vault structure to detect organizational patterns."""

    def __init__(self, obsidian_client: Obsidian):
        """
        Initialize structure analyzer.

        Args:
            obsidian_client: Obsidian API client
        """
        self.client = obsidian_client

    def analyze_vault_structure(self) -> Dict[str, Any]:
        """
        Analyze complete vault structure.

        Returns:
            Dictionary containing detected patterns and structure info
        """
        # Get root folders
        root_folders = self._get_root_folders()

        # Analyze each major component
        daily_notes_info = self._analyze_daily_notes(root_folders)
        people_info = self._analyze_people_folder(root_folders)
        projects_info = self._analyze_projects_structure(root_folders)

        # Detect other organizational patterns
        folder_hierarchy = self._build_folder_hierarchy()

        return {
            "root_folders": root_folders,
            "daily_notes": daily_notes_info,
            "people": people_info,
            "projects": projects_info,
            "folder_hierarchy": folder_hierarchy,
            "statistics": self._calculate_statistics()
        }

    def _get_root_folders(self) -> List[str]:
        """Get list of root folders in the vault."""
        try:
            result = self.client.list_files_in_vault()
            folders = []
            for item in result.get("files", []):
                if item.endswith("/"):
                    folders.append(item.rstrip("/"))
            return sorted(folders)
        except Exception as e:
            print(f"Error getting root folders: {e}")
            return []

    def _analyze_daily_notes(self, root_folders: List[str]) -> Dict[str, Any]:
        """
        Analyze daily notes structure.

        Args:
            root_folders: List of root folder names

        Returns:
            Dictionary with daily notes information
        """
        # Look for common daily notes folder names
        daily_folders = [
            f for f in root_folders
            if any(keyword in f.lower() for keyword in ["daily", "journal", "diário", "diario"])
        ]

        if not daily_folders:
            return {"found": False}

        # Analyze the most likely daily notes folder
        daily_folder = daily_folders[0]

        try:
            # Get structure within daily notes folder
            structure = self._explore_folder_structure(daily_folder, max_depth=3)

            # Detect pattern (year-based, month-based, etc)
            pattern = self._detect_daily_notes_pattern(structure)

            # Try to get a sample daily note to analyze its structure
            sample_note = self._find_sample_daily_note(structure)
            sections = []
            frontmatter_fields = []

            if sample_note:
                note_data = self._get_note_metadata(sample_note)
                if note_data:
                    sections = self._extract_sections(note_data.get("content", ""))
                    frontmatter_fields = list(note_data.get("frontmatter", {}).keys())

            return {
                "found": True,
                "folder": daily_folder,
                "pattern": pattern,
                "structure": structure,
                "sample_sections": sections,
                "frontmatter_fields": frontmatter_fields
            }
        except Exception as e:
            print(f"Error analyzing daily notes: {e}")
            return {"found": True, "folder": daily_folder, "error": str(e)}

    def _analyze_people_folder(self, root_folders: List[str]) -> Dict[str, Any]:
        """
        Analyze people folder structure.

        Args:
            root_folders: List of root folder names

        Returns:
            Dictionary with people folder information
        """
        # Look for people-related folders
        people_folders = [
            f for f in root_folders
            if any(keyword in f.lower() for keyword in ["people", "person", "contact", "pessoas"])
        ]

        if not people_folders:
            return {"found": False}

        people_folder = people_folders[0]

        try:
            # Get list of people notes
            result = self.client.list_files_in_directory(people_folder)
            people_files = [
                f for f in result.get("files", [])
                if f.endswith(".md") and not f.endswith("/")
            ]

            # Sample a few to analyze frontmatter
            sample_schemas = []
            for i, person_file in enumerate(people_files[:5]):  # Sample 5 notes
                file_path = f"{people_folder}/{person_file}"
                note_data = self._get_note_metadata(file_path)
                if note_data and note_data.get("frontmatter"):
                    sample_schemas.append(note_data["frontmatter"])

            # Infer common schema
            common_schema = self._infer_common_schema(sample_schemas)

            return {
                "found": True,
                "folder": people_folder,
                "total_people": len(people_files),
                "sample_people": people_files[:10],
                "common_schema": common_schema
            }
        except Exception as e:
            print(f"Error analyzing people folder: {e}")
            return {"found": True, "folder": people_folder, "error": str(e)}

    def _analyze_projects_structure(self, root_folders: List[str]) -> Dict[str, Any]:
        """
        Analyze projects folder structure.

        Args:
            root_folders: List of root folder names

        Returns:
            Dictionary with projects structure information
        """
        # Look for project-related folders
        project_folders = [
            f for f in root_folders
            if any(keyword in f.lower() for keyword in ["project", "projeto", "work"])
        ]

        if not project_folders:
            return {"found": False}

        projects_folder = project_folders[0]

        try:
            # Analyze hierarchy (e.g., Company/Project structure)
            structure = self._explore_folder_structure(projects_folder, max_depth=3)

            # Detect if there's a hierarchy pattern
            hierarchy_pattern = self._detect_hierarchy_pattern(structure)

            # Sample some project notes for schema
            project_files = self._find_markdown_files(structure, max_files=5)
            sample_schemas = []

            for file_path in project_files:
                note_data = self._get_note_metadata(file_path)
                if note_data and note_data.get("frontmatter"):
                    sample_schemas.append(note_data["frontmatter"])

            common_schema = self._infer_common_schema(sample_schemas)

            return {
                "found": True,
                "folders": [projects_folder],
                "hierarchy_pattern": hierarchy_pattern,
                "structure": structure,
                "common_schema": common_schema
            }
        except Exception as e:
            print(f"Error analyzing projects: {e}")
            return {"found": True, "folders": [projects_folder], "error": str(e)}

    def _explore_folder_structure(
        self,
        folder_path: str,
        max_depth: int = 2,
        current_depth: int = 0
    ) -> Dict[str, Any]:
        """
        Recursively explore folder structure.

        Args:
            folder_path: Path to folder
            max_depth: Maximum depth to explore
            current_depth: Current recursion depth

        Returns:
            Dictionary representing folder structure
        """
        if current_depth >= max_depth:
            return {"path": folder_path, "truncated": True}

        try:
            result = self.client.list_files_in_directory(folder_path)
            items = result.get("files", [])

            structure = {
                "path": folder_path,
                "folders": [],
                "files": [],
                "depth": current_depth
            }

            for item in items:
                if item.endswith("/"):
                    # It's a folder
                    subfolder = item.rstrip("/")
                    subfolder_path = f"{folder_path}/{subfolder}"
                    substructure = self._explore_folder_structure(
                        subfolder_path,
                        max_depth,
                        current_depth + 1
                    )
                    structure["folders"].append(substructure)
                else:
                    # It's a file
                    structure["files"].append(item)

            return structure
        except Exception as e:
            return {"path": folder_path, "error": str(e)}

    def _detect_daily_notes_pattern(self, structure: Dict[str, Any]) -> str:
        """
        Detect daily notes organizational pattern.

        Args:
            structure: Folder structure dictionary

        Returns:
            Detected pattern description
        """
        # Check for year folders (YYYY)
        folders = structure.get("folders", [])
        folder_names = [Path(f.get("path", "")).name for f in folders]

        year_pattern = any(re.match(r"^\d{4}$", name) for name in folder_names)
        month_pattern = any(re.match(r"^\d{2} - \w+", name) for name in folder_names)

        if year_pattern:
            if month_pattern:
                return "Daily Notes/YYYY/MM - Month Name/YYYY-MM-DD.md"
            return "Daily Notes/YYYY/YYYY-MM-DD.md"

        # Check files for date patterns
        files = structure.get("files", [])
        if any(re.match(r"^\d{4}-\d{2}-\d{2}\.md$", f) for f in files):
            return "Daily Notes/YYYY-MM-DD.md"

        return "Custom/Unknown pattern"

    def _detect_hierarchy_pattern(self, structure: Dict[str, Any]) -> Optional[str]:
        """
        Detect hierarchy pattern in projects structure.

        Args:
            structure: Folder structure dictionary

        Returns:
            Detected hierarchy pattern or None
        """
        folders = structure.get("folders", [])

        if not folders:
            return None

        # Check if there are subfolders (indicating hierarchy)
        has_subfolders = any(
            len(f.get("folders", [])) > 0 or len(f.get("files", [])) > 0
            for f in folders
        )

        if has_subfolders:
            return "Company/Project"

        return "Flat structure"

    def _find_sample_daily_note(self, structure: Dict[str, Any]) -> Optional[str]:
        """
        Find a sample daily note file.

        Args:
            structure: Folder structure dictionary

        Returns:
            Path to sample daily note or None
        """
        # Recursively search for a file matching daily note pattern
        def search_structure(struct: Dict[str, Any], base_path: str = "") -> Optional[str]:
            files = struct.get("files", [])
            for file in files:
                if re.match(r"^\d{4}-\d{2}-\d{2}\.md$", file):
                    return f"{base_path}/{file}".lstrip("/")

            for folder in struct.get("folders", []):
                folder_path = folder.get("path", "")
                result = search_structure(folder, folder_path)
                if result:
                    return result

            return None

        return search_structure(structure)

    def _find_markdown_files(self, structure: Dict[str, Any], max_files: int = 10) -> List[str]:
        """
        Find markdown files in structure.

        Args:
            structure: Folder structure dictionary
            max_files: Maximum number of files to return

        Returns:
            List of file paths
        """
        found_files = []

        def search_structure(struct: Dict[str, Any], base_path: str = ""):
            if len(found_files) >= max_files:
                return

            files = struct.get("files", [])
            for file in files:
                if file.endswith(".md"):
                    found_files.append(f"{base_path}/{file}".lstrip("/"))
                    if len(found_files) >= max_files:
                        return

            for folder in struct.get("folders", []):
                folder_path = folder.get("path", "")
                search_structure(folder, folder_path)

        search_structure(structure)
        return found_files

    def _get_note_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get note metadata including frontmatter and content.

        Args:
            file_path: Path to note file

        Returns:
            Dictionary with note data or None
        """
        try:
            return self.client.get_file_contents(file_path, return_json=True)
        except Exception as e:
            print(f"Error getting note metadata for {file_path}: {e}")
            return None

    def _extract_sections(self, content: str) -> List[str]:
        """
        Extract section headings from markdown content.

        Args:
            content: Markdown content

        Returns:
            List of section headings
        """
        sections = []
        for line in content.split("\n"):
            # Match markdown headings (### Heading)
            match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
            if match:
                sections.append(match.group(2).strip())
        return sections

    def _infer_common_schema(self, schemas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Infer common schema from multiple frontmatter examples.

        Args:
            schemas: List of frontmatter dictionaries

        Returns:
            Common schema with field types and frequency
        """
        if not schemas:
            return {}

        # Count field occurrences
        field_counter = Counter()
        field_types = defaultdict(Counter)

        for schema in schemas:
            for key, value in schema.items():
                field_counter[key] += 1
                # Determine type
                value_type = type(value).__name__
                field_types[key][value_type] += 1

        # Build common schema
        common_schema = {}
        total_schemas = len(schemas)

        for field, count in field_counter.items():
            frequency = count / total_schemas
            most_common_type = field_types[field].most_common(1)[0][0]

            common_schema[field] = {
                "type": most_common_type,
                "frequency": frequency,
                "present_in": count,
                "total": total_schemas
            }

        return common_schema

    def _build_folder_hierarchy(self) -> Dict[str, Any]:
        """
        Build complete folder hierarchy of vault.

        Returns:
            Dictionary representing complete vault structure
        """
        try:
            root_structure = self._explore_folder_structure("", max_depth=2)
            return root_structure
        except Exception as e:
            print(f"Error building folder hierarchy: {e}")
            return {"error": str(e)}

    def _calculate_statistics(self) -> Dict[str, int]:
        """
        Calculate basic vault statistics.

        Returns:
            Dictionary with statistics
        """
        # This is a basic implementation
        # Could be extended to count total files, notes, etc.
        return {
            "root_folders": len(self._get_root_folders())
        }
