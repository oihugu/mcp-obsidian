"""
People manager for CRUD operations on person notes.

Handles creating, listing, updating, and managing person notes
following the detected organizational structure.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import re

from ..obsidian import Obsidian
from ..config import get_config_manager


class PeopleManager:
    """Manages CRUD operations for person notes."""

    def __init__(self, obsidian_client: Obsidian):
        """
        Initialize people manager.

        Args:
            obsidian_client: Obsidian API client
        """
        self.client = obsidian_client
        self.config = get_config_manager()

    def create_person(
        self,
        name: str,
        frontmatter: Optional[Dict[str, Any]] = None,
        content: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new person note with structured frontmatter.

        Args:
            name: Full name of the person (e.g., "Igor Curi")
            frontmatter: Optional frontmatter dict. If None, uses defaults
            content: Optional initial content for the note
            **kwargs: Additional frontmatter fields (role, company, email, etc)

        Returns:
            Dictionary with creation result
        """
        # Get people folder from config
        people_folder = self.config.get_people_folder()
        if not people_folder:
            return {"error": "People folder not detected. Run analyze_vault_structure first."}

        # Generate file path
        filename = f"{name}.md"
        filepath = f"{people_folder}/{filename}"

        # Build frontmatter
        if frontmatter is None:
            frontmatter = self._build_default_frontmatter(name, **kwargs)
        else:
            # Merge provided frontmatter with kwargs
            frontmatter = {**frontmatter, **kwargs}

        # Build full note content
        full_content = self._build_note_content(frontmatter, content)

        # Create the note
        try:
            self.client.put_content(filepath, full_content)
            return {
                "success": True,
                "path": filepath,
                "name": name,
                "frontmatter": frontmatter
            }
        except Exception as e:
            return {"error": str(e), "path": filepath}

    def list_people(
        self,
        filters: Optional[Dict[str, Any]] = None,
        include_frontmatter: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List all people in the vault.

        Args:
            filters: Optional filters (by company, role, tags, etc)
            include_frontmatter: Whether to include full frontmatter

        Returns:
            List of person dictionaries
        """
        people_folder = self.config.get_people_folder()
        if not people_folder:
            return []

        try:
            result = self.client.list_files_in_directory(people_folder)
            files = result.get("files", [])
            people_files = [f for f in files if f.endswith(".md") and not f.endswith("/")]

            people_list = []
            for filename in people_files:
                filepath = f"{people_folder}/{filename}"
                name = filename.replace(".md", "")

                person_data = {"name": name, "path": filepath}

                # Optionally load frontmatter
                if include_frontmatter:
                    note_data = self.client.get_file_contents(filepath, return_json=True)
                    if note_data:
                        person_data["frontmatter"] = note_data.get("frontmatter", {})
                        person_data["tags"] = note_data.get("tags", [])

                # Apply filters if provided
                if filters:
                    if not self._matches_filters(person_data, filters):
                        continue

                people_list.append(person_data)

            return people_list

        except Exception as e:
            print(f"Error listing people: {e}")
            return []

    def get_person(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific person's note data.

        Args:
            name: Person's name (e.g., "Igor Curi")

        Returns:
            Dictionary with person data or None
        """
        people_folder = self.config.get_people_folder()
        if not people_folder:
            return None

        filepath = f"{people_folder}/{name}.md"

        try:
            note_data = self.client.get_file_contents(filepath, return_json=True)
            if note_data:
                return {
                    "name": name,
                    "path": filepath,
                    "frontmatter": note_data.get("frontmatter", {}),
                    "content": note_data.get("content", ""),
                    "tags": note_data.get("tags", []),
                    "stat": note_data.get("stat", {})
                }
        except Exception as e:
            print(f"Error getting person {name}: {e}")
            return None

    def update_person(
        self,
        name: str,
        frontmatter: Optional[Dict[str, Any]] = None,
        append_content: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Update a person's note.

        Args:
            name: Person's name
            frontmatter: New frontmatter (replaces existing)
            append_content: Content to append to the note
            **kwargs: Individual frontmatter fields to update

        Returns:
            Dictionary with update result
        """
        # Get current note
        current = self.get_person(name)
        if not current:
            return {"error": f"Person '{name}' not found"}

        filepath = current["path"]

        try:
            # Update frontmatter if provided
            if frontmatter or kwargs:
                updated_fm = {**current["frontmatter"]}

                if frontmatter:
                    updated_fm.update(frontmatter)
                if kwargs:
                    updated_fm.update(kwargs)

                # Rebuild note with updated frontmatter
                content = current["content"]

                # Remove old frontmatter from content if it exists
                content = self._strip_frontmatter(content)

                # Build new content with updated frontmatter
                new_content = self._build_note_content(updated_fm, content)

                self.client.put_content(filepath, new_content)

            # Append content if provided
            if append_content:
                self.client.append_content(filepath, "\n" + append_content)

            return {
                "success": True,
                "path": filepath,
                "name": name
            }

        except Exception as e:
            return {"error": str(e), "path": filepath}

    def delete_person(self, name: str) -> Dict[str, Any]:
        """
        Delete a person's note.

        Args:
            name: Person's name

        Returns:
            Dictionary with deletion result
        """
        people_folder = self.config.get_people_folder()
        if not people_folder:
            return {"error": "People folder not detected"}

        filepath = f"{people_folder}/{name}.md"

        try:
            self.client.delete_file(filepath)
            return {
                "success": True,
                "path": filepath,
                "name": name
            }
        except Exception as e:
            return {"error": str(e), "path": filepath}

    def search_people(
        self,
        query: str,
        search_in: List[str] = ["name", "content", "tags"]
    ) -> List[Dict[str, Any]]:
        """
        Search for people by name, content, or tags.

        Args:
            query: Search query
            search_in: Fields to search in

        Returns:
            List of matching people
        """
        all_people = self.list_people(include_frontmatter=True)
        results = []

        query_lower = query.lower()

        for person in all_people:
            match = False

            if "name" in search_in and query_lower in person["name"].lower():
                match = True

            if "tags" in search_in and person.get("tags"):
                if any(query_lower in tag.lower() for tag in person["tags"]):
                    match = True

            if "content" in search_in:
                # We'd need to load content here
                person_data = self.get_person(person["name"])
                if person_data and query_lower in person_data["content"].lower():
                    match = True

            if match:
                results.append(person)

        return results

    # Private helper methods

    def _build_default_frontmatter(self, name: str, **kwargs) -> Dict[str, Any]:
        """Build default frontmatter for a person note."""
        fm = {
            "name": name,
            "type": "person",
            "created": datetime.now().strftime("%Y-%m-%d"),
        }

        # Add optional fields from kwargs
        optional_fields = ["role", "company", "email", "linkedin", "phone", "tags", "projects"]
        for field in optional_fields:
            if field in kwargs and kwargs[field]:
                fm[field] = kwargs[field]

        # If tags is not a list, make it one
        if "tags" in fm and not isinstance(fm["tags"], list):
            fm["tags"] = [fm["tags"]]

        return fm

    def _build_note_content(self, frontmatter: Dict[str, Any], content: str) -> str:
        """Build complete note content with frontmatter."""
        # Build YAML frontmatter
        fm_lines = ["---"]

        for key, value in frontmatter.items():
            if isinstance(value, list):
                # Array values
                fm_lines.append(f"{key}:")
                for item in value:
                    fm_lines.append(f"  - {item}")
            elif isinstance(value, dict):
                # Object values
                fm_lines.append(f"{key}:")
                for k, v in value.items():
                    fm_lines.append(f"  {k}: {v}")
            elif value is None:
                fm_lines.append(f"{key}:")
            else:
                # Scalar values
                if isinstance(value, str) and (":" in value or "#" in value):
                    # Quote strings with special characters
                    fm_lines.append(f'{key}: "{value}"')
                else:
                    fm_lines.append(f"{key}: {value}")

        fm_lines.append("---")
        fm_text = "\n".join(fm_lines)

        # Combine with content
        if content:
            return f"{fm_text}\n\n{content}"
        else:
            return fm_text

    def _strip_frontmatter(self, content: str) -> str:
        """Remove frontmatter from content."""
        # Match frontmatter block (--- at start, content, --- )
        pattern = r"^---\n.*?\n---\n\n?"
        return re.sub(pattern, "", content, flags=re.DOTALL)

    def _matches_filters(self, person: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if person matches all filters."""
        frontmatter = person.get("frontmatter", {})

        for key, value in filters.items():
            if key == "name":
                if value.lower() not in person.get("name", "").lower():
                    return False
            elif key == "tags":
                person_tags = person.get("tags", [])
                # Check if any filter tag is in person tags
                filter_tags = value if isinstance(value, list) else [value]
                if not any(tag in person_tags for tag in filter_tags):
                    return False
            else:
                # Check frontmatter field
                if frontmatter.get(key) != value:
                    return False

        return True
