from collections.abc import Sequence
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
import json
import logging
import os
from . import obsidian

logger = logging.getLogger(__name__)

api_key = os.getenv("OBSIDIAN_API_KEY", "")
obsidian_host = os.getenv("OBSIDIAN_HOST", "127.0.0.1")

if api_key == "":
    raise ValueError(f"OBSIDIAN_API_KEY environment variable required. Working directory: {os.getcwd()}")

TOOL_LIST_FILES_IN_VAULT = "obsidian_list_files_in_vault"
TOOL_LIST_FILES_IN_DIR = "obsidian_list_files_in_dir"

class ToolHandler():
    def __init__(self, tool_name: str):
        self.name = tool_name

    def get_tool_description(self) -> Tool:
        raise NotImplementedError()

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        raise NotImplementedError()
    
class ListFilesInVaultToolHandler(ToolHandler):
    def __init__(self):
        super().__init__(TOOL_LIST_FILES_IN_VAULT)

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Lists all files and directories in the root directory of your Obsidian vault.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            },
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)

        files = api.list_files_in_vault()

        return [
            TextContent(
                type="text",
                text=json.dumps(files, indent=2)
            )
        ]
    
class ListFilesInDirToolHandler(ToolHandler):
    def __init__(self):
        super().__init__(TOOL_LIST_FILES_IN_DIR)

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Lists all files and directories that exist in a specific Obsidian directory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "dirpath": {
                        "type": "string",
                        "description": "Path to list files from (relative to your vault root). Note that empty directories will not be returned."
                    },
                },
                "required": ["dirpath"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:

        if "dirpath" not in args:
            raise RuntimeError("dirpath argument missing in arguments")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)

        files = api.list_files_in_dir(args["dirpath"])

        return [
            TextContent(
                type="text",
                text=json.dumps(files, indent=2)
            )
        ]
    
class GetFileContentsToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_file_contents")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Return the content of a single file in your vault.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the relevant file (relative to your vault root).",
                        "format": "path"
                    },
                },
                "required": ["filepath"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "filepath" not in args:
            raise RuntimeError("filepath argument missing in arguments")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)

        content = api.get_file_contents(args["filepath"])

        return [
            TextContent(
                type="text",
                text=json.dumps(content, indent=2)
            )
        ]
    
class SearchToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_simple_search")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="""Simple search for documents matching a specified text query across all files in the vault. 
            Use this tool when you want to do a simple text search""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Text to a simple search for in the vault."
                    },
                    "context_length": {
                        "type": "integer",
                        "description": "How much context to return around the matching string (default: 100)",
                        "default": 100
                    }
                },
                "required": ["query"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "query" not in args:
            raise RuntimeError("query argument missing in arguments")

        context_length = args.get("context_length", 100)
        
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        results = api.search(args["query"], context_length)
        
        formatted_results = []
        for result in results:
            formatted_matches = []
            for match in result.get('matches', []):
                context = match.get('context', '')
                match_pos = match.get('match', {})
                start = match_pos.get('start', 0)
                end = match_pos.get('end', 0)
                
                formatted_matches.append({
                    'context': context,
                    'match_position': {'start': start, 'end': end}
                })
                
            formatted_results.append({
                'filename': result.get('filename', ''),
                'score': result.get('score', 0),
                'matches': formatted_matches
            })

        return [
            TextContent(
                type="text",
                text=json.dumps(formatted_results, indent=2)
            )
        ]
    
class AppendContentToolHandler(ToolHandler):
   def __init__(self):
       super().__init__("obsidian_append_content")

   def get_tool_description(self):
       return Tool(
           name=self.name,
           description="Append content to a new or existing file in the vault.",
           inputSchema={
               "type": "object",
               "properties": {
                   "filepath": {
                       "type": "string",
                       "description": "Path to the file (relative to vault root)",
                       "format": "path"
                   },
                   "content": {
                       "type": "string",
                       "description": "Content to append to the file"
                   }
               },
               "required": ["filepath", "content"]
           }
       )

   def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
       if "filepath" not in args or "content" not in args:
           raise RuntimeError("filepath and content arguments required")

       api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
       api.append_content(args.get("filepath", ""), args["content"])

       return [
           TextContent(
               type="text",
               text=f"Successfully appended content to {args['filepath']}"
           )
       ]
   
class PatchContentToolHandler(ToolHandler):
   def __init__(self):
       super().__init__("obsidian_patch_content")

   def get_tool_description(self):
       return Tool(
           name=self.name,
           description="Insert content into an existing note relative to a heading, block reference, or frontmatter field.",
           inputSchema={
               "type": "object",
               "properties": {
                   "filepath": {
                       "type": "string",
                       "description": "Path to the file (relative to vault root)",
                       "format": "path"
                   },
                   "operation": {
                       "type": "string",
                       "description": "Operation to perform (append, prepend, or replace)",
                       "enum": ["append", "prepend", "replace"]
                   },
                   "target_type": {
                       "type": "string",
                       "description": "Type of target to patch",
                       "enum": ["heading", "block", "frontmatter"]
                   },
                   "target": {
                       "type": "string", 
                       "description": "Target identifier (heading path, block reference, or frontmatter field)"
                   },
                   "content": {
                       "type": "string",
                       "description": "Content to insert"
                   }
               },
               "required": ["filepath", "operation", "target_type", "target", "content"]
           }
       )

   def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
       if not all(k in args for k in ["filepath", "operation", "target_type", "target", "content"]):
           raise RuntimeError("filepath, operation, target_type, target and content arguments required")

       api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
       api.patch_content(
           args.get("filepath", ""),
           args.get("operation", ""),
           args.get("target_type", ""),
           args.get("target", ""),
           args.get("content", "")
       )

       return [
           TextContent(
               type="text",
               text=f"Successfully patched content in {args['filepath']}"
           )
       ]
       
class PutContentToolHandler(ToolHandler):
   def __init__(self):
       super().__init__("obsidian_put_content")

   def get_tool_description(self):
       return Tool(
           name=self.name,
           description="Create a new file in your vault or update the content of an existing one in your vault.",
           inputSchema={
               "type": "object",
               "properties": {
                   "filepath": {
                       "type": "string",
                       "description": "Path to the relevant file (relative to your vault root)",
                       "format": "path"
                   },
                   "content": {
                       "type": "string",
                       "description": "Content of the file you would like to upload"
                   }
               },
               "required": ["filepath", "content"]
           }
       )

   def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
       if "filepath" not in args or "content" not in args:
           raise RuntimeError("filepath and content arguments required")

       api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
       api.put_content(args.get("filepath", ""), args["content"])

       return [
           TextContent(
               type="text",
               text=f"Successfully uploaded content to {args['filepath']}"
           )
       ]
   

class DeleteFileToolHandler(ToolHandler):
   def __init__(self):
       super().__init__("obsidian_delete_file")

   def get_tool_description(self):
       return Tool(
           name=self.name,
           description="Delete a file or directory from the vault.",
           inputSchema={
               "type": "object",
               "properties": {
                   "filepath": {
                       "type": "string",
                       "description": "Path to the file or directory to delete (relative to vault root)",
                       "format": "path"
                   },
                   "confirm": {
                       "type": "boolean",
                       "description": "Confirmation to delete the file (must be true)",
                       "default": False
                   }
               },
               "required": ["filepath", "confirm"]
           }
       )

   def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
       if "filepath" not in args:
           raise RuntimeError("filepath argument missing in arguments")
       
       if not args.get("confirm", False):
           raise RuntimeError("confirm must be set to true to delete a file")

       api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
       api.delete_file(args["filepath"])

       return [
           TextContent(
               type="text",
               text=f"Successfully deleted {args['filepath']}"
           )
       ]
   
class ComplexSearchToolHandler(ToolHandler):
   def __init__(self):
       super().__init__("obsidian_complex_search")

   def get_tool_description(self):
       return Tool(
           name=self.name,
           description="""Complex search for documents using a JsonLogic query. 
           Supports standard JsonLogic operators plus 'glob' and 'regexp' for pattern matching. Results must be non-falsy.

           Use this tool when you want to do a complex search, e.g. for all documents with certain tags etc.
           ALWAYS follow query syntax in examples.

           Examples
            1. Match all markdown files
            {"glob": ["*.md", {"var": "path"}]}

            2. Match all markdown files with 1221 substring inside them
            {
              "and": [
                { "glob": ["*.md", {"var": "path"}] },
                { "regexp": [".*1221.*", {"var": "content"}] }
              ]
            }

            3. Match all markdown files in Work folder containing name Keaton
            {
              "and": [
                { "glob": ["*.md", {"var": "path"}] },
                { "regexp": [".*Work.*", {"var": "path"}] },
                { "regexp": ["Keaton", {"var": "content"}] }
              ]
            }
           """,
           inputSchema={
               "type": "object",
               "properties": {
                   "query": {
                       "type": "object",
                       "description": "JsonLogic query object. ALWAYS follow query syntax in examples. \
                            Example 1: {\"glob\": [\"*.md\", {\"var\": \"path\"}]} matches all markdown files \
                            Example 2: {\"and\": [{\"glob\": [\"*.md\", {\"var\": \"path\"}]}, {\"regexp\": [\".*1221.*\", {\"var\": \"content\"}]}]} matches all markdown files with 1221 substring inside them \
                            Example 3: {\"and\": [{\"glob\": [\"*.md\", {\"var\": \"path\"}]}, {\"regexp\": [\".*Work.*\", {\"var\": \"path\"}]}, {\"regexp\": [\"Keaton\", {\"var\": \"content\"}]}]} matches all markdown files in Work folder containing name Keaton \
                        "
                   }
               },
               "required": ["query"]
           }
       )

   def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
       if "query" not in args:
           raise RuntimeError("query argument missing in arguments")

       api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
       results = api.search_json(args.get("query", ""))

       return [
           TextContent(
               type="text",
               text=json.dumps(results, indent=2)
           )
       ]

class BatchGetFileContentsToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_batch_get_file_contents")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Return the contents of multiple files in your vault, concatenated with headers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepaths": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "Path to a file (relative to your vault root)",
                            "format": "path"
                        },
                        "description": "List of file paths to read"
                    },
                },
                "required": ["filepaths"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "filepaths" not in args:
            raise RuntimeError("filepaths argument missing in arguments")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        content = api.get_batch_file_contents(args["filepaths"])

        return [
            TextContent(
                type="text",
                text=content
            )
        ]

class PeriodicNotesToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_periodic_note")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Get current periodic note for the specified period.",
            inputSchema={
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "description": "The period type (daily, weekly, monthly, quarterly, yearly)",
                        "enum": ["daily", "weekly", "monthly", "quarterly", "yearly"]
                    },
                    "type": {
                        "type": "string",
                        "description": "The type of data to get ('content' or 'metadata'). 'content' returns just the content in Markdown format. 'metadata' includes note metadata (including paths, tags, etc.) and the content.",
                        "default": "content",
                        "enum": ["content", "metadata"]
                    }
                },
                "required": ["period"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "period" not in args:
            raise RuntimeError("period argument missing in arguments")

        period = args["period"]
        valid_periods = ["daily", "weekly", "monthly", "quarterly", "yearly"]
        if period not in valid_periods:
            raise RuntimeError(f"Invalid period: {period}. Must be one of: {', '.join(valid_periods)}")
        
        type = args["type"] if "type" in args else "content"
        valid_types = ["content", "metadata"]
        if type not in valid_types:
            raise RuntimeError(f"Invalid type: {type}. Must be one of: {', '.join(valid_types)}")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        content = api.get_periodic_note(period,type)

        return [
            TextContent(
                type="text",
                text=content
            )
        ]
        
class RecentPeriodicNotesToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_recent_periodic_notes")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Get most recent periodic notes for the specified period type.",
            inputSchema={
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "description": "The period type (daily, weekly, monthly, quarterly, yearly)",
                        "enum": ["daily", "weekly", "monthly", "quarterly", "yearly"]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of notes to return (default: 5)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 50
                    },
                    "include_content": {
                        "type": "boolean",
                        "description": "Whether to include note content (default: false)",
                        "default": False
                    }
                },
                "required": ["period"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "period" not in args:
            raise RuntimeError("period argument missing in arguments")

        period = args["period"]
        valid_periods = ["daily", "weekly", "monthly", "quarterly", "yearly"]
        if period not in valid_periods:
            raise RuntimeError(f"Invalid period: {period}. Must be one of: {', '.join(valid_periods)}")

        limit = args.get("limit", 5)
        if not isinstance(limit, int) or limit < 1:
            raise RuntimeError(f"Invalid limit: {limit}. Must be a positive integer")
            
        include_content = args.get("include_content", False)
        if not isinstance(include_content, bool):
            raise RuntimeError(f"Invalid include_content: {include_content}. Must be a boolean")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        results = api.get_recent_periodic_notes(period, limit, include_content)

        return [
            TextContent(
                type="text",
                text=json.dumps(results, indent=2)
            )
        ]
        
class RecentChangesToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_recent_changes")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Get recently modified files in the vault.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of files to return (default: 10)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100
                    },
                    "days": {
                        "type": "integer",
                        "description": "Only include files modified within this many days (default: 90)",
                        "minimum": 1,
                        "default": 90
                    }
                }
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        limit = args.get("limit", 10)
        if not isinstance(limit, int) or limit < 1:
            raise RuntimeError(f"Invalid limit: {limit}. Must be a positive integer")
            
        days = args.get("days", 90)
        if not isinstance(days, int) or days < 1:
            raise RuntimeError(f"Invalid days: {days}. Must be a positive integer")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        results = api.get_recent_changes(limit, days)

        return [
            TextContent(
                type="text",
                text=json.dumps(results, indent=2)
            )
        ]

