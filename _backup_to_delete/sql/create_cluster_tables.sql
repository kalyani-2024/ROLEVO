-- Create missing cluster-related tables for PythonAnywhere

-- Create roleplay_cluster table
CREATE TABLE IF NOT EXISTS roleplay_cluster (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    cluster_id VARCHAR(100),
    type VARCHAR(50) DEFAULT 'assessment',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_cluster_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Create cluster_roleplay junction table (links roleplays to clusters)
-- Note: roleplay_id must match roleplay.id type (VARCHAR(100))
CREATE TABLE IF NOT EXISTS cluster_roleplay (
    cluster_id INT NOT NULL,
    roleplay_id VARCHAR(100) NOT NULL,
    order_sequence INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (cluster_id, roleplay_id),
    FOREIGN KEY (cluster_id) REFERENCES roleplay_cluster(id) ON DELETE CASCADE,
    FOREIGN KEY (roleplay_id) REFERENCES roleplay(id) ON DELETE CASCADE,
    INDEX idx_cluster_id (cluster_id),
    INDEX idx_roleplay_id (roleplay_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Create user_cluster junction table (links users to clusters)
CREATE TABLE IF NOT EXISTS user_cluster (
    user_id INT NOT NULL,
    cluster_id INT NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, cluster_id),
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (cluster_id) REFERENCES roleplay_cluster(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_cluster_id (cluster_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Remove separate index creation since they're now in the CREATE TABLE statements

-- Add is_admin column to user table if it doesn't exist
ALTER TABLE user 
ADD COLUMN IF NOT EXISTS is_admin TINYINT(1) DEFAULT 0;

-- Add scenario_file_path and logo_path columns to roleplay table if they don't exist
ALTER TABLE roleplay 
ADD COLUMN IF NOT EXISTS scenario_file_path VARCHAR(500) DEFAULT '',
ADD COLUMN IF NOT EXISTS logo_path VARCHAR(500) DEFAULT '';
