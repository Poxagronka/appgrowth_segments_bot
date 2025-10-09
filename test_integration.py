#!/usr/bin/env python3
"""Integration test for multiple bundle IDs segment creation logic"""

def generate_segment_name(app_id, country, seg_type, value):
    """Generate segment name with UPPERCASE country code"""
    if seg_type == "RetainedAtLeast":
        code = str(int(value)) + "d"
    else:  # ActiveUsers
        if isinstance(value, str):
            value = float(value)
        code = str(int(value * 100))

    # Make country uppercase, keep app_id as is, code lowercase
    country = country.upper()
    code = code.lower()

    return f"bloom_{app_id}_{country}_{code}"


def test_segment_creation_logic():
    """Test the segment creation logic with multiple bundle IDs"""

    print("Testing segment creation logic...\n")

    # Simulate input
    bundle_ids = ["com.easybrain.sudoku", "com.easybrain.nonogram"]
    countries = ["USA", "GBR", "DEU"]
    segment_types = ["RetainedAtLeast_7", "ActiveUsers_0.95"]

    # Calculate total segments
    total_segments = len(bundle_ids) * len(countries) * len(segment_types)
    print(f"Expected total segments: {total_segments}")
    print(f"  📱 Apps: {len(bundle_ids)}")
    print(f"  🌍 Countries: {len(countries)}")
    print(f"  📊 Types: {len(segment_types)}\n")

    # Generate all segment names
    generated_segments = []
    for app_id in bundle_ids:
        print(f"📱 Processing bundle ID: {app_id}")
        for country in countries:
            for seg_type_value in segment_types:
                seg_type, value = seg_type_value.split("_")

                if seg_type == "RetainedAtLeast":
                    val = int(value)
                else:  # ActiveUsers
                    val = float(value)

                name = generate_segment_name(app_id, country, seg_type, value)
                generated_segments.append(name)
                print(f"  ✅ Generated: {name}")

    print(f"\n📊 Total generated segments: {len(generated_segments)}")
    assert len(generated_segments) == total_segments, "Segment count mismatch!"

    # Verify all segments are unique
    unique_segments = set(generated_segments)
    print(f"📊 Unique segments: {len(unique_segments)}")
    assert len(unique_segments) == len(generated_segments), "Duplicate segments found!"

    # Verify segment naming pattern
    print("\n🔍 Verifying segment naming patterns:")
    for segment in generated_segments[:5]:  # Check first 5
        parts = segment.split("_")
        assert parts[0] == "bloom", f"Invalid prefix in {segment}"
        print(f"  ✅ {segment}")

    print("\n🎉 All integration tests passed!")
    print(f"\n📋 Sample segments created:")
    for segment in generated_segments[:10]:
        print(f"  • {segment}")
    if len(generated_segments) > 10:
        print(f"  ... and {len(generated_segments) - 10} more")


if __name__ == "__main__":
    test_segment_creation_logic()
