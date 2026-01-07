-- First, let's see the current data for this roleplay
SELECT * FROM roleplay WHERE name LIKE '%Flavia%';

-- The issue is that competency_file_path, scenario_file_path, and logo_path columns 
-- appear to have wrong data (timestamps instead of file paths)

-- Fix: Set the correct values (empty strings for files that weren't uploaded)
UPDATE roleplay 
SET 
    competency_file_path = '',
    scenario_file_path = '',
    logo_path = ''
WHERE name LIKE '%Flavia%';

-- Verify the fix
SELECT id, name, file_path, image_file_path, competency_file_path, scenario_file_path, logo_path, created_at, updated_at 
FROM roleplay 
WHERE name LIKE '%Flavia%';
