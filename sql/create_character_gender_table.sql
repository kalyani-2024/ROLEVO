-- Create table to store character names and their genders for each roleplay
-- This allows dynamic gender detection for any roleplay

CREATE TABLE IF NOT EXISTS roleplay_characters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    roleplay_id INT NOT NULL,
    character_name VARCHAR(100) NOT NULL,
    gender ENUM('male', 'female') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (roleplay_id) REFERENCES roleplay(id) ON DELETE CASCADE,
    UNIQUE KEY unique_roleplay_character (roleplay_id, character_name)
);

-- Example data (you can add characters when uploading roleplays)
-- INSERT INTO roleplay_characters (roleplay_id, character_name, gender) VALUES
-- (1, 'Bheem', 'male'),
-- (1, 'Satyam', 'male'),
-- (1, 'Kevin', 'male'),
-- (2, 'Kalyani', 'female'),
-- (2, 'Flavia', 'female');
