#!/usr/bin/env python3
"""Test script for bulk bundle ID parsing"""

def parse_bulk_bundle_ids(bulk_text):
    """
    Parse bulk bundle IDs from text input (supports newlines, commas, and spaces).

    Returns:
        list: List of bundle IDs (stripped and deduplicated)
    """
    if not bulk_text or not bulk_text.strip():
        return []

    # Replace commas with spaces, then split by any whitespace
    text = bulk_text.replace(',', ' ')
    bundle_ids = text.split()

    # Strip, remove empty strings, and deduplicate while preserving order
    seen = set()
    result = []
    for bid in bundle_ids:
        bid = bid.strip()
        if bid and bid not in seen:
            seen.add(bid)
            result.append(bid)

    return result


def test_parse_bulk_bundle_ids():
    """Test the parse_bulk_bundle_ids function"""

    print("Testing parse_bulk_bundle_ids function...\n")

    # Test 1: Single bundle ID
    test1 = "com.easybrain.number.puzzle.game"
    result1 = parse_bulk_bundle_ids(test1)
    print(f"Test 1 (single): {test1}")
    print(f"Result: {result1}")
    assert result1 == ["com.easybrain.number.puzzle.game"], "Test 1 failed"
    print("✅ Test 1 passed\n")

    # Test 2: Multiple bundle IDs separated by newlines
    test2 = """com.easybrain.number.puzzle.game
com.example.another.app
com.test.third.app"""
    result2 = parse_bulk_bundle_ids(test2)
    print(f"Test 2 (newlines):")
    print(f"Result: {result2}")
    assert len(result2) == 3, "Test 2 failed"
    print("✅ Test 2 passed\n")

    # Test 3: Multiple bundle IDs separated by commas
    test3 = "com.easybrain.number.puzzle.game,com.example.another.app,com.test.third.app"
    result3 = parse_bulk_bundle_ids(test3)
    print(f"Test 3 (commas): {test3}")
    print(f"Result: {result3}")
    assert len(result3) == 3, "Test 3 failed"
    print("✅ Test 3 passed\n")

    # Test 4: Multiple bundle IDs separated by spaces
    test4 = "com.easybrain.number.puzzle.game com.example.another.app com.test.third.app"
    result4 = parse_bulk_bundle_ids(test4)
    print(f"Test 4 (spaces): {test4}")
    print(f"Result: {result4}")
    assert len(result4) == 3, "Test 4 failed"
    print("✅ Test 4 passed\n")

    # Test 5: Mixed separators (commas, spaces, newlines)
    test5 = """com.easybrain.number.puzzle.game, com.example.another.app
    com.test.third.app com.test.fourth.app"""
    result5 = parse_bulk_bundle_ids(test5)
    print(f"Test 5 (mixed separators):")
    print(f"Result: {result5}")
    assert len(result5) == 4, "Test 5 failed"
    print("✅ Test 5 passed\n")

    # Test 6: Duplicates (should be removed)
    test6 = "com.easybrain.number.puzzle.game,com.easybrain.number.puzzle.game,com.example.another.app"
    result6 = parse_bulk_bundle_ids(test6)
    print(f"Test 6 (duplicates): {test6}")
    print(f"Result: {result6}")
    assert len(result6) == 2, "Test 6 failed (duplicates not removed)"
    print("✅ Test 6 passed\n")

    # Test 7: Empty input
    test7 = ""
    result7 = parse_bulk_bundle_ids(test7)
    print(f"Test 7 (empty): '{test7}'")
    print(f"Result: {result7}")
    assert result7 == [], "Test 7 failed"
    print("✅ Test 7 passed\n")

    # Test 8: Whitespace only
    test8 = "   \n   "
    result8 = parse_bulk_bundle_ids(test8)
    print(f"Test 8 (whitespace only)")
    print(f"Result: {result8}")
    assert result8 == [], "Test 8 failed"
    print("✅ Test 8 passed\n")

    print("🎉 All tests passed!")


if __name__ == "__main__":
    test_parse_bulk_bundle_ids()
