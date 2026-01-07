"""
Test script to demonstrate competency validation
Run this to test if your roleplay Excel competencies match your master file
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_competency_validation(roleplay_excel_path, competency_master_path):
    """
    Test if all competencies in roleplay Excel exist in master file
    
    Args:
        roleplay_excel_path: Path to roleplay Excel file
        competency_master_path: Path to competency master Excel file
    """
    from reader.excel import ExcelReader
    
    print(f"\n{'='*80}")
    print("COMPETENCY VALIDATION TEST")
    print(f"{'='*80}\n")
    
    print(f"Roleplay file: {roleplay_excel_path}")
    print(f"Master file:   {competency_master_path}\n")
    
    try:
        # Load Excel reader
        reader = ExcelReader(roleplay_excel_path, None, competency_master_path)
        
        print("✅ Files loaded successfully!\n")
        
        # Try to read first interaction (this triggers competency validation)
        print("Testing competencies from first interaction...\n")
        interaction_data = reader.get_interaction(1)
        
        print("✅ VALIDATION PASSED!")
        print(f"   All competencies in roleplay Excel are valid.")
        print(f"   Found competencies: {interaction_data.get('competencies', [])}\n")
        
        # Try to get total interactions
        total = reader.get_total_interactions()
        print(f"📊 Total interactions in roleplay: {total}")
        
        return True
        
    except ValueError as e:
        error_msg = str(e)
        if "Could not find competency" in error_msg:
            print("❌ VALIDATION FAILED!")
            print(f"   {error_msg}\n")
            print("💡 Solution:")
            print("   1. Open your roleplay Excel file")
            print("   2. Check the competency names in the 'Flow' sheet")
            print("   3. Make sure they EXACTLY match the master file (spelling, spacing, case)")
            print("   4. Common issues:")
            print("      - Extra spaces: 'EMP LEVEL 2 ' vs 'EMP LEVEL 2'")
            print("      - Wrong case: 'emp level 2' vs 'EMP LEVEL 2'")
            print("      - Typos: 'OPNTOCRIT' vs 'OPENTOCRIT'")
            return False
        else:
            print(f"❌ ERROR: {error_msg}")
            return False
    
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        print(f"\n{'='*80}\n")


if __name__ == "__main__":
    # Example usage
    print("Usage: python test_competency_validation.py <roleplay_excel> <master_excel>")
    print("\nOr edit this script to set your file paths:\n")
    
    # EDIT THESE PATHS TO TEST YOUR FILES
    roleplay_path = r"data\roleplay\RP_EXAMPLE_roleplay.xls"
    master_path = r"data\master\RP_EXAMPLE_competency.xlsx"
    
    if len(sys.argv) == 3:
        roleplay_path = sys.argv[1]
        master_path = sys.argv[2]
    
    if os.path.exists(roleplay_path) and os.path.exists(master_path):
        test_competency_validation(roleplay_path, master_path)
    else:
        print(f"\n⚠️  Files not found. Please provide valid paths.")
        print(f"   Roleplay: {roleplay_path} {'✓' if os.path.exists(roleplay_path) else '✗'}")
        print(f"   Master:   {master_path} {'✓' if os.path.exists(master_path) else '✗'}\n")
