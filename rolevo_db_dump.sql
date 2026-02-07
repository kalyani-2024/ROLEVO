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
-- Dumping data for table `chathistory`
--

LOCK TABLES `chathistory` WRITE;
/*!40000 ALTER TABLE `chathistory` DISABLE KEYS */;
INSERT INTO `chathistory` VALUES (1034,345,'ok liam thats great to hear','Others nod\nBheem(M): Yes Sir. Doing good. I\'ve launched the scheme we discussed.\nSatyam(M): All okay Sir. As always, Kevin has asked me to check about his promotion.',0,NULL,'2026-01-18 16:58:39'),(1035,345,'great good to hear that','The team seems concerned and starts glancing at each other.',0,NULL,'2026-01-18 16:59:55'),(1036,345,'okay im afraid i have some terrible news for the team','Bheem(M): But we have been trying. First we did not get enough support for scheme approval.\nSatyam(M): Right. And how many emails we have sent to Head office for approval, then they expect us to perform!\nShiv(M): I\'ve also been trying to turnaround my location Sir.',0,NULL,'2026-01-18 17:00:18'),(1037,346,'hi all how are you','Others nod.\nBheem(M): All okay Sir. Dealers are excited about the new scheme. I see good improvement in numbers \nSatyam(M): I\'m ok Sir. Kevin as usual is not! He asked me to check with you about this promotion.',0,NULL,'2026-01-18 18:15:04'),(1038,346,'im afraid i have some bad news','The team members exchange worried glances with each other.',0,NULL,'2026-01-18 18:15:39'),(1039,346,'so as you know we have found some issues within our territories evidences of fraud','Bheem(M): But we have been trying. First we did not get enough support for scheme approval.\nSatyam(M): Right. And how many emails we have sent to Head office for approval, then they expect us to perform!\nShiv(M): I\'ve also been trying to turnaround my location Sir.',0,NULL,'2026-01-18 18:16:14'),(1040,346,'okay i see','Bheem(M): Sir, how is fraud something we can prevent? That is the job of the Fraud control unit.\nSatyam(M): Yes, and we have been trying - you know the problems we have had with no response from Head office earlier.',0,NULL,'2026-01-18 18:16:54'),(1041,346,'but stuff keeps happening and we have to fix it or find solution to it','Bheem(M): So then Sir, you have to communicate this for us, please. We are not at fault.\nSatyam(M): Yes Sir, we are really trying and with your support it is only a matter of a month or two before we meet all our targets\nKaran(M) (quietly): Sir, may I ask why are you telling us this?',0,NULL,'2026-01-18 18:18:01'),(1042,347,'ok everyone i have some bad news','Others nod\nBheem(M): Yes Sir. Doing good. I\'ve launched the scheme we discussed.\nSatyam(M): All okay Sir. As always, Kevin has asked me to check about his promotion.',0,NULL,'2026-01-18 18:48:55'),(1043,347,'ok kevin is not getting promotion','Everyone seems concerned and exchanges glances with each other.',0,NULL,'2026-01-18 18:49:20'),(1044,347,'what happened whats up with the mood','Bheem(M): But we have been trying. First we did not get enough support for scheme approval.\nSatyam(M): Right. And how many emails we have sent to Head office for approval, then they expect us to perform!\nShiv(M): I\'ve also been trying to turnaround my location Sir.',0,NULL,'2026-01-18 18:49:38'),(1045,348,'ok so i have news for the team','Others nod\nBheem(M): Yes Sir. Doing good. I\'ve launched the scheme we discussed.\nSatyam(M): All okay Sir. As always, Kevin has asked me to check about his promotion.',0,NULL,'2026-01-18 18:53:50'),(1046,348,'theres no promotion for kevin so now moving on to the topic','The team seems concerned and starts glancing at each other.',0,NULL,'2026-01-18 18:54:15'),(1047,348,'ok team lets cheerup but i have bad news. company has been facing fraud issues','Bheem(M): But we have been trying. First we did not get enough support for scheme approval.\nSatyam(M): Right. And how many emails we have sent to Head office for approval, then they expect us to perform!\nShiv(M): I\'ve also been trying to turnaround my location Sir.',0,NULL,'2026-01-18 18:54:41'),(1048,348,'okay i understand','Bheem(M): Sir, how is fraud something we can prevent? That is the job of the Fraud control unit.\nSatyam(M): Yes, and we have been trying - you know the problems we have had with no response from Head office earlier.',0,NULL,'2026-01-18 18:55:32'),(1049,348,'but we need to deal with this issue fraud is smthg we need to control','Bheem(M): So then Sir, you have to communicate this for us, please. We are not at fault.\nSatyam(M): Yes Sir, we are really trying and with your support it is only a matter of a month or two before we meet all our targets\nKaran(M) (quietly): Sir, may I ask why are you telling us this?',0,NULL,'2026-01-18 18:56:04'),(1050,348,'i need to talk with the team, after all we are one aren\'t we... I need to build strong support system within the company and thats why i thought discussing with the team and brainstorming solutions could be enough to tackle this issue','Shiv(M): So what are you trying to say Sir?\nKaran(M) (very softly as if to himself): I think this is really bad news.',0,NULL,'2026-01-18 18:57:48'),(1051,348,'yes it is very bad','Bheem(M): Oh that is such good news! I drove all this way through the night for this! You could have just told us this on a concall.\nSatyam(M) (panicking): I am the only earning member of my family! How will I make it work! \nPaul(M): We know what is going to happen next Sir. With only 2 locations left, I\'m sure it will be our turn next!',0,NULL,'2026-01-18 18:58:08'),(1052,349,'ok team lets hear it','Others nod\nBheem(M): Yes Sir. Doing good. I\'ve launched the scheme we discussed.\nSatyam(M): All okay Sir. As always, Kevin has asked me to check about his promotion.',0,NULL,'2026-01-18 19:06:15'),(1053,349,'Kevin my mate, i will consider his promotion before that i have some bad news to share with you all, as you know our team has been facing some challenges','The team nods in understanding.',0,NULL,'2026-01-18 19:07:08'),(1054,349,'okay team whats the matter','Bheem(M): But we have been trying. First we did not get enough support for scheme approval.\nSatyam(M): Right. And how many emails we have sent to Head office for approval, then they expect us to perform!\nShiv(M): I\'ve also been trying to turnaround my location Sir.',0,NULL,'2026-01-18 19:07:24'),(1055,349,'ill speak with the board but right now we have to solve this','Bheem(M): Sir, how is fraud something we can prevent? That is the job of the Fraud control unit.\nSatyam(M): Yes, and we have been trying - you know the problems we have had with no response from Head office earlier.',0,NULL,'2026-01-18 19:09:37'),(1056,349,'That is the job of the Fraud control unit.','Bheem(M): So then Sir, you have to communicate this for us, please. We are not at fault.\nSatyam(M): Yes Sir, we are really trying and with your support it is only a matter of a month or two before we meet all our targets\nKaran(M) (quietly): Sir, may I ask why are you telling us this?',0,NULL,'2026-01-18 19:10:00'),(1057,349,'we are a team and i thought you all shud know','Shiv(M): So what are you trying to say Sir?\nKaran(M) (very softly as if to himself): I think this is really bad news.',0,NULL,'2026-01-18 19:10:38'),(1058,349,'I think this is really bad news.','Bheem(M): Oh that is such good news! I drove all this way through the night for this! You could have just told us this on a concall.\nSatyam(M) (panicking): I am the only earning member of my family! How will I make it work! \nPaul(M): We know what is going to happen next Sir. With only 2 locations left, I\'m sure it will be our turn next!',0,NULL,'2026-01-18 19:13:43'),(1059,349,'e know what is going to happen next Sir. With only 2 locations left, I\'m sure it will be our turn next!','Bheem(M): But it is very very unfair Sir. You tell me, you know the issues. We had such low support earlier. Only after you joined have we started getting the clearances faster!\nShiv(M): And I just quit a job where I was doing well and joined here a few months ago!\nSatyam(M): How will I manage my life? How will I pay the loan I just took for my father\'s hospitalisation?',0,NULL,'2026-01-18 19:15:47'),(1060,349,'okay i get it','Satyam(M): How can anyone solve my loan issue?\nBheem(M): I feel stupid to not have taken that offer.\nShiv(M): My team will struggle emotionally and will be demotivated.',0,NULL,'2026-01-18 19:20:03'),(1061,350,'ok team lets hear it','Others nod\nBheem(M): Yes Sir. Doing good. I\'ve launched the scheme we discussed.\nSatyam(M): All okay Sir. As always, Kevin has asked me to check about his promotion.',0,NULL,'2026-01-19 20:40:49'),(1062,351,'good morning to one and all. hows everyone doing.','Others nod.\nBheem(M): All okay Sir. Dealers are excited about the new scheme. I see good improvement in numbers \nSatyam(M): I\'m ok Sir. Kevin as usual is not! He asked me to check with you about this promotion.',0,NULL,'2026-01-19 20:43:12'),(1063,351,'kevin isnt getting a promotion and im afraid i have even sadder news','The team is visibly concerned and exchanging glances with each other.',0,NULL,'2026-01-19 20:43:57'),(1064,351,'alright team dont panick but as you know we have been facing challenges and there have been instances of fraud within company because of which records are all over the place','Bheem(M): But we have been trying. First we did not get enough support for scheme approval.\nSatyam(M): Right. And how many emails we have sent to Head office for approval, then they expect us to perform!\nShiv(M): I\'ve also been trying to turnaround my location Sir.',0,NULL,'2026-01-19 20:45:14'),(1065,351,'hmm i understand but company has been facing several issues and we need to fix it hightime','Bheem(M): Sir, how is fraud something we can prevent? That is the job of the Fraud control unit.\nSatyam(M): Yes, and we have been trying - you know the problems we have had with no response from Head office earlier.',0,NULL,'2026-01-19 20:47:24'),(1066,351,'but there has been reports and we need to fix this issue asap somehow we need  to take crtitcal mitigation strategeies to makeup for the revenue leak','Bheem(M): So then Sir, you should have communicated this to us. We are not at fault.\nSatyam(M): Yes Sir, we are trying and with your support, it is only a matter of a month or two before we meet all our targets\nKaran(M) (quietly): Sir, may I ask why are you telling us this?',0,NULL,'2026-01-19 20:48:41'),(1067,351,'i thought we all shud know because we are one team','Shiv(M): So what are you trying to say Sir?\nKaran(M) (very softly as if to himself): I think this is really bad news.',0,NULL,'2026-01-19 20:49:37'),(1068,351,'yes it is and its hightime to fix','Bheem(M): Oh that is such good news! I drove all this way through the night for this! You could have just told us this on a concall.\nSatyam(M) (panicking): I am the only earning member of my family! How will I make it work! \nPaul(M): We know what is going to happen next Sir. With only 2 locations left, I\'m sure it will be our turn next!',0,NULL,'2026-01-19 20:50:00'),(1069,351,'we know what is going to happen next Sir','Bheem(M): But it is very very unfair Sir. You tell me, you know the issues. We had such low support earlier. Only after you joined have we started getting the clearances faster!\nShiv(M): And I just quit a job where I was doing well and joined here a few months ago!\nSatyam(M): How will I manage my life? How will I pay the loan I just took for my father\'s hospitalisation?',0,NULL,'2026-01-19 20:56:00');
/*!40000 ALTER TABLE `chathistory` ENABLE KEYS */;
UNLOCK TABLES;

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
-- Dumping data for table `cluster_roleplay`
--

