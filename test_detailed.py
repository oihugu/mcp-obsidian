#!/usr/bin/env python3
"""
Detailed tests for specific scenarios.
"""

import os
import json

# Set environment variables for remote API
os.environ['OBSIDIAN_API_KEY'] = '07452926311ed660b8a3d309a2581979dbe404a393375635c20873e94aadb870'
os.environ['OBSIDIAN_PROTOCOL'] = 'http'
os.environ['OBSIDIAN_HOST'] = 'secondbrain.oihugudev.com.br'
os.environ['OBSIDIAN_PORT'] = '80'

from src.mcp_obsidian import tools


def test_project_folder_context():
    """Test getting context for a specific project folder"""
    print("="*80)
    print("TEST: Getting context for BeSolution/CNI folder")
    print("="*80)

    handler = tools.GetFolderContextToolHandler()

    result = handler.run_tool({"folder_path": "Projetos/BeSolution/CNI"})

    if result and len(result) > 0:
        data = json.loads(result[0].text)
        print(json.dumps(data, indent=2))
    else:
        print("No result")


def test_analyze_project_frontmatter():
    """Test analyzing frontmatter in project folder"""
    print("\n" + "="*80)
    print("TEST: Analyzing frontmatter in Projetos/BeSolution")
    print("="*80)

    handler = tools.AnalyzeFrontmatterInFolderToolHandler()

    result = handler.run_tool({
        "folder_path": "Projetos/BeSolution",
        "sample_size": 10
    })

    if result and len(result) > 0:
        data = json.loads(result[0].text)
        print(json.dumps(data, indent=2))
    else:
        print("No result")


def test_daily_notes_folder_context():
    """Test getting context for daily notes folder"""
    print("\n" + "="*80)
    print("TEST: Getting context for Daily Notes folder")
    print("="*80)

    handler = tools.GetFolderContextToolHandler()

    result = handler.run_tool({"folder_path": "Daily Notes"})

    if result and len(result) > 0:
        data = json.loads(result[0].text)
        print(json.dumps(data, indent=2))
    else:
        print("No result")


def test_analyze_vault_with_save():
    """Test analyzing vault and saving configuration"""
    print("\n" + "="*80)
    print("TEST: Analyzing vault and saving configuration")
    print("="*80)

    handler = tools.AnalyzeVaultStructureToolHandler()

    result = handler.run_tool({"save_config": True})

    if result and len(result) > 0:
        data = json.loads(result[0].text)

        print("\n📊 VAULT ANALYSIS COMPLETE")
        print(f"Config saved: {data.get('config_saved', False)}")
        if data.get('config_saved'):
            print(f"Config path: {data.get('config_path')}")

        # Show key findings
        print("\n🔍 KEY FINDINGS:")

        daily = data.get('daily_notes', {})
        if daily.get('found'):
            print(f"\n📅 Daily Notes:")
            print(f"   Pattern: {daily.get('pattern')}")
            print(f"   Frontmatter fields: {', '.join(daily.get('frontmatter_fields', []))}")

        people = data.get('people', {})
        if people.get('found'):
            print(f"\n👥 People:")
            print(f"   Total: {people.get('total_people')}")
            print(f"   Sample: {', '.join(people.get('sample_people', [])[:5])}")

        projects = data.get('projects', {})
        if projects.get('found'):
            print(f"\n📁 Projects:")
            print(f"   Hierarchy: {projects.get('hierarchy_pattern')}")

        # Show full JSON for reference
        print("\n" + "-"*80)
        print("FULL RESPONSE:")
        print(json.dumps(data, indent=2))
    else:
        print("No result")


if __name__ == "__main__":
    test_project_folder_context()
    test_analyze_project_frontmatter()
    test_daily_notes_folder_context()
    test_analyze_vault_with_save()

    print("\n" + "="*80)
    print("✅ Detailed tests completed!")
    print("="*80)
