-- Check the exact column definition for roleplay.id
SHOW CREATE TABLE roleplay;

-- Check character set and collation
SELECT 
    COLUMN_NAME,
    COLUMN_TYPE,
    CHARACTER_SET_NAME,
    COLLATION_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
AND TABLE_NAME = 'roleplay'
AND COLUMN_NAME = 'id';