LOCK TABLES `cluster_roleplay` WRITE;
/*!40000 ALTER TABLE `cluster_roleplay` DISABLE KEYS */;
INSERT INTO `cluster_roleplay` VALUES (15,'RP_6LQOPP89',1),(15,'RP_UE8YNKJN',2);
/*!40000 ALTER TABLE `cluster_roleplay` ENABLE KEYS */;
UNLOCK TABLES;

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
-- Dumping data for table `pf16_analysis_results`
--

LOCK TABLES `pf16_analysis_results` WRITE;
/*!40000 ALTER TABLE `pf16_analysis_results` DISABLE KEYS */;
/*!40000 ALTER TABLE `pf16_analysis_results` ENABLE KEYS */;
UNLOCK TABLES;

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
-- Dumping data for table `play`
--

LOCK TABLES `play` WRITE;
/*!40000 ALTER TABLE `play` DISABLE KEYS */;
INSERT INTO `play` VALUES (345,'2026-01-18 22:27:53',NULL,5,'RP_UE8YNKJN',15,1,0,'ongoing',0),(346,'2026-01-18 23:44:19',NULL,5,'RP_UE8YNKJN',15,1,0,'ongoing',0),(347,'2026-01-19 00:18:26',NULL,5,'RP_UE8YNKJN',15,1,0,'ongoing',0),(348,'2026-01-19 00:23:16',NULL,5,'RP_UE8YNKJN',15,1,0,'ongoing',0),(349,'2026-01-19 00:35:47',NULL,5,'RP_UE8YNKJN',15,1,0,'ongoing',0),(350,'2026-01-20 02:09:50',NULL,6,'RP_UE8YNKJN',15,1,0,'ongoing',0),(351,'2026-01-20 02:12:30',NULL,6,'RP_UE8YNKJN',15,1,0,'ongoing',0),(352,'2026-01-20 02:37:25',NULL,5,'RP_UE8YNKJN',15,1,0,'ongoing',0);
/*!40000 ALTER TABLE `play` ENABLE KEYS */;
UNLOCK TABLES;

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
-- Dumping data for table `roleplay`
--

