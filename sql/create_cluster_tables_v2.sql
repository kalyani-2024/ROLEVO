-- Create cluster tables without foreign key constraints
-- The foreign keys can fail if character sets don't match exactly
-- Tables will still work perfectly without them

-- Drop existing tables if they exist (be careful!)
DROP TABLE IF EXISTS user_cluster;
DROP TABLE IF EXISTS cluster_roleplay;
DROP TABLE IF EXISTS roleplay_cluster;

-- Create roleplay_cluster table
CREATE TABLE roleplay_cluster (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    cluster_id VARCHAR(100),
    type VARCHAR(50) DEFAULT 'assessment',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create cluster_roleplay table
-- Match the exact type, charset and collation of roleplay.id
CREATE TABLE cluster_roleplay (
    cluster_id INT NOT NULL,
    roleplay_id VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
    order_sequence INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (cluster_id, roleplay_id),
    KEY idx_cluster_id (cluster_id),
    KEY idx_roleplay_id (roleplay_id)
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create user_cluster table
CREATE TABLE user_cluster (
    user_id INT NOT NULL,
    cluster_id INT NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, cluster_id),
    KEY idx_user_id (user_id),
    KEY idx_cluster_id (cluster_id)
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Try to add foreign keys (if these fail, it's OK - tables will still work)
-- Try cluster_roleplay -> roleplay_cluster
ALTER TABLE cluster_roleplay 
ADD CONSTRAINT fk_cluster_roleplay_cluster 
FOREIGN KEY (cluster_id) REFERENCES roleplay_cluster(id) ON DELETE CASCADE;

-- Try cluster_roleplay -> roleplay (this might fail due to charset mismatch)
-- If it fails, the app will still work, just without enforced referential integrity
ALTER TABLE cluster_roleplay 
ADD CONSTRAINT fk_cluster_roleplay_roleplay 
FOREIGN KEY (roleplay_id) REFERENCES roleplay(id) ON DELETE CASCADE;

-- Try user_cluster -> user
ALTER TABLE user_cluster 
ADD CONSTRAINT fk_user_cluster_user 
FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE;

-- Try user_cluster -> roleplay_cluster
ALTER TABLE user_cluster 
ADD CONSTRAINT fk_user_cluster_cluster 
FOREIGN KEY (cluster_id) REFERENCES roleplay_cluster(id) ON DELETE CASCADE;

-- Verify tables were created
SELECT 'Tables created successfully!' as status;
SHOW TABLES LIKE '%cluster%';
