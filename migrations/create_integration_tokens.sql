-- Migration: Create integration_tokens table for AIO SSO
-- Run this migration to enable AIO platform integration

CREATE TABLE IF NOT EXISTS integration_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    token VARCHAR(64) UNIQUE NOT NULL,
    user_id INT NULL,
    cluster_id VARCHAR(50) NULL,
    callback_url VARCHAR(500) NULL,
    aio_user_id VARCHAR(100) NULL,
    user_email VARCHAR(255) NULL,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    used TINYINT DEFAULT 0,
    INDEX idx_token (token),
    INDEX idx_expires (expires_at),
    INDEX idx_used (used),
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Optional: Create roleplay_competencies table if not exists
-- Note: roleplay.id is VARCHAR (e.g., RP_XXXXX), not INT
CREATE TABLE IF NOT EXISTS roleplay_competencies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    roleplay_id VARCHAR(50) NOT NULL,
    competency_id VARCHAR(50) NOT NULL,
    competency_name VARCHAR(100) NOT NULL,
    max_score FLOAT DEFAULT 3,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_roleplay (roleplay_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Add cluster_id column to cluster table if not exists (for alphanumeric cluster IDs)
-- ALTER TABLE cluster ADD COLUMN IF NOT EXISTS cluster_id VARCHAR(50) NULL AFTER name;