LOCK TABLES `roleplay` WRITE;
/*!40000 ALTER TABLE `roleplay` DISABLE KEYS */;
INSERT INTO `roleplay` VALUES ('RP_6LQOPP89','security review','C:\\Users\\lenovo\\OneDrive\\Desktop\\Rolevo-flaskapp-firas\\Rolevo-flaskapp-firas\\data\\roleplay\\temp_1768914330_1768914330_Obj handling-Distributor_melwyn.xls','C:\\Users\\lenovo\\OneDrive\\Desktop\\Rolevo-flaskapp-firas\\Rolevo-flaskapp-firas\\data\\images\\temp_1768914330_1768914330_Flavia test RP with images.xls','C:\\Users\\lenovo\\OneDrive\\Desktop\\Rolevo-flaskapp-firas\\Rolevo-flaskapp-firas\\data\\master\\temp_1768914330_1768914330_CompetencyMaster 22072022 (1).xlsx','<p>okay required</p>','security auditor','2026-01-20 13:05:31','2026-01-20 13:05:31','',''),('RP_UE8YNKJN','team testing for jan 12th audio big title','C:\\Users\\lenovo\\OneDrive\\Desktop\\Rolevo-flaskapp-firas\\Rolevo-flaskapp-firas\\data\\roleplay\\temp_1768755441_1768755441_TVS RP2 - Team meeting-multiparty (1).xls','C:\\Users\\lenovo\\OneDrive\\Desktop\\Rolevo-flaskapp-firas\\Rolevo-flaskapp-firas\\data\\images\\temp_1768755441_1768755441_Flavia test RP with images.xls','C:\\Users\\lenovo\\OneDrive\\Desktop\\Rolevo-flaskapp-firas\\Rolevo-flaskapp-firas\\data\\master\\temp_1768755441_1768755441_CompetencyMaster 22072022 (1).xlsx','<p>team</p>','team ','2026-01-18 16:57:22','2026-01-20 12:50:04','','');
/*!40000 ALTER TABLE `roleplay` ENABLE KEYS */;
UNLOCK TABLES;

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
-- Dumping data for table `roleplay_cluster`
--