# ==============================================================================
# DISCOVERY AND ANALYSIS TOOLS
# ==============================================================================

class AnalyzeVaultStructureToolHandler(ToolHandler):
    """Analyzes the complete vault structure to detect organizational patterns."""

    def __init__(self):
        super().__init__("obsidian_analyze_vault_structure")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Analyzes the complete vault structure to detect organizational patterns, including daily notes structure, people folder, projects hierarchy, and common frontmatter schemas. This helps the AI understand how the vault is organized.",
            inputSchema={
                "type": "object",
                "properties": {
                    "save_config": {
                        "type": "boolean",
                        "description": "Whether to save detected patterns to vault configuration (default: true)",
                        "default": True
                    }
                }
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        from .analyzers.structure import VaultStructureAnalyzer
        from .config import get_config_manager

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        analyzer = VaultStructureAnalyzer(api)

        # Analyze vault structure
        analysis = analyzer.analyze_vault_structure()

        # Optionally save to config
        save_config = args.get("save_config", True)
        if save_config:
            try:
                config_mgr = get_config_manager()

                # Update config with detected patterns
                daily_notes_data = analysis.get("daily_notes", {})
                people_data = analysis.get("people", {})
                projects_data = analysis.get("projects", {})

                config_mgr.update_detected_patterns(
                    daily_notes={
                        "pattern": daily_notes_data.get("pattern"),
                        "sections": daily_notes_data.get("sample_sections", []),
                        "frontmatter_fields": daily_notes_data.get("frontmatter_fields", [])
                    } if daily_notes_data.get("found") else None,
                    people={
                        "folder": people_data.get("folder"),
                        "schema": people_data.get("common_schema", {})
                    } if people_data.get("found") else None,
                    projects={
                        "folders": projects_data.get("folders", []),
                        "schema": projects_data.get("common_schema", {}),
                        "hierarchy_pattern": projects_data.get("hierarchy_pattern")
                    } if projects_data.get("found") else None,
                    vault_folders=analysis.get("root_folders", [])
                )

                config_mgr.save()
                analysis["config_saved"] = True
                analysis["config_path"] = str(config_mgr.config_path)
            except Exception as e:
                analysis["config_error"] = f"Failed to save config: {str(e)}"

        return [
            TextContent(
                type="text",
                text=json.dumps(analysis, indent=2)
            )
        ]


class AnalyzeFrontmatterInFolderToolHandler(ToolHandler):
    """Analyzes frontmatter patterns in a specific folder."""

    def __init__(self):
        super().__init__("obsidian_analyze_frontmatter")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Analyzes frontmatter patterns across notes in a specific folder. Detects common fields, their types, and suggests improvements for consistency.",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder_path": {
                        "type": "string",
                        "description": "Path to folder to analyze (e.g., 'People', 'Projetos/BeSolution')"
                    },
                    "sample_size": {
                        "type": "integer",
                        "description": "Number of notes to sample (default: 20)",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["folder_path"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        from .analyzers.frontmatter import FrontmatterAnalyzer

        if "folder_path" not in args:
            raise RuntimeError("folder_path argument missing")

        folder_path = args["folder_path"]
        sample_size = args.get("sample_size", 20)

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        analyzer = FrontmatterAnalyzer(api)

        analysis = analyzer.analyze_frontmatter_in_folder(folder_path, sample_size)

        return [
            TextContent(
                type="text",
                text=json.dumps(analysis, indent=2)
            )
        ]


class SuggestFrontmatterForNoteToolHandler(ToolHandler):
    """Suggests frontmatter improvements for a specific note."""

    def __init__(self):
        super().__init__("obsidian_suggest_frontmatter")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Analyzes a specific note and suggests frontmatter fields to add or fix based on similar notes in the same folder. Helps maintain consistency across notes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_path": {
                        "type": "string",
                        "description": "Path to the note to analyze (e.g., 'People/Igor Curi.md')"
                    },
                    "reference_folder": {
                        "type": "string",
                        "description": "Optional: Folder to use as reference for schema (default: note's parent folder)"
                    }
                },
                "required": ["note_path"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        from .analyzers.frontmatter import FrontmatterAnalyzer

        if "note_path" not in args:
            raise RuntimeError("note_path argument missing")

        note_path = args["note_path"]
        reference_folder = args.get("reference_folder")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        analyzer = FrontmatterAnalyzer(api)

        suggestions = analyzer.suggest_frontmatter_for_note(note_path, reference_folder)

        return [
            TextContent(
                type="text",
                text=json.dumps(suggestions, indent=2)
            )
        ]


class GetFolderContextToolHandler(ToolHandler):
    """Gets context and metadata about a specific folder."""

    def __init__(self):
        super().__init__("obsidian_get_folder_context")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Gets rich context about a folder, including its purpose (based on configuration), common patterns, file count, and organizational structure. Helps understand what a folder is used for.",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder_path": {
                        "type": "string",
                        "description": "Path to folder (e.g., 'People', 'Projetos', 'Daily Notes')"
                    }
                },
                "required": ["folder_path"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        from .analyzers.structure import VaultStructureAnalyzer
        from .analyzers.frontmatter import FrontmatterAnalyzer
        from .config import get_config_manager

        if "folder_path" not in args:
            raise RuntimeError("folder_path argument missing")

        folder_path = args["folder_path"]

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        config_mgr = get_config_manager()

        # Get folder contents
        try:
            folder_contents = api.list_files_in_directory(folder_path)
            files = folder_contents.get("files", [])
            md_files = [f for f in files if f.endswith(".md") and not f.endswith("/")]
            subfolders = [f.rstrip("/") for f in files if f.endswith("/")]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

        # Determine folder purpose based on config
        purpose = "Unknown"
        detected_type = None

        # Check if it's the daily notes folder
        daily_notes_folder = config_mgr.get_daily_notes_pattern()
        if daily_notes_folder and folder_path.startswith(daily_notes_folder.split("/")[0]):
            purpose = "Daily Notes - Contains daily journal entries and logs"
            detected_type = "daily_notes"

        # Check if it's the people folder
        people_folder = config_mgr.get_people_folder()
        if people_folder and folder_path == people_folder:
            purpose = "People - Contains notes about individuals and contacts"
            detected_type = "people"

        # Check if it's a projects folder
        project_folders = config_mgr.get_project_folders()
        if any(folder_path.startswith(pf) for pf in project_folders):
            purpose = "Projects - Contains project documentation and work items"
            detected_type = "projects"

        # Analyze frontmatter patterns (if not too many files)
        frontmatter_analysis = None
        if len(md_files) > 0 and len(md_files) <= 50:
            analyzer = FrontmatterAnalyzer(api)
            frontmatter_analysis = analyzer.analyze_frontmatter_in_folder(
                folder_path,
                sample_size=min(20, len(md_files))
            )

        context = {
            "folder_path": folder_path,
            "purpose": purpose,
            "detected_type": detected_type,
            "statistics": {
                "total_files": len(files),
                "markdown_files": len(md_files),
                "subfolders": len(subfolders)
            },
            "subfolders": subfolders[:20],  # Limit to first 20
            "sample_files": md_files[:10],  # Limit to first 10
            "frontmatter_patterns": frontmatter_analysis
        }

        return [
            TextContent(
                type="text",
                text=json.dumps(context, indent=2)
            )
        ]

# ==============================================================================
# PEOPLE MANAGEMENT TOOLS
# ==============================================================================

class CreatePersonToolHandler(ToolHandler):
    """Creates a new person note with structured frontmatter."""

    def __init__(self):
        super().__init__("obsidian_create_person")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Creates a new person note with structured frontmatter in the People folder. Automatically detects folder location and applies consistent schema.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Full name of the person (e.g., 'Igor Curi')"
                    },
                    "role": {
                        "type": "string",
                        "description": "Role or relationship (e.g., 'Colleague', 'Client', 'Manager')"
                    },
                    "company": {
                        "type": "string",
                        "description": "Company or organization"
                    },
                    "email": {
                        "type": "string",
                        "description": "Email address"
                    },
                    "linkedin": {
                        "type": "string",
                        "description": "LinkedIn profile URL"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorization"
                    },
                    "content": {
                        "type": "string",
                        "description": "Initial content for the note"
                    }
                },
                "required": ["name"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        from .knowledge.people import PeopleManager

        if "name" not in args:
            raise RuntimeError("name argument missing")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        manager = PeopleManager(api)

        name = args.pop("name")
        content = args.pop("content", "")

        result = manager.create_person(name=name, content=content, **args)

        return [TextContent(type="text", text=json.dumps(result, indent=2))]


class ListPeopleToolHandler(ToolHandler):
    """Lists all people in the vault."""

    def __init__(self):
        super().__init__("obsidian_list_people")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Lists all people in the People folder with optional filtering by company, role, or tags.",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_frontmatter": {
                        "type": "boolean",
                        "description": "Whether to include full frontmatter (default: false)",
                        "default": False
                    },
                    "company": {
                        "type": "string",
                        "description": "Filter by company"
                    },
                    "role": {
                        "type": "string",
                        "description": "Filter by role"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by tags"
                    }
                }
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        from .knowledge.people import PeopleManager

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        manager = PeopleManager(api)

        include_frontmatter = args.get("include_frontmatter", False)

        # Build filters
        filters = {}
        if "company" in args:
            filters["company"] = args["company"]
        if "role" in args:
            filters["role"] = args["role"]
        if "tags" in args:
            filters["tags"] = args["tags"]

        people = manager.list_people(
            filters=filters if filters else None,
            include_frontmatter=include_frontmatter
        )

        return [TextContent(type="text", text=json.dumps(people, indent=2))]


