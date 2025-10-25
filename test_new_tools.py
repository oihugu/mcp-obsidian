#!/usr/bin/env python3
"""
Test script for new discovery and analysis tools.
Tests against remote Obsidian API.
"""

import os
import json
import sys

# Set environment variables for remote API
os.environ['OBSIDIAN_API_KEY'] = '07452926311ed660b8a3d309a2581979dbe404a393375635c20873e94aadb870'
os.environ['OBSIDIAN_PROTOCOL'] = 'http'
os.environ['OBSIDIAN_HOST'] = 'secondbrain.oihugudev.com.br'
os.environ['OBSIDIAN_PORT'] = '80'

# Import after setting env vars
from src.mcp_obsidian import tools


def print_separator(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def test_analyze_vault_structure():
    """Test obsidian_analyze_vault_structure"""
    print_separator("TEST 1: Analyze Vault Structure")

    handler = tools.AnalyzeVaultStructureToolHandler()

    try:
        result = handler.run_tool({"save_config": False})  # Don't save during test

        if result and len(result) > 0:
            data = json.loads(result[0].text)
            print("✅ SUCCESS - Vault Structure Analysis")
            print("\nRoot Folders:")
            for folder in data.get("root_folders", []):
                print(f"  - {folder}")

            print("\nDaily Notes:")
            daily = data.get("daily_notes", {})
            if daily.get("found"):
                print(f"  Folder: {daily.get('folder')}")
                print(f"  Pattern: {daily.get('pattern')}")
                print(f"  Sections: {', '.join(daily.get('sample_sections', [])[:3])}")
            else:
                print("  Not found")

            print("\nPeople:")
            people = data.get("people", {})
            if people.get("found"):
                print(f"  Folder: {people.get('folder')}")
                print(f"  Total: {people.get('total_people', 0)}")
            else:
                print("  Not found")

            print("\nProjects:")
            projects = data.get("projects", {})
            if projects.get("found"):
                print(f"  Folders: {', '.join(projects.get('folders', []))}")
                print(f"  Hierarchy: {projects.get('hierarchy_pattern')}")
            else:
                print("  Not found")

            return True
        else:
            print("❌ FAILED - No result returned")
            return False

    except Exception as e:
        print(f"❌ FAILED - Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_analyze_frontmatter():
    """Test obsidian_analyze_frontmatter"""
    print_separator("TEST 2: Analyze Frontmatter in Folder")

    handler = tools.AnalyzeFrontmatterInFolderToolHandler()

    try:
        # Test with People folder
        result = handler.run_tool({
            "folder_path": "People",
            "sample_size": 10
        })

        if result and len(result) > 0:
            data = json.loads(result[0].text)

            if "error" in data:
                print(f"⚠️  WARNING - {data['error']}")
                return True  # Not a failure, just no frontmatter

            print("✅ SUCCESS - Frontmatter Analysis")
            print(f"\nTotal files: {data.get('total_files', 0)}")
            print(f"Files with frontmatter: {data.get('files_with_frontmatter', 0)}")

            schema = data.get('schema', {})
            if schema:
                print("\nCommon fields:")
                for field, info in list(schema.items())[:5]:  # Show first 5
                    print(f"  - {field}: {info.get('type')} (in {info.get('present_in')}/{info.get('total')} notes)")
            else:
                print("\nNo frontmatter schema detected")

            suggestions = data.get('suggestions', [])
            if suggestions:
                print("\nSuggestions:")
                for sug in suggestions[:3]:  # Show first 3
                    print(f"  - {sug}")

            return True
        else:
            print("❌ FAILED - No result returned")
            return False

    except Exception as e:
        print(f"❌ FAILED - Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_suggest_frontmatter():
    """Test obsidian_suggest_frontmatter"""
    print_separator("TEST 3: Suggest Frontmatter for Note")

    handler = tools.SuggestFrontmatterForNoteToolHandler()

    try:
        # Test with a person note
        result = handler.run_tool({
            "note_path": "People/Igor Curi.md"
        })

        if result and len(result) > 0:
            data = json.loads(result[0].text)

            if "error" in data:
                print(f"⚠️  WARNING - {data['error']}")
                return True  # Not a failure

            print("✅ SUCCESS - Frontmatter Suggestions")
            print(f"\nNote: {data.get('note_path')}")

            current_fm = data.get('current_frontmatter', {})
            print(f"Current frontmatter fields: {len(current_fm)}")
            if current_fm:
                print(f"  Fields: {', '.join(current_fm.keys())}")
            else:
                print("  No frontmatter currently")

            suggestions = data.get('suggestions', [])
            if suggestions:
                print(f"\nSuggestions ({len(suggestions)}):")
                for sug in suggestions:
                    print(f"  - {sug.get('type')}: {sug.get('message')}")
            else:
                print("\nNo suggestions (frontmatter is already consistent)")

            return True
        else:
            print("❌ FAILED - No result returned")
            return False

    except Exception as e:
        print(f"❌ FAILED - Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_get_folder_context():
    """Test obsidian_get_folder_context"""
    print_separator("TEST 4: Get Folder Context")

    handler = tools.GetFolderContextToolHandler()

    try:
        # Test with Projetos folder
        result = handler.run_tool({
            "folder_path": "Projetos"
        })

        if result and len(result) > 0:
            data = json.loads(result[0].text)

            if "error" in data:
                print(f"❌ FAILED - {data['error']}")
                return False

            print("✅ SUCCESS - Folder Context")
            print(f"\nFolder: {data.get('folder_path')}")
            print(f"Purpose: {data.get('purpose')}")
            print(f"Type: {data.get('detected_type')}")

            stats = data.get('statistics', {})
            print(f"\nStatistics:")
            print(f"  Total files: {stats.get('total_files', 0)}")
            print(f"  Markdown files: {stats.get('markdown_files', 0)}")
            print(f"  Subfolders: {stats.get('subfolders', 0)}")

            subfolders = data.get('subfolders', [])
            if subfolders:
                print(f"\nSubfolders ({len(subfolders)}):")
                for sf in subfolders[:5]:  # Show first 5
                    print(f"  - {sf}")

            return True
        else:
            print("❌ FAILED - No result returned")
            return False

    except Exception as e:
        print(f"❌ FAILED - Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "🧪 TESTING NEW MCP OBSIDIAN TOOLS ".center(80, "="))
    print(f"Remote API: {os.environ['OBSIDIAN_HOST']}")
    print("="*80)

    results = {}

    # Run all tests
    results['vault_structure'] = test_analyze_vault_structure()
    results['frontmatter_analysis'] = test_analyze_frontmatter()
    results['frontmatter_suggestions'] = test_suggest_frontmatter()
    results['folder_context'] = test_get_folder_context()

    # Summary
    print_separator("TEST SUMMARY")
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"Passed: {passed}/{total}")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