LOCK TABLES `roleplay_cluster` WRITE;
/*!40000 ALTER TABLE `roleplay_cluster` DISABLE KEYS */;
INSERT INTO `roleplay_cluster` VALUES (15,'elevenlabs','1a7a3499-c2c','training','2026-01-18 16:57:43','2026-01-18 16:57:43');
/*!40000 ALTER TABLE `roleplay_cluster` ENABLE KEYS */;
UNLOCK TABLES;

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
-- Dumping data for table `roleplay_config`
--

LOCK TABLES `roleplay_config` WRITE;
/*!40000 ALTER TABLE `roleplay_config` DISABLE KEYS */;
INSERT INTO `roleplay_config` VALUES (78,'RP_UE8YNKJN','text',3,'[\"English\"]',300,1800,1,'last',0,'',0,'easy',0,'persona360',1,1,30,0,'2026-01-18 16:57:22','2026-01-20 12:50:04'),(79,'RP_6LQOPP89','audio',3,'[\"English\"]',300,1800,1,'last',0,'',0,'easy',1,'persona360',1,1,30,0,'2026-01-20 13:05:31','2026-01-20 13:05:31');
/*!40000 ALTER TABLE `roleplay_config` ENABLE KEYS */;
UNLOCK TABLES;

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
-- Dumping data for table `roleplayoverride`
--

LOCK TABLES `roleplayoverride` WRITE;
/*!40000 ALTER TABLE `roleplayoverride` DISABLE KEYS */;
/*!40000 ALTER TABLE `roleplayoverride` ENABLE KEYS */;
UNLOCK TABLES;

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
-- Dumping data for table `scorebreakdown`
--

