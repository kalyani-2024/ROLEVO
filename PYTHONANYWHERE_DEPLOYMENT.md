# PythonAnywhere Deployment Changes

## Database Migration
Run this SQL command in the PythonAnywhere MySQL console:

```sql
ALTER TABLE roleplay 
ADD COLUMN competency_file_path VARCHAR(500) DEFAULT NULL
AFTER image_file_path;
```

Verify it was added:
```sql
DESCRIBE roleplay;
```

## File Changes to Upload

### 1. Updated Files
Upload these modified files to PythonAnywhere:

- `app/routes.py` - Fixed attempt counting (index 13 for repeat_attempts_allowed, index 16 for ideal_video_path)
- `app/enhanced_excel_validator.py` - Fixed competency validation (allows empty cells in meta competencies)
- `reader/master.py` - Added debug output for master file loading
- `app/templates/admin_user_detail.html` - Added roleplay history table
- `app/templates/user_dashboard.html` - Cleaned up (removed history section)

### 2. Test After Deployment

#### Test 1: Attempt Counting
1. Login as user
2. Start a roleplay configured with 1 attempt
3. Complete the roleplay
4. Check completion page - should show "0 of 1 attempts remaining"
5. Go to homepage - should also show "0 of 1 attempts remaining"

#### Test 2: Excel Validation
1. Login as admin
2. Upload roleplay Excel with meta competencies that don't fill all columns
3. Should NOT show error about missing meta competencies in column D
4. Should only error if NO meta competencies at all

#### Test 3: Admin User Detail
1. Login as admin
2. Go to Admin > Users
3. Click on any user who has completed roleplays
4. Should see "Roleplay History" table at bottom with:
   - Roleplay name
   - Character
   - Cluster
   - Status (Completed/Optimal Viewed)
   - Date
   - Score
   - Download button

#### Test 4: Master File Loading
Check the PythonAnywhere error logs after starting app. Should see:
```
📋 MASTER FILE LOADED: /path/to/Competency descriptions.xlsx
   Total competencies loaded: X
   Competency keys (Abbr column):
      - 'KEY1' → Description 1
      - 'KEY2' → Description 2
      ...
```

This helps debug competency matching errors.

## Common Issues & Fixes

### Issue 1: "Could not find competency 'X' in master file"
**Cause:** Mismatch between roleplay Excel and master competency file
**Check:** Look at the error log showing available competencies
**Fix:** Either:
- Update roleplay Excel to match available competencies (exact spelling/spacing)
- Upload new master competency file with the missing competency

### Issue 2: Attempt counting shows wrong numbers
**Cause:** Using wrong column index from get_roleplay_with_config()
**Fix:** Already fixed in routes.py - uses index 13 for repeat_attempts_allowed

### Issue 3: Excel validation errors for empty meta competency columns
**Cause:** Validator was too strict
**Fix:** Already fixed in enhanced_excel_validator.py - only errors if ALL competencies missing

## Reload Web App
After uploading all files and running the SQL migration:

1. Go to PythonAnywhere Web tab
2. Click "Reload" button for your web app
3. Check error logs for any startup issues
4. Test all functionality above

## Files Modified (Summary)
- ✅ Database: Added `competency_file_path` column
- ✅ `app/routes.py`: Fixed indices 11→13, 14→16, added roleplay history query
- ✅ `app/enhanced_excel_validator.py`: Less strict competency validation
- ✅ `reader/master.py`: Debug output for loaded competencies  
- ✅ `app/templates/admin_user_detail.html`: Added history table
- ✅ `app/templates/user_dashboard.html`: Removed history (admin-only now)
