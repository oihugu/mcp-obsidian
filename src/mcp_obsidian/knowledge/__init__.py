"""Knowledge management modules for people, projects, and daily notes."""

from .people import PeopleManager
from .projects import ProjectsManager
from .daily import DailyNotesManager

__all__ = ["PeopleManager", "ProjectsManager", "DailyNotesManager"]
