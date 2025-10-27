import logging
logger = logging.getLogger(__name__)
"""
Daily Notes manager for intelligent creation and management.

Handles creating daily notes following the detected organizational
pattern, including year/month/week folder structures.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import re
import calendar

from ..obsidian import Obsidian
from ..config import get_config_manager


class DailyNotesManager:
    """Manages creation and interaction with daily notes."""

    def __init__(self, obsidian_client: Obsidian):
        """
        Initialize daily notes manager.

        Args:
            obsidian_client: Obsidian API client
        """
        self.client = obsidian_client
        self.config = get_config_manager()

    def create_daily_note(
        self,
        date: Optional[datetime] = None,
        frontmatter: Optional[Dict[str, Any]] = None,
        use_template: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a daily note for the specified date.

        Args:
            date: Date for the daily note (defaults to today)
            frontmatter: Optional custom frontmatter
            use_template: Whether to use detected template structure
            **kwargs: Additional frontmatter fields

        Returns:
            Dictionary with creation result
        """
        if date is None:
            date = datetime.now()

        # Get daily notes pattern from config
        pattern = self.config.get_daily_notes_pattern()
        if not pattern:
            return {"error": "Daily notes pattern not detected. Run analyze_vault_structure first."}

        # Build file path based on detected pattern
        filepath = self._build_daily_note_path(date, pattern)

        # Build frontmatter
        if frontmatter is None:
            frontmatter = self._build_default_frontmatter(date, **kwargs)
        else:
            frontmatter = {**frontmatter, **kwargs}

        # Build content with sections if using template
        if use_template:
            content = self._build_template_content(frontmatter, date)
        else:
            content = self._build_note_content(frontmatter, "")

        # Create the note
        try:
            self.client.put_content(filepath, content)
            return {
                "success": True,
                "path": filepath,
                "date": date.strftime("%Y-%m-%d"),
                "frontmatter": frontmatter
            }
        except Exception as e:
            return {"error": str(e), "path": filepath}

    def get_daily_note(self, date: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """
        Get a specific daily note.

        Args:
            date: Date for the daily note (defaults to today)

        Returns:
            Dictionary with daily note data or None
        """
        if date is None:
            date = datetime.now()

        pattern = self.config.get_daily_notes_pattern()
        if not pattern:
            return None

        filepath = self._build_daily_note_path(date, pattern)

        try:
            note_data = self.client.get_file_contents(filepath, return_json=True)
            if note_data:
                return {
                    "path": filepath,
                    "date": date.strftime("%Y-%m-%d"),
                    "frontmatter": note_data.get("frontmatter", {}),
                    "content": note_data.get("content", ""),
                    "tags": note_data.get("tags", []),
                    "stat": note_data.get("stat", {})
                }
        except Exception as e:
            logger.debug(f"Error getting daily note for {date.strftime('%Y-%m-%d')}: {e}")
            return None

    def append_to_daily_note(
        self,
        content: str,
        section: Optional[str] = None,
        date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Append content to a daily note, optionally under a specific section.

        Args:
            content: Content to append
            section: Optional section heading to append under
            date: Date for the daily note (defaults to today)

        Returns:
            Dictionary with append result
        """
        if date is None:
            date = datetime.now()

        # Check if note exists, create if not
        daily_note = self.get_daily_note(date)
        if not daily_note:
            # Create the note first
            create_result = self.create_daily_note(date)
            if "error" in create_result:
                return create_result
            daily_note = {"path": create_result["path"]}

        filepath = daily_note["path"]

        try:
            if section:
                # Append under specific section using patch
                self.client.patch_content(
                    filepath,
                    operation="append",
                    target_type="heading",
                    target=section,
                    content=content
                )
            else:
                # Append to end of file
                self.client.append_content(filepath, "\n" + content)

            return {
                "success": True,
                "path": filepath,
                "date": date.strftime("%Y-%m-%d"),
                "section": section
            }

        except Exception as e:
            return {"error": str(e), "path": filepath}

    def get_recent_daily_notes(
        self,
        days: int = 7,
        include_content: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get recent daily notes.

        Args:
            days: Number of days to look back
            include_content: Whether to include full content

        Returns:
            List of daily note dictionaries
        """
        pattern = self.config.get_daily_notes_pattern()

        # If pattern is configured, use the optimized path-based approach
        if pattern:
            notes = []
            today = datetime.now()

            for i in range(days):
                date = today - timedelta(days=i)
                note = self.get_daily_note(date)

                if note:
                    if not include_content:
                        # Remove content to save space
                        note.pop("content", None)
                    notes.append(note)

            return notes

        # Fallback: Search for daily notes without pattern
        return self._search_recent_daily_notes(days, include_content)

    def list_daily_notes_in_range(
        self,
        start_date: datetime,
        end_date: datetime,
        include_content: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List all daily notes in a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            include_content: Whether to include full content

        Returns:
            List of daily note dictionaries
        """
        notes = []
        current_date = start_date

        while current_date <= end_date:
            note = self.get_daily_note(current_date)
            if note:
                if not include_content:
                    note.pop("content", None)
                notes.append(note)

            current_date += timedelta(days=1)

        return notes

    # Private helper methods

    def _build_daily_note_path(self, date: datetime, pattern: str) -> str:
        """Build file path for daily note based on detected pattern."""
        # Extract base folder from pattern
        # Patterns: "Daily Notes/YYYY/MM - Month/W##/YYYY-MM-DD.md"
        #          "Daily Notes/YYYY/MM - Month/YYYY-MM-DD.md"
        #          "Daily Notes/YYYY/YYYY-MM-DD.md"
        #          "Daily Notes/YYYY-MM-DD.md"

        base = "Daily Notes"  # Default, could be extracted from pattern

        year = date.strftime("%Y")
        month_num = date.strftime("%m")
        month_name = date.strftime("%B")  # Full month name
        week_num = date.isocalendar()[1]  # ISO week number
        filename = f"{date.strftime('%Y-%m-%d')}.md"

        if "W##" in pattern:
            # Pattern with week folders
            return f"{base}/{year}/{month_num} - {month_name}/W{week_num:02d}/{filename}"
        elif "MM - Month Name" in pattern:
            # Pattern with month folders, no week
            return f"{base}/{year}/{month_num} - {month_name}/{filename}"
        elif "YYYY/YYYY" in pattern:
            # Pattern with year folder only
            return f"{base}/{year}/{filename}"
        else:
            # Flat structure
            return f"{base}/{filename}"

    def _build_default_frontmatter(self, date: datetime, **kwargs) -> Dict[str, Any]:
        """Build default frontmatter for a daily note."""
        fm = {
            "type": "daily-note",
            "date": date.strftime("%Y-%m-%d"),
            "tags": ["work-log"],
        }

        # Add optional fields
        optional_fields = ["time", "mentions", "projects", "sticker"]
        for field in optional_fields:
            if field in kwargs and kwargs[field]:
                fm[field] = kwargs[field]

        # Add current time if not provided
        if "time" not in fm:
            fm["time"] = datetime.now().strftime("%H:%M")

        # mentions should be a list or null
        if "mentions" in fm and not isinstance(fm["mentions"], (list, type(None))):
            fm["mentions"] = [fm["mentions"]]

        return fm

    def _build_template_content(self, frontmatter: Dict[str, Any], date: datetime) -> str:
        """Build daily note content with detected section structure."""
        # Get detected sections from config
        sections = self.config.config.daily_notes.detected_sections

        # Build frontmatter
        fm_text = self._build_frontmatter_yaml(frontmatter)

        # If no sections detected, use default template
        if not sections:
            sections = [
                "Resumo do Dia",
                "Projetos do Dia",
                "Registro de Ações (Tasks)",
                "Reuniões",
                "Decisões e Bloqueios",
                "Notas Rápidas"
            ]

        # Build content with sections
        content_parts = [fm_text, ""]

        for section in sections:
            if "Projetos do Dia" in section:
                # Special table format for projects
                content_parts.append(f"### {section}")
                content_parts.append("| Projeto | Principal Contribuição | Status | Link |")
                content_parts.append("| ------- | ---------------------- | ------ | ---- |")
                content_parts.append("|         |                        |        |      |")
            else:
                content_parts.append(f"### {section}")
                content_parts.append("")

            content_parts.append("---")
            content_parts.append("")

        return "\n".join(content_parts)

    def _build_note_content(self, frontmatter: Dict[str, Any], content: str) -> str:
        """Build complete note content with frontmatter."""
        fm_text = self._build_frontmatter_yaml(frontmatter)

        if content:
            return f"{fm_text}\n\n{content}"
        else:
            return fm_text

    def _build_frontmatter_yaml(self, frontmatter: Dict[str, Any]) -> str:
        """Build YAML frontmatter block."""
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
        return "\n".join(fm_lines)

    def _search_recent_daily_notes(
        self,
        days: int = 7,
        include_content: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search for recent daily notes without relying on pattern detection.
        Recursively explores Daily Notes folder and finds recent notes.
        """
        import re

        notes = []
        today = datetime.now()
        cutoff_date = today - timedelta(days=days)

        # Date pattern in filenames: YYYY-MM-DD or MM-DD
        date_pattern = re.compile(r'(\d{4})-(\d{2})-(\d{2})\.md$|(\d{2})-(\d{2})\.md$')

        def explore_folder(path: str):
            """Recursively explore folder for daily note files."""
            try:
                result = self.client.list_files_in_dir(path)
                files = result.get('files', [])

                for file in files:
                    file_path = f"{path}/{file}" if not path.endswith('/') else f"{path}{file}"

                    # If it's a directory, explore it
                    if file.endswith('/'):
                        explore_folder(file_path)
                    # If it's a markdown file, check if it matches date pattern
                    elif file.endswith('.md'):
                        match = date_pattern.search(file)
                        if match:
                            try:
                                # Parse date from filename
                                if match.group(1):  # YYYY-MM-DD format
                                    file_date = datetime(
                                        int(match.group(1)),
                                        int(match.group(2)),
                                        int(match.group(3))
                                    )
                                else:  # MM-DD format - use current year from path
                                    year_match = re.search(r'/(\d{4})/', file_path)
                                    year = int(year_match.group(1)) if year_match else today.year
                                    file_date = datetime(
                                        year,
                                        int(match.group(4)),
                                        int(match.group(5))
                                    )

                                # Check if within date range
                                if cutoff_date <= file_date <= today:
                                    note_data = {
                                        "path": file_path,
                                        "date": file_date.strftime("%Y-%m-%d"),
                                        "filename": file
                                    }

                                    if include_content:
                                        try:
                                            content_data = self.client.get_file_contents(file_path, return_json=True)
                                            if content_data:
                                                note_data["content"] = content_data.get("content", "")
                                                note_data["frontmatter"] = content_data.get("frontmatter", {})
                                                note_data["tags"] = content_data.get("tags", [])
                                        except:
                                            pass

                                    notes.append(note_data)
                            except (ValueError, IndexError):
                                # Skip files that don't parse as valid dates
                                pass
            except Exception as e:
                logger.debug(f"Error exploring folder {path}: {e}")

        # Start exploring from Daily Notes folder
        try:
            explore_folder("Daily Notes")
        except Exception as e:
            logger.debug(f"Error accessing Daily Notes folder: {e}")
            return []

        # Sort by date descending (most recent first)
        notes.sort(key=lambda x: x["date"], reverse=True)

        return notes
