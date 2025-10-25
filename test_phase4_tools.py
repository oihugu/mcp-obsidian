#!/usr/bin/env python3
"""
Test script for Phase 4 CRUD tools.
Tests People, Projects, and Daily Notes management.
"""

import os
import json
import sys
from datetime import datetime

# Set environment variables for remote API
os.environ['OBSIDIAN_API_KEY'] = '07452926311ed660b8a3d309a2581979dbe404a393375635c20873e94aadb870'
os.environ['OBSIDIAN_PROTOCOL'] = 'http'
os.environ['OBSIDIAN_HOST'] = 'secondbrain.oihugudev.com.br'
os.environ['OBSIDIAN_PORT'] = '80'

from src.mcp_obsidian import tools


def print_separator(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def test_people_crud():
    """Test People CRUD operations"""
    print_separator("PHASE 4 - PEOPLE MANAGEMENT")

    # Test 1: List existing people
    print("📋 TEST 1: List People")
    handler = tools.ListPeopleToolHandler()
    try:
        result = handler.run_tool({"include_frontmatter": False})
        data = json.loads(result[0].text)
        print(f"✅ Found {len(data)} people in vault")
        if data:
            print(f"   Sample: {', '.join([p['name'] for p in data[:3]])}")
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

    # Test 2: Create a test person
    print("\n👤 TEST 2: Create Person")
    test_person_name = "Test Person MCP"
    handler = tools.CreatePersonToolHandler()
    try:
        result = handler.run_tool({
            "name": test_person_name,
            "role": "Test Role",
            "company": "Test Company",
            "email": "test@example.com",
            "tags": ["test", "mcp"],
            "content": "## Notes\n\nThis is a test person created by MCP tests."
        })
        data = json.loads(result[0].text)

        if "success" in data and data["success"]:
            print(f"✅ Created person: {data['path']}")
        else:
            print(f"❌ FAILED: {data.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

    # Test 3: Update the person
    print("\n✏️  TEST 3: Update Person")
    handler = tools.UpdatePersonToolHandler()
    try:
        result = handler.run_tool({
            "name": test_person_name,
            "role": "Updated Role",
            "append_content": "\n\n## Update\n\nPerson was updated via MCP."
        })
        data = json.loads(result[0].text)

        if "success" in data and data["success"]:
            print(f"✅ Updated person successfully")
        else:
            print(f"❌ FAILED: {data.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")

    # Test 4: List with filters
    print("\n🔍 TEST 4: List People with Filter")
    handler = tools.ListPeopleToolHandler()
    try:
        result = handler.run_tool({
            "company": "Test Company",
            "include_frontmatter": True
        })
        data = json.loads(result[0].text)
        print(f"✅ Filtered list returned {len(data)} person(s)")
        if data and data[0].get('frontmatter'):
            print(f"   Frontmatter fields: {', '.join(data[0]['frontmatter'].keys())}")
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")

    return True


def test_projects_crud():
    """Test Projects CRUD operations"""
    print_separator("PHASE 4 - PROJECTS MANAGEMENT")

    # Test 1: List companies
    print("🏢 TEST 1: List Companies")
    handler = tools.ListCompaniesToolHandler()
    try:
        result = handler.run_tool({})
        data = json.loads(result[0].text)
        companies = data.get('companies', [])
        print(f"✅ Found {len(companies)} companies")
        print(f"   Companies: {', '.join(companies)}")
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

    # Test 2: List projects
    print("\n📁 TEST 2: List All Projects")
    handler = tools.ListProjectsToolHandler()
    try:
        result = handler.run_tool({"include_frontmatter": False})
        data = json.loads(result[0].text)
        print(f"✅ Found {len(data)} projects")
        if data:
            # Group by company
            by_company = {}
            for proj in data:
                company = proj.get('company', 'Unknown')
                if company not in by_company:
                    by_company[company] = []
                by_company[company].append(proj['name'])

            for company, projects in list(by_company.items())[:3]:
                print(f"   {company}: {len(projects)} projects")
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

    # Test 3: Create a test project
    print("\n📊 TEST 3: Create Project")
    test_project_name = "Test Project MCP"
    handler = tools.CreateProjectToolHandler()
    try:
        result = handler.run_tool({
            "name": test_project_name,
            "company": "BeSolution",
            "status": "active",
            "start_date": datetime.now().strftime("%Y-%m-%d"),
            "team": ["Test Person MCP"],
            "technologies": ["Python", "MCP"],
            "tags": ["test", "automation"],
            "content": "## Overview\n\nThis is a test project created by MCP tests."
        })
        data = json.loads(result[0].text)

        if "success" in data and data["success"]:
            print(f"✅ Created project: {data['path']}")
        else:
            print(f"❌ FAILED: {data.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

    # Test 4: List projects by company
    print("\n🔍 TEST 4: List Projects by Company")
    handler = tools.ListProjectsToolHandler()
    try:
        result = handler.run_tool({
            "company": "BeSolution",
            "include_frontmatter": False
        })
        data = json.loads(result[0].text)
        print(f"✅ Found {len(data)} projects in BeSolution")
        if data:
            print(f"   Sample: {', '.join([p['name'] for p in data[:3]])}")
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")

    return True


def test_daily_notes():
    """Test Daily Notes operations"""
    print_separator("PHASE 4 - DAILY NOTES MANAGEMENT")

    # Test 1: Create daily note for today
    print("📅 TEST 1: Create Daily Note for Today")
    handler = tools.CreateDailyNoteToolHandler()
    try:
        result = handler.run_tool({
            "use_template": True,
            "mentions": ["Test Person MCP"]
        })
        data = json.loads(result[0].text)

        if "success" in data and data["success"]:
            print(f"✅ Created daily note: {data['path']}")
            print(f"   Date: {data['date']}")
        else:
            print(f"⚠️  Note might already exist: {data.get('error', 'Unknown')}")
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

    # Test 2: Append to daily note
    print("\n➕ TEST 2: Append to Daily Note")
    handler = tools.AppendToDailyNoteToolHandler()
    try:
        result = handler.run_tool({
            "content": "- Testando MCP Obsidian Phase 4",
            "section": "Notas Rápidas"
        })
        data = json.loads(result[0].text)

        if "success" in data and data["success"]:
            print(f"✅ Appended to section: {data.get('section', 'N/A')}")
        else:
            print(f"⚠️  {data.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")

    # Test 3: Get recent daily notes
    print("\n📋 TEST 3: Get Recent Daily Notes")
    handler = tools.GetRecentDailyNotesToolHandler()
    try:
        result = handler.run_tool({
            "days": 7,
            "include_content": False
        })
        data = json.loads(result[0].text)
        print(f"✅ Found {len(data)} daily notes in last 7 days")
        if data:
            for note in data[:3]:
                print(f"   - {note['date']}")
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")

    return True


def main():
    print("\n" + "🧪 TESTING PHASE 4 CRUD TOOLS ".center(80, "="))
    print(f"Remote API: {os.environ['OBSIDIAN_HOST']}")
    print("="*80)

    results = {}

    # Run all tests
    print("\n⚠️  NOTE: Tests will create test data in your vault")
    print("   Test Person: 'Test Person MCP'")
    print("   Test Project: 'Test Project MCP' in BeSolution/")
    print("   Test Daily Note: Today's date with test content\n")

    results['people'] = test_people_crud()
    results['projects'] = test_projects_crud()
    results['daily_notes'] = test_daily_notes()

    # Summary
    print_separator("TEST SUMMARY")
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"Passed: {passed}/{total}")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")

    if passed == total:
        print("\n🎉 All Phase 4 tests passed!")
        print("\n📝 NOTE: Test data was created in your vault:")
        print("   - People/Test Person MCP.md")
        print("   - Projetos/BeSolution/Test Project MCP.md")
        print("   - Daily Notes/[today]/")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
