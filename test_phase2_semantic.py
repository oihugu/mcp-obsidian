#!/usr/bin/env python3
"""
Test script for Phase 2 Semantic Search tools.
Tests embeddings generation, semantic search, and relationship analysis.
"""

import os
import json
import sys

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


def test_rebuild_embeddings():
    """Test rebuilding embeddings index."""
    print_separator("PHASE 2 - TEST 1: REBUILD EMBEDDINGS")

    print("🔧 Building embeddings index for entire vault...")
    print("   (This may take a few minutes for the first run)\n")

    handler = tools.RebuildEmbeddingsToolHandler()
    try:
        # Build index for entire vault
        result = handler.run_tool({"force": False})
        data = json.loads(result[0].text)

        if data.get("success"):
            print(f"✅ Index built successfully!")
            print(f"   Total notes indexed: {data.get('total_notes', 0)}")
            print(f"   Failed: {data.get('failed', 0)}")
            return True
        else:
            print(f"❌ FAILED: {data.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_semantic_search():
    """Test semantic search functionality."""
    print_separator("PHASE 2 - TEST 2: SEMANTIC SEARCH")

    queries = [
        {
            "query": "projetos de inteligência artificial e chatbots",
            "folder": "Projetos",
            "top_k": 5
        },
        {
            "query": "pessoas da BeSolution",
            "folder": "People",
            "top_k": 5
        },
        {
            "query": "arquitetura de software e design patterns",
            "top_k": 3
        }
    ]

    handler = tools.SemanticSearchToolHandler()

    for i, query_params in enumerate(queries, 1):
        print(f"\n📋 TEST 2.{i}: Search: '{query_params['query']}'")
        if 'folder' in query_params:
            print(f"   Folder: {query_params['folder']}")

        try:
            result = handler.run_tool(query_params)
            data = json.loads(result[0].text)

            if data:
                print(f"✅ Found {len(data)} results:")
                for result in data[:3]:  # Show top 3
                    print(f"   - {result['filepath']}")
                    print(f"     Similarity: {result['similarity']:.3f}")
            else:
                print("⚠️  No results found")

        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            return False

    return True


def test_find_related_notes():
    """Test finding related notes."""
    print_separator("PHASE 2 - TEST 3: FIND RELATED NOTES")

    # Test with a known file (adjust based on your vault)
    test_cases = [
        {
            "name": "Person note",
            "filepath": "People/Alexandre Alves.md",
            "top_k": 5
        }
    ]

    handler = tools.FindRelatedNotesToolHandler()

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 TEST 3.{i}: Related to '{test_case['name']}'")
        print(f"   File: {test_case['filepath']}")

        try:
            result = handler.run_tool({
                "filepath": test_case["filepath"],
                "top_k": test_case["top_k"],
                "min_similarity": 0.6
            })
            data = json.loads(result[0].text)

            if data:
                print(f"✅ Found {len(data)} related notes:")
                for note in data[:3]:
                    print(f"   - {note['title']}")
                    print(f"     Path: {note['filepath']}")
                    print(f"     Similarity: {note['similarity']:.3f}")
            else:
                print("⚠️  No related notes found")

        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            return False

    return True


def test_suggest_links():
    """Test link suggestions."""
    print_separator("PHASE 2 - TEST 4: SUGGEST LINKS")

    test_file = "People/Alexandre Alves.md"

    print(f"📋 TEST 4: Link suggestions for '{test_file}'")

    handler = tools.SuggestLinksToolHandler()

    try:
        result = handler.run_tool({
            "filepath": test_file,
            "max_suggestions": 5,
            "min_similarity": 0.7
        })
        data = json.loads(result[0].text)

        if data:
            print(f"✅ Found {len(data)} link suggestions:")
            for suggestion in data:
                print(f"\n   Target: {suggestion['title']}")
                print(f"   Path: {suggestion['target']}")
                print(f"   Reason: {suggestion['reason']}")
                print(f"   Similarity: {suggestion.get('similarity', 0):.3f}")
        else:
            print("⚠️  No link suggestions found")

        return True

    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False


def test_analyze_relationships():
    """Test relationship analysis."""
    print_separator("PHASE 2 - TEST 5: ANALYZE RELATIONSHIPS")

    print("📋 TEST 5: Analyze relationships in People folder")

    handler = tools.AnalyzeRelationshipsToolHandler()

    try:
        result = handler.run_tool({
            "folder": "People",
            "min_similarity": 0.7,
            "find_clusters": True,
            "find_isolated": True
        })
        data = json.loads(result[0].text)

        summary = data.get("summary", {})
        clusters = data.get("clusters", [])
        isolated = data.get("isolated_notes", [])

        print(f"\n✅ Relationship Analysis Complete!")
        print(f"\n   Summary:")
        print(f"   - Total notes: {summary.get('total_notes', 0)}")
        print(f"   - Total connections: {summary.get('connectivity', {}).get('total_connections', 0)}")
        print(f"   - Avg connections/note: {summary.get('connectivity', {}).get('avg_connections_per_note', 0)}")

        if clusters:
            print(f"\n   Clusters found: {len(clusters)}")
            for i, cluster in enumerate(clusters[:3], 1):  # Show top 3
                print(f"\n   Cluster {i}:")
                print(f"   - Size: {cluster['size']} notes")
                print(f"   - Theme: {cluster['theme']}")
                print(f"   - Avg similarity: {cluster['avg_similarity']:.3f}")

        if isolated:
            print(f"\n   Isolated notes: {len(isolated)}")
            for note in isolated[:3]:  # Show top 3
                print(f"   - {note['title']} ({note['num_connections']} connections)")

        return True

    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "🧪 TESTING PHASE 2 SEMANTIC SEARCH ".center(80, "="))
    print(f"Remote API: {os.environ['OBSIDIAN_HOST']}")
    print("="*80)

    results = {}

    print("\n⚠️  NOTE: First run will download the sentence-transformers model")
    print("   Model: all-MiniLM-L6-v2 (~80MB)")
    print("   This is a one-time download.\n")

    # Run tests sequentially
    results['rebuild_embeddings'] = test_rebuild_embeddings()

    if results['rebuild_embeddings']:
        results['semantic_search'] = test_semantic_search()
        results['find_related'] = test_find_related_notes()
        results['suggest_links'] = test_suggest_links()
        results['analyze_relationships'] = test_analyze_relationships()
    else:
        print("\n⚠️  Skipping remaining tests due to index build failure")
        results['semantic_search'] = False
        results['find_related'] = False
        results['suggest_links'] = False
        results['analyze_relationships'] = False

    # Summary
    print_separator("TEST SUMMARY")
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"Passed: {passed}/{total}")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")

    if passed == total:
        print("\n🎉 All Phase 2 tests passed!")
        print("\n📊 System Status:")
        print("   - Embeddings index: Built and cached")
        print("   - Semantic search: Working")
        print("   - Relationship analysis: Working")
        print("   - Link suggestions: Working")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