class UpdatePersonToolHandler(ToolHandler):
    """Updates a person's note."""

    def __init__(self):
        super().__init__("obsidian_update_person")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Updates a person's note frontmatter or appends content. Can update individual fields or entire frontmatter.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Person's name"
                    },
                    "role": {
                        "type": "string",
                        "description": "Update role"
                    },
                    "company": {
                        "type": "string",
                        "description": "Update company"
                    },
                    "email": {
                        "type": "string",
                        "description": "Update email"
                    },
                    "append_content": {
                        "type": "string",
                        "description": "Content to append to note"
                    }
                },
                "required": ["name"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        from .knowledge.people import PeopleManager

        if "name" not in args:
            raise RuntimeError("name argument missing")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        manager = PeopleManager(api)

        name = args.pop("name")
        append_content = args.pop("append_content", None)

        result = manager.update_person(name=name, append_content=append_content, **args)

        return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ==============================================================================
# PROJECTS MANAGEMENT TOOLS
# ==============================================================================

class CreateProjectToolHandler(ToolHandler):
    """Creates a new project note."""

    def __init__(self):
        super().__init__("obsidian_create_project")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Creates a new project note with structured frontmatter. Follows detected hierarchy (Company/Project) and applies consistent schema.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Project name (e.g., 'CNI - Chatbot')"
                    },
                    "company": {
                        "type": "string",
                        "description": "Company or client name (e.g., 'BeSolution')"
                    },
                    "status": {
                        "type": "string",
                        "description": "Project status",
                        "enum": ["active", "paused", "completed", "archived"]
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD)"
                    },
                    "team": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Team members"
                    },
                    "technologies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Technologies used"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorization"
                    },
                    "content": {
                        "type": "string",
                        "description": "Initial content"
                    }
                },
                "required": ["name"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        from .knowledge.projects import ProjectsManager

        if "name" not in args:
            raise RuntimeError("name argument missing")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        manager = ProjectsManager(api)

        name = args.pop("name")
        company = args.pop("company", None)
        content = args.pop("content", "")

        result = manager.create_project(name=name, company=company, content=content, **args)

        return [TextContent(type="text", text=json.dumps(result, indent=2))]


class ListProjectsToolHandler(ToolHandler):
    """Lists all projects in the vault."""

    def __init__(self):
        super().__init__("obsidian_list_projects")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Lists all projects with optional filtering by company, status, or tags.",
            inputSchema={
                "type": "object",
                "properties": {
                    "company": {
                        "type": "string",
                        "description": "Filter by company/client"
                    },
                    "status": {
                        "type": "string",
                        "description": "Filter by status",
                        "enum": ["active", "paused", "completed", "archived"]
                    },
                    "include_frontmatter": {
                        "type": "boolean",
                        "description": "Include full frontmatter (default: false)",
                        "default": False
                    }
                }
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        from .knowledge.projects import ProjectsManager

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        manager = ProjectsManager(api)

        company = args.get("company")
        include_frontmatter = args.get("include_frontmatter", False)

        # Build filters
        filters = {}
        if "status" in args:
            filters["status"] = args["status"]

        projects = manager.list_projects(
            company=company,
            filters=filters if filters else None,
            include_frontmatter=include_frontmatter
        )

        return [TextContent(type="text", text=json.dumps(projects, indent=2))]


class ListCompaniesToolHandler(ToolHandler):
    """Lists all companies/clients."""

    def __init__(self):
        super().__init__("obsidian_list_companies")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Lists all companies/clients from the projects hierarchy.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        from .knowledge.projects import ProjectsManager

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        manager = ProjectsManager(api)

        companies = manager.list_companies()

        return [TextContent(type="text", text=json.dumps({"companies": companies}, indent=2))]


# ==============================================================================
# DAILY NOTES TOOLS
# ==============================================================================

class CreateDailyNoteToolHandler(ToolHandler):
    """Creates a daily note with intelligent structure."""

    def __init__(self):
        super().__init__("obsidian_create_daily_note")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Creates a daily note for a specific date using detected organizational pattern and template structure.",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (defaults to today)"
                    },
                    "use_template": {
                        "type": "boolean",
                        "description": "Whether to use detected template structure (default: true)",
                        "default": True
                    },
                    "mentions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "People to mention in frontmatter"
                    }
                }
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        from .knowledge.daily import DailyNotesManager
        from datetime import datetime

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        manager = DailyNotesManager(api)

        date = None
        if "date" in args:
            try:
                date = datetime.strptime(args["date"], "%Y-%m-%d")
            except ValueError:
                raise RuntimeError("Invalid date format. Use YYYY-MM-DD")

        use_template = args.get("use_template", True)
        mentions = args.get("mentions")

        kwargs = {}
        if mentions:
            kwargs["mentions"] = mentions

        result = manager.create_daily_note(date=date, use_template=use_template, **kwargs)

        return [TextContent(type="text", text=json.dumps(result, indent=2))]


