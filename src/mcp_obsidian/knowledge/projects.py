import logging
logger = logging.getLogger(__name__)
"""
Projects manager for CRUD operations on project notes.

Handles creating, listing, updating, and managing project notes
following the detected hierarchical structure (Company/Project).
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import re

from ..obsidian import Obsidian
from ..config import get_config_manager


class ProjectsManager:
    """Manages CRUD operations for project notes."""

    def __init__(self, obsidian_client: Obsidian):
        """
        Initialize projects manager.

        Args:
            obsidian_client: Obsidian API client
        """
        self.client = obsidian_client
        self.config = get_config_manager()

    def create_project(
        self,
        name: str,
        company: Optional[str] = None,
        frontmatter: Optional[Dict[str, Any]] = None,
        content: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new project note.

        Args:
            name: Project name (e.g., "CNI - Chatbot")
            company: Company/organization name (e.g., "BeSolution")
            frontmatter: Optional frontmatter dict
            content: Optional initial content
            **kwargs: Additional frontmatter fields (status, start_date, team, etc)

        Returns:
            Dictionary with creation result
        """
        # Get projects folders from config
        project_folders = self.config.get_project_folders()
        if not project_folders:
            return {"error": "Projects folder not detected. Run analyze_vault_structure first."}

        # Use first projects folder as base
        base_folder = project_folders[0]

        # Determine file path based on hierarchy
        if company:
            filepath = f"{base_folder}/{company}/{name}.md"
        else:
            filepath = f"{base_folder}/{name}.md"

        # Build frontmatter
        if frontmatter is None:
            frontmatter = self._build_default_frontmatter(name, company, **kwargs)
        else:
            frontmatter = {**frontmatter, **kwargs}
            if company and "company" not in frontmatter:
                frontmatter["company"] = company

        # Build full note content
        full_content = self._build_note_content(frontmatter, content)

        # Create the note
        try:
            self.client.put_content(filepath, full_content)
            return {
                "success": True,
                "path": filepath,
                "name": name,
                "company": company,
                "frontmatter": frontmatter
            }
        except Exception as e:
            return {"error": str(e), "path": filepath}

    def list_projects(
        self,
        company: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        include_frontmatter: bool = False,
        recursive: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List all projects in the vault.

        Args:
            company: Optional company filter
            filters: Optional filters (by status, tags, etc)
            include_frontmatter: Whether to include full frontmatter
            recursive: Whether to search in all subfolders

        Returns:
            List of project dictionaries
        """
        project_folders = self.config.get_project_folders()
        if not project_folders:
            return []

        projects_list = []

        for base_folder in project_folders:
            # If company specified, search in that company folder only
            if company:
                search_folders = [f"{base_folder}/{company}"]
            else:
                # Get all company folders
                search_folders = self._get_company_folders(base_folder)
                # Also include root folder
                search_folders.insert(0, base_folder)

            for folder in search_folders:
                try:
                    projects = self._list_projects_in_folder(
                        folder,
                        include_frontmatter=include_frontmatter,
                        recursive=recursive
                    )
                    projects_list.extend(projects)
                except Exception as e:
                    logger.debug(f"Error listing projects in {folder}: {e}")
                    continue

        # Apply filters if provided
        if filters:
            projects_list = [p for p in projects_list if self._matches_filters(p, filters)]

        return projects_list

    def get_project(self, name: str, company: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get a specific project's note data.

        Args:
            name: Project name
            company: Optional company name (for faster lookup)

        Returns:
            Dictionary with project data or None
        """
        # If company provided, try direct path first
        if company:
            project_folders = self.config.get_project_folders()
            if project_folders:
                filepath = f"{project_folders[0]}/{company}/{name}.md"
                project_data = self._get_project_data(filepath, name, company)
                if project_data:
                    return project_data

        # Otherwise search all projects
        all_projects = self.list_projects(include_frontmatter=True)
        for project in all_projects:
            if project["name"] == name:
                if company is None or project.get("company") == company:
                    return project

        return None

    def update_project(
        self,
        name: str,
        company: Optional[str] = None,
        frontmatter: Optional[Dict[str, Any]] = None,
        append_content: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Update a project's note.

        Args:
            name: Project name
            company: Optional company name
            frontmatter: New frontmatter (replaces existing)
            append_content: Content to append
            **kwargs: Individual frontmatter fields to update

        Returns:
            Dictionary with update result
        """
        # Get current project
        current = self.get_project(name, company)
        if not current:
            return {"error": f"Project '{name}' not found"}

        filepath = current["path"]

        try:
            # Update frontmatter if provided
            if frontmatter or kwargs:
                updated_fm = {**current["frontmatter"]}

                if frontmatter:
                    updated_fm.update(frontmatter)
                if kwargs:
                    updated_fm.update(kwargs)

                # Rebuild note
                content = current["content"]
                content = self._strip_frontmatter(content)
                new_content = self._build_note_content(updated_fm, content)

                self.client.put_content(filepath, new_content)

            # Append content if provided
            if append_content:
                self.client.append_content(filepath, "\n" + append_content)

            return {
                "success": True,
                "path": filepath,
                "name": name,
                "company": company
            }

        except Exception as e:
            return {"error": str(e), "path": filepath}

    def delete_project(self, name: str, company: Optional[str] = None) -> Dict[str, Any]:
        """
        Delete a project's note.

        Args:
            name: Project name
            company: Optional company name

        Returns:
            Dictionary with deletion result
        """
        project = self.get_project(name, company)
        if not project:
            return {"error": f"Project '{name}' not found"}

        filepath = project["path"]

        try:
            self.client.delete_file(filepath)
            return {
                "success": True,
                "path": filepath,
                "name": name
            }
        except Exception as e:
            return {"error": str(e), "path": filepath}

    def list_companies(self) -> List[str]:
        """
        List all companies (top-level folders in projects).

        Returns:
            List of company names
        """
        project_folders = self.config.get_project_folders()
        if not project_folders:
            return []

        companies = []
        for base_folder in project_folders:
            companies.extend(self._get_company_folders(base_folder))

        # Extract just the company names (remove full path)
        company_names = []
        for folder_path in companies:
            # Get last part of path
            company = folder_path.split("/")[-1]
            if company not in company_names:
                company_names.append(company)

        return sorted(company_names)

    # Private helper methods

    def _get_company_folders(self, base_folder: str) -> List[str]:
        """Get list of company folders within projects folder."""
        try:
            result = self.client.list_files_in_directory(base_folder)
            folders = [f.rstrip("/") for f in result.get("files", []) if f.endswith("/")]
            return [f"{base_folder}/{f}" for f in folders]
        except Exception as e:
            logger.debug(f"Error getting company folders: {e}")
            return []

    def _list_projects_in_folder(
        self,
        folder: str,
        include_frontmatter: bool = False,
        recursive: bool = True
    ) -> List[Dict[str, Any]]:
        """List all projects in a specific folder."""
        projects = []

        try:
            result = self.client.list_files_in_directory(folder)
            items = result.get("files", [])

            # Extract company from folder path
            parts = folder.split("/")
            company = parts[-1] if len(parts) > 1 else None

            for item in items:
                if item.endswith(".md"):
                    # It's a project file
                    name = item.replace(".md", "")
                    filepath = f"{folder}/{item}"

                    project_data = {
                        "name": name,
                        "path": filepath,
                        "company": company
                    }

                    if include_frontmatter:
                        note_data = self.client.get_file_contents(filepath, return_json=True)
                        if note_data:
                            project_data["frontmatter"] = note_data.get("frontmatter", {})
                            project_data["content"] = note_data.get("content", "")
                            project_data["tags"] = note_data.get("tags", [])

                    projects.append(project_data)

                elif recursive and item.endswith("/"):
                    # It's a subfolder, search recursively
                    subfolder = f"{folder}/{item.rstrip('/')}"
                    subprojects = self._list_projects_in_folder(
                        subfolder,
                        include_frontmatter,
                        recursive
                    )
                    projects.extend(subprojects)

        except Exception as e:
            logger.debug(f"Error listing projects in {folder}: {e}")

        return projects

    def _get_project_data(self, filepath: str, name: str, company: Optional[str]) -> Optional[Dict[str, Any]]:
        """Get project data from a specific file path."""
        try:
            note_data = self.client.get_file_contents(filepath, return_json=True)
            if note_data:
                return {
                    "name": name,
                    "path": filepath,
                    "company": company,
                    "frontmatter": note_data.get("frontmatter", {}),
                    "content": note_data.get("content", ""),
                    "tags": note_data.get("tags", []),
                    "stat": note_data.get("stat", {})
                }
        except Exception:
            return None

    def _build_default_frontmatter(
        self,
        name: str,
        company: Optional[str],
        **kwargs
    ) -> Dict[str, Any]:
        """Build default frontmatter for a project note."""
        fm = {
            "project": name,
            "type": "project",
            "created": datetime.now().strftime("%Y-%m-%d"),
        }

        if company:
            fm["company"] = company

        # Add optional fields from kwargs
        optional_fields = ["status", "start_date", "end_date", "team", "technologies", "tags", "client"]
        for field in optional_fields:
            if field in kwargs and kwargs[field]:
                fm[field] = kwargs[field]

        # Default status if not provided
        if "status" not in fm:
            fm["status"] = "active"

        # Ensure tags and team are lists
        for list_field in ["tags", "team", "technologies"]:
            if list_field in fm and not isinstance(fm[list_field], list):
                fm[list_field] = [fm[list_field]]

        return fm

    def _build_note_content(self, frontmatter: Dict[str, Any], content: str) -> str:
        """Build complete note content with frontmatter."""
        fm_lines = ["---"]

        for key, value in frontmatter.items():
            if isinstance(value, list):
                fm_lines.append(f"{key}:")
                for item in value:
                    fm_lines.append(f"  - {item}")
            elif isinstance(value, dict):
                fm_lines.append(f"{key}:")
                for k, v in value.items():
                    fm_lines.append(f"  {k}: {v}")
            elif value is None:
                fm_lines.append(f"{key}:")
            else:
                if isinstance(value, str) and (":" in value or "#" in value):
                    fm_lines.append(f'{key}: "{value}"')
                else:
                    fm_lines.append(f"{key}: {value}")

        fm_lines.append("---")
        fm_text = "\n".join(fm_lines)

        if content:
            return f"{fm_text}\n\n{content}"
        else:
            return fm_text

    def _strip_frontmatter(self, content: str) -> str:
        """Remove frontmatter from content."""
        pattern = r"^---\n.*?\n---\n\n?"
        return re.sub(pattern, "", content, flags=re.DOTALL)

    def _matches_filters(self, project: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if project matches all filters."""
        frontmatter = project.get("frontmatter", {})

        for key, value in filters.items():
            if key == "name":
                if value.lower() not in project.get("name", "").lower():
                    return False
            elif key == "company":
                if value.lower() not in project.get("company", "").lower():
                    return False
            elif key == "tags":
                project_tags = project.get("tags", [])
                filter_tags = value if isinstance(value, list) else [value]
                if not any(tag in project_tags for tag in filter_tags):
                    return False
            else:
                if frontmatter.get(key) != value:
                    return False

        return True
