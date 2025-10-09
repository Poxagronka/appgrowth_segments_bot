#!/usr/bin/env python3
"""Test country code validation"""

from countries import ALL_VALID_COUNTRY_CODES

def parse_bulk_countries(bulk_text):
    """
    Parse bulk country codes from text input (supports newlines, commas, and spaces).
    Validates codes against ALL_VALID_COUNTRY_CODES.

    Returns:
        tuple: (valid_codes, invalid_codes) - two lists of country codes
    """
    if not bulk_text or not bulk_text.strip():
        return [], []

    # Replace commas with spaces, then split by any whitespace
    text = bulk_text.replace(',', ' ')
    codes = text.split()

    valid_codes = []
    invalid_codes = []

    for code in codes:
        code = code.strip().upper()
        if code:
            if code in ALL_VALID_COUNTRY_CODES:
                valid_codes.append(code)
            else:
                invalid_codes.append(code)

    return valid_codes, invalid_codes


if __name__ == "__main__":
    # Test 1: Valid codes
    print('Test 1: Valid codes')
    valid, invalid = parse_bulk_countries('USA GBR DEU')
    print(f'  Valid: {valid}')
    print(f'  Invalid: {invalid}')
    print(f'  ✓ Pass' if invalid == [] else f'  ✗ Fail')

    # Test 2: Mix of valid and invalid codes
    print('\nTest 2: Mix of valid and invalid codes')
    valid, invalid = parse_bulk_countries('USA XXX GBR YYY DEU')
    print(f'  Valid: {valid}')
    print(f'  Invalid: {invalid}')
    print(f'  ✓ Pass' if invalid == ['XXX', 'YYY'] else f'  ✗ Fail')

    # Test 3: Invalid codes
    print('\nTest 3: All invalid codes')
    valid, invalid = parse_bulk_countries('XXX YYY ZZZ')
    print(f'  Valid: {valid}')
    print(f'  Invalid: {invalid}')
    print(f'  ✓ Pass' if valid == [] and len(invalid) == 3 else f'  ✗ Fail')

    # Test 4: Comma-separated valid codes
    print('\nTest 4: Comma-separated valid codes')
    valid, invalid = parse_bulk_countries('USA, GBR, DEU')
    print(f'  Valid: {valid}')
    print(f'  Invalid: {invalid}')
    print(f'  ✓ Pass' if invalid == [] and len(valid) == 3 else f'  ✗ Fail')

    # Test 5: Mixed formats with typo
    print('\nTest 5: Mixed formats with typo')
    valid, invalid = parse_bulk_countries('USA GBR, DEUU, FRA')
    print(f'  Valid: {valid}')
    print(f'  Invalid: {invalid}')
    print(f'  ✓ Pass' if invalid == ['DEUU'] and len(valid) == 3 else f'  ✗ Fail')

    # Test 6: Empty input
    print('\nTest 6: Empty input')
    valid, invalid = parse_bulk_countries('')
    print(f'  Valid: {valid}')
    print(f'  Invalid: {invalid}')
    print(f'  ✓ Pass' if valid == [] and invalid == [] else f'  ✗ Fail')

    # Test 7: Kosovo (special case)
    print('\nTest 7: Kosovo special case')
    valid, invalid = parse_bulk_countries('XKX')
    print(f'  Valid: {valid}')
    print(f'  Invalid: {invalid}')
    print(f'  ✓ Pass' if valid == ['XKX'] and invalid == [] else f'  ✗ Fail')

    # Test 8: Newline-separated codes
    print('\nTest 8: Newline-separated codes')
    valid, invalid = parse_bulk_countries('USA\nGBR\nDEU\nINVALID')
    print(f'  Valid: {valid}')
    print(f'  Invalid: {invalid}')
    print(f'  ✓ Pass' if invalid == ['INVALID'] and len(valid) == 3 else f'  ✗ Fail')

    # Test 9: Case insensitivity
    print('\nTest 9: Case insensitivity (lowercase input)')
    valid, invalid = parse_bulk_countries('usa gbr deu')
    print(f'  Valid: {valid}')
    print(f'  Invalid: {invalid}')
    print(f'  ✓ Pass' if invalid == [] and valid == ['USA', 'GBR', 'DEU'] else f'  ✗ Fail')

    print('\n✅ All tests completed!')
    print(f'Total valid country codes in database: {len(ALL_VALID_COUNTRY_CODES)}')