class AppendToDailyNoteToolHandler(ToolHandler):
    """Appends content to a daily note."""

    def __init__(self):
        super().__init__("obsidian_append_to_daily")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Appends content to a daily note, optionally under a specific section heading. Creates the note if it doesn't exist.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Content to append"
                    },
                    "section": {
                        "type": "string",
                        "description": "Section heading to append under (e.g., 'Notas Rápidas')"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (defaults to today)"
                    }
                },
                "required": ["content"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        from .knowledge.daily import DailyNotesManager
        from datetime import datetime

        if "content" not in args:
            raise RuntimeError("content argument missing")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        manager = DailyNotesManager(api)

        content = args["content"]
        section = args.get("section")

        date = None
        if "date" in args:
            try:
                date = datetime.strptime(args["date"], "%Y-%m-%d")
            except ValueError:
                raise RuntimeError("Invalid date format. Use YYYY-MM-DD")

        result = manager.append_to_daily_note(content=content, section=section, date=date)

        return [TextContent(type="text", text=json.dumps(result, indent=2))]


class GetRecentDailyNotesToolHandler(ToolHandler):
    """Gets recent daily notes."""

    def __init__(self):
        super().__init__("obsidian_get_recent_dailies")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Gets recent daily notes for a specified number of days.",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look back (default: 7)",
                        "default": 7,
                        "minimum": 1,
                        "maximum": 90
                    },
                    "include_content": {
                        "type": "boolean",
                        "description": "Whether to include full content (default: false)",
                        "default": False
                    }
                }
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        from .knowledge.daily import DailyNotesManager

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        manager = DailyNotesManager(api)

        days = args.get("days", 7)
        include_content = args.get("include_content", False)

        notes = manager.get_recent_daily_notes(days=days, include_content=include_content)

        return [TextContent(type="text", text=json.dumps(notes, indent=2))]


