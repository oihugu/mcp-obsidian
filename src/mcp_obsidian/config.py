"""
Configuration management for MCP Obsidian server.

This module handles vault configuration, including auto-detection of
structure patterns, frontmatter schemas, and user preferences.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class DailyNotesConfig:
    """Configuration for daily notes structure."""

    path_pattern: str = "auto-detect"  # e.g., "Daily Notes/YYYY/MM - Month Name/YYYY-MM-DD.md"
    detected_pattern: Optional[str] = None
    sections: list[str] = field(default_factory=lambda: ["auto-detect"])
    detected_sections: list[str] = field(default_factory=list)
    frontmatter_fields: list[str] = field(default_factory=list)


@dataclass
class PeopleConfig:
    """Configuration for people notes."""

    folder: str = "auto-detect"  # e.g., "People"
    detected_folder: Optional[str] = None
    frontmatter_schema: str = "auto-detect"
    detected_schema: Dict[str, str] = field(default_factory=dict)
    name_pattern: str = "{First Name} {Last Name}.md"


@dataclass
class ProjectsConfig:
    """Configuration for project notes."""

    folders: list[str] = field(default_factory=lambda: ["auto-detect"])
    detected_folders: list[str] = field(default_factory=list)
    frontmatter_schema: str = "auto-detect"
    detected_schema: Dict[str, str] = field(default_factory=dict)
    hierarchy_pattern: Optional[str] = None  # e.g., "Company/Project"


@dataclass
class FeaturesConfig:
    """Feature flags for the MCP server."""

    semantic_search: bool = False  # Requires embeddings setup
    auto_linking: bool = True
    template_suggestions: bool = True
    relationship_analysis: bool = True
    smart_frontmatter: bool = True


@dataclass
class VaultConfig:
    """Main vault configuration."""

    daily_notes: DailyNotesConfig = field(default_factory=DailyNotesConfig)
    people: PeopleConfig = field(default_factory=PeopleConfig)
    projects: ProjectsConfig = field(default_factory=ProjectsConfig)
    features: FeaturesConfig = field(default_factory=FeaturesConfig)

    # Metadata
    last_analyzed: Optional[str] = None
    vault_root_folders: list[str] = field(default_factory=list)


class ConfigManager:
    """Manages vault configuration with auto-detection capabilities."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to configuration file. If None, uses default location.
        """
        if config_path is None:
            # Try to find config in current directory or create default
            config_path = os.environ.get("OBSIDIAN_VAULT_CONFIG", "vault-config.json")

        self.config_path = Path(config_path)
        self.config: VaultConfig = self._load_or_create_config()

    def _load_or_create_config(self) -> VaultConfig:
        """Load existing config or create default one."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                return self._dict_to_config(data)
            except Exception as e:
                print(f"Error loading config: {e}. Using default.")
                return VaultConfig()
        else:
            return VaultConfig()

    def _dict_to_config(self, data: Dict[str, Any]) -> VaultConfig:
        """Convert dictionary to VaultConfig."""
        daily_notes = DailyNotesConfig(**data.get("daily_notes", {}))
        people = PeopleConfig(**data.get("people", {}))
        projects = ProjectsConfig(**data.get("projects", {}))
        features = FeaturesConfig(**data.get("features", {}))

        return VaultConfig(
            daily_notes=daily_notes,
            people=people,
            projects=projects,
            features=features,
            last_analyzed=data.get("last_analyzed"),
            vault_root_folders=data.get("vault_root_folders", [])
        )

    def _config_to_dict(self) -> Dict[str, Any]:
        """Convert VaultConfig to dictionary."""
        return {
            "daily_notes": asdict(self.config.daily_notes),
            "people": asdict(self.config.people),
            "projects": asdict(self.config.projects),
            "features": asdict(self.config.features),
            "last_analyzed": self.config.last_analyzed,
            "vault_root_folders": self.config.vault_root_folders
        }

    def save(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_path, "w") as f:
                json.dump(self._config_to_dict(), f, indent=2)
            print(f"Configuration saved to {self.config_path}")
        except Exception as e:
            print(f"Error saving config: {e}")

    def update_detected_patterns(
        self,
        daily_notes: Optional[Dict[str, Any]] = None,
        people: Optional[Dict[str, Any]] = None,
        projects: Optional[Dict[str, Any]] = None,
        vault_folders: Optional[list[str]] = None
    ) -> None:
        """
        Update detected patterns in configuration.

        Args:
            daily_notes: Detected daily notes patterns
            people: Detected people patterns
            projects: Detected projects patterns
            vault_folders: List of root folders in vault
        """
        if daily_notes:
            self.config.daily_notes.detected_pattern = daily_notes.get("pattern")
            self.config.daily_notes.detected_sections = daily_notes.get("sections", [])
            self.config.daily_notes.frontmatter_fields = daily_notes.get("frontmatter_fields", [])

        if people:
            self.config.people.detected_folder = people.get("folder")
            self.config.people.detected_schema = people.get("schema", {})

        if projects:
            self.config.projects.detected_folders = projects.get("folders", [])
            self.config.projects.detected_schema = projects.get("schema", {})
            self.config.projects.hierarchy_pattern = projects.get("hierarchy_pattern")

        if vault_folders:
            self.config.vault_root_folders = vault_folders

        from datetime import datetime
        self.config.last_analyzed = datetime.now().isoformat()

    def get_daily_notes_pattern(self) -> Optional[str]:
        """Get the daily notes path pattern (user-defined or detected)."""
        if self.config.daily_notes.path_pattern != "auto-detect":
            return self.config.daily_notes.path_pattern
        return self.config.daily_notes.detected_pattern

    def get_people_folder(self) -> Optional[str]:
        """Get the people folder (user-defined or detected)."""
        if self.config.people.folder != "auto-detect":
            return self.config.people.folder
        return self.config.people.detected_folder

    def get_project_folders(self) -> list[str]:
        """Get project folders (user-defined or detected)."""
        if self.config.projects.folders != ["auto-detect"]:
            return self.config.projects.folders
        return self.config.projects.detected_folders

    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled."""
        return getattr(self.config.features, feature, False)


# Global config instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get or create global ConfigManager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def reload_config() -> ConfigManager:
    """Reload configuration from file."""
    global _config_manager
    _config_manager = ConfigManager()
    return _config_manager
