-- Create missing cluster-related tables for PythonAnywhere
-- Simple version without constraints first, then add them

-- Step 1: Create roleplay_cluster table
DROP TABLE IF EXISTS user_cluster;
DROP TABLE IF EXISTS cluster_roleplay;
DROP TABLE IF EXISTS roleplay_cluster;

CREATE TABLE roleplay_cluster (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    cluster_id VARCHAR(100),
    type VARCHAR(50) DEFAULT 'assessment',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Step 2: Create cluster_roleplay junction table
-- roleplay_id MUST be VARCHAR(100) to match roleplay.id
CREATE TABLE cluster_roleplay (
    cluster_id INT NOT NULL,
    roleplay_id VARCHAR(100) NOT NULL,
    order_sequence INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (cluster_id, roleplay_id)
);

-- Step 3: Create user_cluster junction table
CREATE TABLE user_cluster (
    user_id INT NOT NULL,
    cluster_id INT NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, cluster_id)
);

-- Step 4: Add foreign keys (if they fail, tables will still work)
ALTER TABLE cluster_roleplay 
ADD CONSTRAINT fk_cluster_roleplay_cluster 
FOREIGN KEY (cluster_id) REFERENCES roleplay_cluster(id) ON DELETE CASCADE;

ALTER TABLE cluster_roleplay 
ADD CONSTRAINT fk_cluster_roleplay_roleplay 
FOREIGN KEY (roleplay_id) REFERENCES roleplay(id) ON DELETE CASCADE;

ALTER TABLE user_cluster 
ADD CONSTRAINT fk_user_cluster_user 
FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE;

ALTER TABLE user_cluster 
ADD CONSTRAINT fk_user_cluster_cluster 
FOREIGN KEY (cluster_id) REFERENCES roleplay_cluster(id) ON DELETE CASCADE;

-- Step 5: Add indexes for performance
CREATE INDEX idx_cluster_roleplay_cluster ON cluster_roleplay(cluster_id);
CREATE INDEX idx_cluster_roleplay_roleplay ON cluster_roleplay(roleplay_id);
CREATE INDEX idx_user_cluster_user ON user_cluster(user_id);
CREATE INDEX idx_user_cluster_cluster ON user_cluster(cluster_id);

-- Step 6: Add missing columns to existing tables
ALTER TABLE user ADD COLUMN is_admin TINYINT(1) DEFAULT 0;
ALTER TABLE roleplay ADD COLUMN scenario_file_path VARCHAR(500) DEFAULT '';
ALTER TABLE roleplay ADD COLUMN logo_path VARCHAR(500) DEFAULT '';