# ============================================================================
# Phase 2: Semantic Search and Navigation Tools
# ============================================================================

class SemanticSearchToolHandler(ToolHandler):
    """Semantic search for notes by meaning."""

    def __init__(self):
        super().__init__("obsidian_semantic_search")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Search for notes by semantic meaning (not just keywords). Uses AI embeddings to find conceptually similar notes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (can be a question, topic, or description)"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (default: 10, max: 50)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    },
                    "min_similarity": {
                        "type": "number",
                        "description": "Minimum similarity threshold 0-1 (default: 0.0)",
                        "default": 0.0,
                        "minimum": 0.0,
                        "maximum": 1.0
                    },
                    "folder": {
                        "type": "string",
                        "description": "Optional folder to search within"
                    },
                    "include_content": {
                        "type": "boolean",
                        "description": "Include content snippets in results (default: false)",
                        "default": False
                    }
                },
                "required": ["query"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        from .semantic import EmbeddingsManager, SemanticSearchEngine

        query = args["query"]
        top_k = args.get("top_k", 10)
        min_similarity = args.get("min_similarity", 0.0)
        folder = args.get("folder")
        include_content = args.get("include_content", False)

        # Initialize semantic search
        embeddings_manager = EmbeddingsManager()
        search_engine = SemanticSearchEngine(embeddings_manager)

        # Perform search
        results = search_engine.search(
            query=query,
            top_k=top_k,
            min_similarity=min_similarity,
            folder=folder,
            include_content=include_content
        )

        return [TextContent(type="text", text=json.dumps(results, indent=2))]


class FindRelatedNotesToolHandler(ToolHandler):
    """Find notes related to a specific note."""

    def __init__(self):
        super().__init__("obsidian_find_related_notes")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Find notes semantically related to a specific note based on content similarity.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the reference note"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of related notes to return (default: 10)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    },
                    "min_similarity": {
                        "type": "number",
                        "description": "Minimum similarity threshold 0-1 (default: 0.6)",
                        "default": 0.6,
                        "minimum": 0.0,
                        "maximum": 1.0
                    }
                },
                "required": ["filepath"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        from .semantic import EmbeddingsManager, SemanticSearchEngine, RelationshipAnalyzer

        filepath = args["filepath"]
        top_k = args.get("top_k", 10)
        min_similarity = args.get("min_similarity", 0.6)

        # Get note content
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        content = api.get_file_contents(filepath)

        # Initialize semantic search
        embeddings_manager = EmbeddingsManager()
        search_engine = SemanticSearchEngine(embeddings_manager)
        relationship_analyzer = RelationshipAnalyzer(search_engine)

        # Find related notes
        results = relationship_analyzer.find_related_notes(
            filepath=filepath,
            content=content,
            top_k=top_k,
            min_similarity=min_similarity
        )

        return [TextContent(type="text", text=json.dumps(results, indent=2))]


class SuggestLinksToolHandler(ToolHandler):
    """Suggest links to add to a note."""

    def __init__(self):
        super().__init__("obsidian_suggest_links")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Suggest potential links to add to a note based on semantic similarity and unlinked mentions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the note"
                    },
                    "max_suggestions": {
                        "type": "integer",
                        "description": "Maximum number of suggestions (default: 10)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    },
                    "min_similarity": {
                        "type": "number",
                        "description": "Minimum similarity threshold 0-1 (default: 0.7)",
                        "default": 0.7,
                        "minimum": 0.0,
                        "maximum": 1.0
                    },
                    "check_existing": {
                        "type": "boolean",
                        "description": "Don't suggest already linked notes (default: true)",
                        "default": True
                    }
                },
                "required": ["filepath"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        from .semantic import EmbeddingsManager, SemanticSearchEngine, RelationshipAnalyzer, LinkSuggestionEngine

        filepath = args["filepath"]
        max_suggestions = args.get("max_suggestions", 10)
        min_similarity = args.get("min_similarity", 0.7)
        check_existing = args.get("check_existing", True)

        # Get note content
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        content = api.get_file_contents(filepath)

        # Initialize link suggestion engine
        embeddings_manager = EmbeddingsManager()
        search_engine = SemanticSearchEngine(embeddings_manager)
        relationship_analyzer = RelationshipAnalyzer(search_engine)
        link_engine = LinkSuggestionEngine(relationship_analyzer)

        # Get suggestions
        suggestions = link_engine.suggest_links_for_note(
            filepath=filepath,
            content=content,
            max_suggestions=max_suggestions,
            min_similarity=min_similarity,
            check_existing=check_existing
        )

        return [TextContent(type="text", text=json.dumps(suggestions, indent=2))]


class AnalyzeRelationshipsToolHandler(ToolHandler):
    """Analyze semantic relationships in the vault."""

    def __init__(self):
        super().__init__("obsidian_analyze_relationships")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Analyze semantic relationships between notes, find clusters, and identify bridge notes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder": {
                        "type": "string",
                        "description": "Optional folder to analyze (analyzes entire vault if not specified)"
                    },
                    "min_similarity": {
                        "type": "number",
                        "description": "Minimum similarity for relationships (default: 0.7)",
                        "default": 0.7,
                        "minimum": 0.0,
                        "maximum": 1.0
                    },
                    "find_clusters": {
                        "type": "boolean",
                        "description": "Find clusters of related notes (default: true)",
                        "default": True
                    },
                    "find_bridges": {
                        "type": "boolean",
                        "description": "Find bridge notes connecting clusters (default: false)",
                        "default": False
                    },
                    "find_isolated": {
                        "type": "boolean",
                        "description": "Find isolated notes with few connections (default: false)",
                        "default": False
                    }
                }
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        from .semantic import EmbeddingsManager, SemanticSearchEngine, RelationshipAnalyzer

        folder = args.get("folder")
        min_similarity = args.get("min_similarity", 0.7)
        find_clusters = args.get("find_clusters", True)
        find_bridges = args.get("find_bridges", False)
        find_isolated = args.get("find_isolated", False)

        # Initialize relationship analyzer
        embeddings_manager = EmbeddingsManager()
        search_engine = SemanticSearchEngine(embeddings_manager)
        relationship_analyzer = RelationshipAnalyzer(search_engine)

        result = {}

        if find_clusters:
            clusters = relationship_analyzer.analyze_note_clusters(
                min_similarity=min_similarity,
                folder=folder
            )
            result["clusters"] = clusters

        if find_bridges:
            bridges = relationship_analyzer.find_bridge_notes(
                min_similarity=min_similarity,
                folder=folder
            )
            result["bridge_notes"] = bridges

        if find_isolated:
            isolated = relationship_analyzer.find_isolated_notes(
                min_similarity=min_similarity,
                folder=folder
            )
            result["isolated_notes"] = isolated

        # Always include summary stats
        if folder:
            stats = relationship_analyzer.analyze_folder_relationships(
                folder=folder,
                min_similarity=min_similarity
            )
            result["summary"] = stats
        else:
            # Get overall vault stats
            graph = relationship_analyzer.get_vault_graph(min_similarity=min_similarity)
            total_notes = len(graph)
            total_connections = sum(len(conns) for conns in graph.values())
            result["summary"] = {
                "total_notes": total_notes,
                "total_connections": total_connections,
                "avg_connections": round(total_connections / total_notes, 2) if total_notes else 0
            }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]


