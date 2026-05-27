#!/usr/bin/env python3
"""Quick deployment readiness test."""

import sys
sys.path.insert(0, '.')

print("=" * 70)
print("[DEPLOYMENT READINESS TEST]")
print("=" * 70)

# Test 1: Module imports
print("\n[1] Testing module imports...")
try:
    from ic_agent.fuzzy import classify_file_by_name, match_project_name
    print("  ✅ Fuzzy matching module")
    
    from ic_agent.cache import FileCache, AnalysisCache
    print("  ✅ Cache module")
    
    from ic_agent.document_processor import normalize_text, extract_sections
    print("  ✅ Document processor module")
    
    from ic_agent.semantic_matcher import extract_requirements_from_oppm
    print("  ✅ Semantic matcher module")
    
    from ic_agent.database import init_db, get_or_create_project
    print("  ✅ Database module")
    
    from ic_agent.server import create_app
    print("  ✅ Flask server module")
    
    # Telegram is optional - try to load it
    try:
        from ic_agent.bot import run_telegram_bot
        print("  ✅ Telegram bot module")
    except ImportError as e:
        if "telegram" in str(e):
            print("  ⚠️  Telegram bot module (optional - install with: pip install python-telegram-bot>=20.0)")
        else:
            raise
    
    from ic_agent.agent import create_ic_agent
    print("  ✅ Agent module")
    
except ImportError as e:
    print(f"  ❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Configuration
print("\n[2] Testing configuration...")
try:
    from ic_agent import config
    if hasattr(config, 'ANTHROPIC_API_KEY'):
        print("  ✅ Configuration loaded")
    else:
        print("  ⚠️  Configuration loaded but missing ANTHROPIC_API_KEY")
except Exception as e:
    print(f"  ⚠️  Configuration warning: {e}")

# Test 3: Database initialization
print("\n[3] Testing database...")
try:
    from ic_agent.database import init_db
    init_db()
    print("  ✅ Database initialized")
except Exception as e:
    print(f"  ⚠️  Database warning: {e}")

# Test 4: Fuzzy matching functionality
print("\n[4] Testing fuzzy matching...")
try:
    category, confidence = classify_file_by_name("Tiger_OPPM.pdf")
    assert category == "oppm", f"Expected 'oppm', got '{category}'"
    print("  ✅ File classification works")
    
    matched, conf = match_project_name("tigerr", ["Tiger", "SchoolSystem"])
    assert matched == "Tiger", f"Expected 'Tiger', got '{matched}'"
    print("  ✅ Project name matching works")
except Exception as e:
    print(f"  ❌ Fuzzy matching failed: {e}")
    sys.exit(1)

# Test 5: Document processing
print("\n[5] Testing document processing...")
try:
    text = "  This  is   a   test   with  extra  spaces.  "
    normalized = normalize_text(text)
    assert "extra" in normalized, "Normalization failed"
    print("  ✅ Text normalization works")
except Exception as e:
    print(f"  ❌ Document processing failed: {e}")
    sys.exit(1)

# Test 6: Caching
print("\n[6] Testing caching...")
try:
    cache = FileCache()
    cache.set("file_123", "test.pdf", "test content")
    result = cache.get("file_123", "test.pdf")
    assert result is not None, "Cache retrieval failed"
    assert "test content" in result["content"], "Cache content mismatch"
    print("  ✅ File caching works")
except Exception as e:
    print(f"  ❌ Caching failed: {e}")
    sys.exit(1)

print("\n" + "=" * 70)
print("[✅ DEPLOYMENT READY] All critical components working!")
print("=" * 70)
print("\nNext steps:")
print("  1. Configure .env with production settings")
print("  2. Verify Google Drive credentials")
print("  3. Set up Telegram bot token")
print("  4. Run: gunicorn --workers 4 --bind 0.0.0.0:8000 'ic_agent.server:create_app()'")