LOCK TABLES `scorebreakdown` WRITE;
/*!40000 ALTER TABLE `scorebreakdown` DISABLE KEYS */;
INSERT INTO `scorebreakdown` VALUES (3527,1026,'Creating/Sustaining Relationships Leve 2',1),(3528,1027,'Creating/Sustaining Relationships Leve 2',1),(3529,1027,'Dealing with ambiguity Level 2',1),(3530,1028,'Maturity to Communicate across org level Level 2',1),(3531,1028,'Dealing with ambiguity Level 2',1),(3532,1029,'Creating/Sustaining Relationships Leve 2',2),(3533,1030,'Creating/Sustaining Relationships Leve 2',1),(3534,1030,'Dealing with ambiguity Level 2',1),(3535,1031,'Maturity to Communicate across org level Level 2',1),(3536,1031,'Dealing with ambiguity Level 2',1),(3537,1032,'Maturity to Communicate across org level Level 2',1),(3538,1032,'Dealing with ambiguity Level 2',1),(3539,1033,'Maturity to Communicate across org level Level 2',1),(3540,1033,'Dealing with ambiguity Level 2',1),(3541,1034,'Creating/Sustaining Relationships Leve 2',1),(3542,1035,'Dealing with ambiguity Level 2',1),(3543,1035,'Creating/Sustaining Relationships Leve 2',1),(3544,1036,'Maturity to Communicate across org level Level 2',1),(3545,1036,'Dealing with ambiguity Level 2',1),(3546,1037,'Creating/Sustaining Relationships Leve 2',1),(3547,1038,'Creating/Sustaining Relationships Leve 2',1),(3548,1038,'Dealing with ambiguity Level 2',1),(3549,1039,'Dealing with ambiguity Level 2',1),(3550,1039,'Maturity to Communicate across org level Level 2',1),(3551,1040,'Dealing with ambiguity Level 2',1),(3552,1040,'Maturity to Communicate across org level Level 2',1),(3553,1041,'Dealing with ambiguity Level 2',1),(3554,1041,'Maturity to Communicate across org level Level 2',1),(3555,1042,'Maturity to Communicate across org level Level 2',2),(3556,1043,'Partnership Approach Level 2',1),(3557,1043,'Creating/Sustaining Relationships Leve 2',1),(3558,1044,'Creating/Sustaining Relationships Leve 2',1),(3559,1045,'Creating/Sustaining Relationships Leve 2',3),(3560,1045,'Dealing with ambiguity Level 2',3),(3561,1046,'Maturity to Communicate across org level Level 2',1),(3562,1046,'Dealing with ambiguity Level 2',1),(3563,1047,'Maturity to Communicate across org level Level 2',1),(3564,1047,'Dealing with ambiguity Level 2',1),(3565,1048,'Maturity to Communicate across org level Level 2',1),(3566,1048,'Dealing with ambiguity Level 2',1),(3567,1049,'Maturity to Communicate across org level Level 2',1),(3568,1050,'Creating/Sustaining Relationships Leve 2',1),(3569,1050,'Partnership Approach Level 2',1),(3570,1051,'Creating/Sustaining Relationships Leve 2',1),(3571,1051,'Maturity to Communicate across org level Level 2',1),(3572,1052,'Maturity to Communicate across org level Level 2',1),(3573,1052,'Learning agility level 2',1),(3574,1053,'Creating/Sustaining Relationships Leve 2',1),(3575,1054,'Creating/Sustaining Relationships Leve 2',2),(3576,1055,'Creating/Sustaining Relationships Leve 2',1),(3577,1055,'Dealing with ambiguity Level 2',1),(3578,1056,'Dealing with ambiguity Level 2',1),(3579,1056,'Maturity to Communicate across org level Level 2',1),(3580,1057,'Dealing with ambiguity Level 2',1),(3581,1057,'Maturity to Communicate across org level Level 2',1),(3582,1058,'Dealing with ambiguity Level 2',2),(3583,1058,'Maturity to Communicate across org level Level 2',2),(3584,1059,'Maturity to Communicate across org level Level 2',1),(3585,1060,'Creating/Sustaining Relationships Leve 2',1),(3586,1060,'Partnership Approach Level 2',1),(3587,1061,'Creating/Sustaining Relationships Leve 2',1),(3588,1061,'Maturity to Communicate across org level Level 2',1);
/*!40000 ALTER TABLE `scorebreakdown` ENABLE KEYS */;
UNLOCK TABLES;

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
-- Dumping data for table `scoremaster`
--