class RebuildEmbeddingsToolHandler(ToolHandler):
    """Rebuild the embeddings index."""

    def __init__(self):
        super().__init__("obsidian_rebuild_embeddings")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Rebuild the semantic search embeddings index for all or specific notes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "force": {
                        "type": "boolean",
                        "description": "Force complete rebuild (default: false, incremental)",
                        "default": False
                    },
                    "folder": {
                        "type": "string",
                        "description": "Optional folder to rebuild (rebuilds entire vault if not specified)"
                    }
                }
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        from .semantic import EmbeddingsManager, SemanticSearchEngine

        force = args.get("force", False)
        folder = args.get("folder")

        # Get all notes
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        vault_data = api.list_files_in_vault()
        all_files = vault_data.get("files", [])

        # Filter markdown files
        markdown_files = [f for f in all_files if f.endswith(".md")]

        # Filter by folder if specified
        if folder:
            markdown_files = [f for f in markdown_files if f.startswith(folder)]

        if not markdown_files:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "No markdown files found"}, indent=2)
            )]

        # Get content for all files
        notes = []
        for filepath in markdown_files:
            try:
                content = api.get_file_contents(filepath)
                notes.append({"filepath": filepath, "content": content})
            except Exception as e:
                logger.error(f"Failed to get content for {filepath}: {e}")

        # Build index
        embeddings_manager = EmbeddingsManager()
        search_engine = SemanticSearchEngine(embeddings_manager)

        result = search_engine.build_index(notes, force=force)

        return [TextContent(type="text", text=json.dumps(result, indent=2))]
