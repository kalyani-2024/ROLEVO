-- MySQL dump 10.13  Distrib 8.0.43, for Win64 (x86_64)
--
-- Host: localhost    Database: roleplay
-- ------------------------------------------------------
-- Server version	8.0.43

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `chathistory`
--

DROP TABLE IF EXISTS `chathistory`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `chathistory` (
  `id` int NOT NULL AUTO_INCREMENT,
  `play_id` int NOT NULL,
  `user_text` varchar(2500) DEFAULT NULL,
  `response_text` varchar(2500) DEFAULT NULL,
  `interaction_time` int DEFAULT '0',
  `audio_file_path` varchar(500) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `play_id` (`play_id`),
  CONSTRAINT `chathistory_ibfk_1` FOREIGN KEY (`play_id`) REFERENCES `play` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1070 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cluster_roleplay`
--

DROP TABLE IF EXISTS `cluster_roleplay`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cluster_roleplay` (
  `cluster_id` int NOT NULL,
  `roleplay_id` varchar(100) NOT NULL,
  `order_sequence` int DEFAULT '1',
  PRIMARY KEY (`cluster_id`,`roleplay_id`),
  KEY `roleplay_id` (`roleplay_id`),
  CONSTRAINT `cluster_roleplay_ibfk_1` FOREIGN KEY (`cluster_id`) REFERENCES `roleplay_cluster` (`id`) ON DELETE CASCADE,
  CONSTRAINT `cluster_roleplay_ibfk_2` FOREIGN KEY (`roleplay_id`) REFERENCES `roleplay` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `pf16_analysis_results`
--

DROP TABLE IF EXISTS `pf16_analysis_results`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `pf16_analysis_results` (
  `id` int NOT NULL AUTO_INCREMENT,
  `play_id` int NOT NULL,
  `user_id` int DEFAULT NULL,
  `roleplay_id` varchar(100) DEFAULT NULL,
  `audio_file_path` varchar(500) DEFAULT NULL,
  `analysis_source` varchar(50) DEFAULT 'persona360',
  `user_age` int DEFAULT NULL,
  `user_gender` varchar(20) DEFAULT NULL,
  `raw_response` json DEFAULT NULL,
  `personality_scores` json DEFAULT NULL,
  `composite_scores` json DEFAULT NULL,
  `overall_role_fit` decimal(5,2) DEFAULT NULL,
  `analysis_confidence` decimal(5,2) DEFAULT NULL,
  `status` enum('pending','processing','completed','failed') DEFAULT 'pending',
  `error_message` text,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `completed_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `play_id` (`play_id`),
  CONSTRAINT `pf16_analysis_results_ibfk_1` FOREIGN KEY (`play_id`) REFERENCES `play` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=22 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `play`
--

DROP TABLE IF EXISTS `play`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `play` (
  `id` int NOT NULL AUTO_INCREMENT,
  `start_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `end_time` datetime DEFAULT NULL,
  `user_id` int NOT NULL,
  `roleplay_id` varchar(100) NOT NULL,
  `cluster_id` int DEFAULT NULL,
  `attempt_number` int DEFAULT '1',
  `total_time_spent` int DEFAULT '0',
  `status` enum('ongoing','completed','abandoned') DEFAULT 'ongoing',
  `viewed_optimal` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `roleplay_id` (`roleplay_id`),
  KEY `cluster_id` (`cluster_id`),
  CONSTRAINT `play_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`),
  CONSTRAINT `play_ibfk_2` FOREIGN KEY (`roleplay_id`) REFERENCES `roleplay` (`id`),
  CONSTRAINT `play_ibfk_3` FOREIGN KEY (`cluster_id`) REFERENCES `roleplay_cluster` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=353 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `roleplay`
--

DROP TABLE IF EXISTS `roleplay`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `roleplay` (
  `id` varchar(100) NOT NULL,
  `name` varchar(1000) NOT NULL,
  `file_path` varchar(500) NOT NULL,
  `image_file_path` varchar(500) NOT NULL,
  `competency_file_path` varchar(500) DEFAULT NULL,
  `scenario` varchar(2000) NOT NULL,
  `person_name` varchar(1000) NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `scenario_file_path` varchar(500) DEFAULT NULL,
  `logo_path` varchar(500) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `roleplay_cluster`
--

DROP TABLE IF EXISTS `roleplay_cluster`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `roleplay_cluster` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(1000) NOT NULL,
  `cluster_id` varchar(100) NOT NULL,
  `type` enum('assessment','training') NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `cluster_id` (`cluster_id`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `roleplay_config`
--

DROP TABLE IF EXISTS `roleplay_config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `roleplay_config` (
  `id` int NOT NULL AUTO_INCREMENT,
  `roleplay_id` varchar(100) NOT NULL,
  `input_type` enum('audio','text') DEFAULT 'text',
  `audio_rerecord_attempts` int DEFAULT '3',
  `available_languages` json DEFAULT NULL,
  `max_interaction_time` int DEFAULT '300',
  `max_total_time` int DEFAULT '1800',
  `repeat_attempts_allowed` int DEFAULT '1',
  `score_type` enum('best','last') DEFAULT 'last',
  `show_ideal_video` tinyint(1) DEFAULT '0',
  `ideal_video_path` varchar(500) DEFAULT NULL,
  `voice_assessment_enabled` tinyint(1) DEFAULT '0',
  `difficulty_level` enum('easy','medium','hard') DEFAULT 'easy',
  `enable_16pf_analysis` tinyint(1) DEFAULT '0',
  `pf16_analysis_source` enum('none','persona360','third_party') DEFAULT 'none',
  `pf16_user_age_required` tinyint(1) DEFAULT '1',
  `pf16_user_gender_required` tinyint(1) DEFAULT '1',
  `pf16_default_age` int DEFAULT '30',
  `pf16_send_audio_for_analysis` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `roleplay_id` (`roleplay_id`),
  CONSTRAINT `roleplay_config_ibfk_1` FOREIGN KEY (`roleplay_id`) REFERENCES `roleplay` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=80 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `roleplayoverride`
--

DROP TABLE IF EXISTS `roleplayoverride`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `roleplayoverride` (
  `roleplay_id` varchar(100) NOT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`roleplay_id`,`user_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `roleplayoverride_ibfk_1` FOREIGN KEY (`roleplay_id`) REFERENCES `roleplay` (`id`) ON DELETE CASCADE,
  CONSTRAINT `roleplayoverride_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `scorebreakdown`
--

DROP TABLE IF EXISTS `scorebreakdown`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `scorebreakdown` (
  `id` int NOT NULL AUTO_INCREMENT,
  `scoremaster_id` int NOT NULL,
  `score_name` varchar(255) NOT NULL,
  `score` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `scoremaster_id` (`scoremaster_id`),
  CONSTRAINT `scorebreakdown_ibfk_1` FOREIGN KEY (`scoremaster_id`) REFERENCES `scoremaster` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3589 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `scoremaster`
--

DROP TABLE IF EXISTS `scoremaster`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `scoremaster` (
  `id` int NOT NULL AUTO_INCREMENT,
  `chathistory_id` int NOT NULL,
  `overall_score` int NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `chathistory_id` (`chathistory_id`),
  CONSTRAINT `scoremaster_ibfk_1` FOREIGN KEY (`chathistory_id`) REFERENCES `chathistory` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1062 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user`
--

DROP TABLE IF EXISTS `user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user` (
  `id` int NOT NULL AUTO_INCREMENT,
  `email` varchar(255) NOT NULL,
  `password` varchar(500) NOT NULL,
  `is_admin` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_cluster`
--

DROP TABLE IF EXISTS `user_cluster`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_cluster` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `cluster_id` int NOT NULL,
  `assigned_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_user_cluster` (`user_id`,`cluster_id`),
  KEY `cluster_id` (`cluster_id`),
  CONSTRAINT `user_cluster_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `user_cluster_ibfk_2` FOREIGN KEY (`cluster_id`) REFERENCES `roleplay_cluster` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=52 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping routines for database 'roleplay'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-01-20 20:54:39