LOCK TABLES `scoremaster` WRITE;
/*!40000 ALTER TABLE `scoremaster` DISABLE KEYS */;
INSERT INTO `scoremaster` VALUES (1026,1034,1,'2026-01-18 16:58:39'),(1027,1035,1,'2026-01-18 16:59:55'),(1028,1036,1,'2026-01-18 17:00:18'),(1029,1037,2,'2026-01-18 18:15:04'),(1030,1038,1,'2026-01-18 18:15:39'),(1031,1039,1,'2026-01-18 18:16:14'),(1032,1040,1,'2026-01-18 18:16:54'),(1033,1041,1,'2026-01-18 18:18:01'),(1034,1042,1,'2026-01-18 18:48:55'),(1035,1043,1,'2026-01-18 18:49:20'),(1036,1044,1,'2026-01-18 18:49:38'),(1037,1045,1,'2026-01-18 18:53:50'),(1038,1046,1,'2026-01-18 18:54:15'),(1039,1047,1,'2026-01-18 18:54:41'),(1040,1048,1,'2026-01-18 18:55:32'),(1041,1049,1,'2026-01-18 18:56:04'),(1042,1050,2,'2026-01-18 18:57:48'),(1043,1051,1,'2026-01-18 18:58:08'),(1044,1052,1,'2026-01-18 19:06:15'),(1045,1053,3,'2026-01-18 19:07:08'),(1046,1054,1,'2026-01-18 19:07:24'),(1047,1055,1,'2026-01-18 19:09:37'),(1048,1056,1,'2026-01-18 19:10:00'),(1049,1057,1,'2026-01-18 19:10:38'),(1050,1058,1,'2026-01-18 19:13:43'),(1051,1059,1,'2026-01-18 19:15:47'),(1052,1060,1,'2026-01-18 19:20:03'),(1053,1061,1,'2026-01-19 20:40:49'),(1054,1062,2,'2026-01-19 20:43:12'),(1055,1063,1,'2026-01-19 20:43:57'),(1056,1064,1,'2026-01-19 20:45:14'),(1057,1065,1,'2026-01-19 20:47:24'),(1058,1066,2,'2026-01-19 20:48:41'),(1059,1067,1,'2026-01-19 20:49:37'),(1060,1068,1,'2026-01-19 20:50:00'),(1061,1069,1,'2026-01-19 20:56:00');
/*!40000 ALTER TABLE `scoremaster` ENABLE KEYS */;
UNLOCK TABLES;

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
-- Dumping data for table `user`
--

LOCK TABLES `user` WRITE;
/*!40000 ALTER TABLE `user` DISABLE KEYS */;
INSERT INTO `user` VALUES (1,'admin@example.com','$2b$12$aAPWFutjUsXhVqvuDzGNde4EDBTwOuTry0CdlM37JVT4h/ZmgW7h2',1),(2,'trajectorie@example.com','1234',1),(3,'f20230236@dubai.bits-pilani.ac.in','$2b$12$OnnD9imbBJMNUNmcUF3dp.76Lh8A0K9cCYCmqubuEjHWLLsFF8b3y',0),(4,'trajectorie@admin.com','$2b$12$7aYw0bRv.PMcpcf2cw0FSuWEaDD3u6mpOjvR1g4ZriRUitQsFBEh2',1),(5,'kalyanibaijusindhu@gmail.com','$2b$12$WvNGdva833UyQecrEdi.NOHakCWOW1qh9AK0JtPvexRy1DtuEf2XC',0),(6,'admin@gmail.com','$2b$12$rP1FrVsmOT3HIzEwBzeVbeHWleFc1NNi6RxgHSAW5GoKl1Ex12ITK',0);
/*!40000 ALTER TABLE `user` ENABLE KEYS */;
UNLOCK TABLES;

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
-- Dumping data for table `user_cluster`
--

LOCK TABLES `user_cluster` WRITE;
/*!40000 ALTER TABLE `user_cluster` DISABLE KEYS */;
INSERT INTO `user_cluster` VALUES (49,5,15,'2026-01-18 16:57:43'),(51,6,15,'2026-01-19 20:35:29');
/*!40000 ALTER TABLE `user_cluster` ENABLE KEYS */;
UNLOCK TABLES;

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

-- Dump completed on 2026-01-20 20:48:52
