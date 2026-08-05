-- MySQL dump 10.13  Distrib 8.0.37, for Win64 (x86_64)
--
-- Host: localhost    Database: jie_bang
-- ------------------------------------------------------
-- Server version	8.0.37

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
-- Table structure for table `alembic_version`
--

DROP TABLE IF EXISTS `alembic_version`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `alembic_version` (
  `version_num` varchar(32) NOT NULL,
  PRIMARY KEY (`version_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `alembic_version`
--

LOCK TABLES `alembic_version` WRITE;
/*!40000 ALTER TABLE `alembic_version` DISABLE KEYS */;
INSERT INTO `alembic_version` VALUES ('34d9b68a59ff');
/*!40000 ALTER TABLE `alembic_version` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `favorite`
--

DROP TABLE IF EXISTS `favorite`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `favorite` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL COMMENT '用户ID',
  `item_type` varchar(30) NOT NULL COMMENT '收藏类型: position / learning_resource / quiz_error / knowledge_point',
  `item_id` varchar(100) NOT NULL COMMENT '对应类型的资源ID',
  `title` varchar(200) NOT NULL COMMENT '收藏项标题',
  `summary` varchar(500) DEFAULT NULL COMMENT '简要描述',
  `metadata` json NOT NULL COMMENT '完整数据快照',
  `tags` json DEFAULT NULL COMMENT '用户自定义标签',
  `created_at` datetime NOT NULL COMMENT '收藏时间',
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `ix_favorite_item_type` (`item_type`),
  CONSTRAINT `favorite_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `favorite`
--

LOCK TABLES `favorite` WRITE;
/*!40000 ALTER TABLE `favorite` DISABLE KEYS */;
INSERT INTO `favorite` VALUES (1,1,'position','4','Java 开发工程师','负责企业级后端系统设计与开发，当前趋势要求具备分布式、云原生和 AI 集成能力。','{\"name\": \"Java 开发工程师\", \"skills\": [\"Java / Spring Boot\", \"MySQL / Redis\", \"微服务架构\", \"Docker / K8s\"], \"category\": \"existing\", \"position_id\": 4, \"career_level\": \"mid\", \"salary_range\": \"15K-35K\"}',NULL,'2026-07-18 21:21:28'),(3,1,'learning_resource','res-1','《深入理解Java虚拟机》','Java性能调优必读经典','{\"url\": \"\", \"type\": \"book\", \"title\": \"《深入理解Java虚拟机》\", \"platform\": \"京东读书\", \"skill_tags\": [\"Java\", \"JVM\"], \"resource_id\": \"res-1\"}',NULL,'2026-07-18 21:21:28'),(4,1,'quiz_error','quiz-1','Java GC 算法选择','关于 CMS 和 G1 收集器的适用场景','{\"quiz_id\": \"quiz-1\", \"step_id\": \"s-1\", \"question\": \"在堆内存 4GB 以上时，JDK 9+ 默认使用哪个垃圾收集器？\", \"skill_name\": \"Java\", \"explanation\": \"JDK 9 开始 G1 成为默认垃圾收集器，适合大内存场景。\", \"user_answer\": \"CMS\", \"correct_answer\": \"G1\"}',NULL,'2026-07-18 21:21:28'),(6,1,'position','raw-101','算法软件工程师','机器视觉 智能驾驶 OpenCV 岗位职责： 研究ADAS产品相关知识，根据ADAS产品需求，完成需求规格说明书 根据需求规格说明书，完成详细设计 根据需求规格说明书、详细设计，完成项目软件开发 设计','{\"name\": \"算法软件工程师\", \"skills\": [\"算法\"], \"category\": \"new\", \"position_id\": \"raw-101\", \"career_level\": \"mid\", \"salary_range\": \"8000-13000元·13薪\"}','[]','2026-07-22 19:28:32');
/*!40000 ALTER TABLE `favorite` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `job_position`
--

DROP TABLE IF EXISTS `job_position`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `job_position` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL COMMENT '岗位名称',
  `category` varchar(20) NOT NULL COMMENT '岗位类型: new=新岗位, existing=既有岗位',
  `aliases` json NOT NULL COMMENT '岗位别名列表',
  `summary` text NOT NULL COMMENT '岗位概述',
  `responsibilities` json NOT NULL COMMENT '核心职责列表',
  `industry_scenarios` json NOT NULL COMMENT '典型行业应用场景',
  `tech_stack` json NOT NULL COMMENT '技术栈列表',
  `career_level` varchar(20) NOT NULL COMMENT '职业级别: junior/mid/senior',
  `salary_range` varchar(50) DEFAULT NULL COMMENT '薪资范围，如 15K-30K',
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `job_position`
--

LOCK TABLES `job_position` WRITE;
/*!40000 ALTER TABLE `job_position` DISABLE KEYS */;
INSERT INTO `job_position` VALUES (7,'AI 智能体开发工程师','new','[\"Agent开发工程师\", \"大模型Agent工程师\"]','负责基于大语言模型构建、部署和优化 AI 智能体（Agent）系统，涵盖工具调用、多步推理和自主决策能力。','[\"设计并实现 LLM-based Agent 架构，包括 ReAct、Plan-and-Solve 等范式\", \"构建 Agent 工具链（Tool Use / Function Calling）与记忆系统\", \"开发 Multi-Agent 协作框架，实现复杂任务的自动分解与协同\", \"持续跟踪 Agent 框架（LangGraph、AutoGen、CrewAI）的最新进展并评估集成\"]','[\"智能客服系统\", \"自动化运维Agent\", \"个人AI助理\", \"企业知识管理\"]','[\"AI框架\", \"编程语言\", \"AI技术\", \"数据存储\", \"后端开发\"]','mid','25K-50K','2026-08-01 19:19:49','2026-08-01 19:19:49'),(8,'上下文工程专家','new','[\"Context Engineering Specialist\", \"上下文优化工程师\"]','专注于 LLM 应用中的上下文管理策略，包括上下文窗口优化、记忆管理和信息检索策略设计。','[\"设计 LLM 应用的上下文管理架构，优化 token 利用率\", \"开发上下文压缩与信息蒸馏技术，提升长对话场景下的模型表现\", \"构建动态上下文注入策略，结合实时数据与历史对话\"]','[\"AI 产品公司\", \"大模型中间件\", \"对话系统优化\"]','[\"AI技术\", \"编程语言\", \"AI框架\"]','senior','30K-60K','2026-08-01 19:19:49','2026-08-01 19:19:49'),(9,'具身智能算法工程师','new','[\"Embodied AI Engineer\", \"机器人算法工程师\"]','研发具身智能系统，将大模型与机器人控制相结合，实现感知-决策-执行的闭环。','[\"研发机器人视觉感知与操作规划算法\", \"结合 VLM（视觉语言模型）实现机器人自主决策\", \"构建仿真环境（Isaac Sim）中的训练流程\"]','[\"工业机器人\", \"服务机器人\", \"自动驾驶\", \"仓储物流\"]','[\"编程语言\", \"机器人框架\", \"AI技术\", \"仿真平台\"]','senior','35K-70K','2026-08-01 19:19:49','2026-08-01 19:19:49'),(10,'Java 开发工程师','existing','[\"Java工程师\", \"Java开发\", \"Java后端\"]','负责企业级后端系统设计与开发，当前趋势要求具备分布式、云原生和 AI 集成能力。','[\"参与系统架构设计，编写高质量 Java 代码\", \"负责微服务架构的设计与治理\", \"参与 AI 能力的后端集成（如 RAG 接口、Agent 调用）\", \"持续优化系统性能与可观测性\"]','[\"金融科技\", \"电商平台\", \"企业SaaS\", \"互联网\"]','[\"编程语言\", \"数据存储\", \"架构设计\", \"云原生\", \"AI集成\", \"前端\"]','mid','15K-35K','2026-08-01 19:19:49','2026-08-01 19:19:49'),(11,'前端开发工程师','existing','[\"前端工程师\", \"Web前端\", \"H5开发\"]','负责 Web 前端架构与开发，当前趋势涵盖 AI 辅助开发工具集成和跨端开发能力。','[\"负责产品前端架构设计与核心模块开发\", \"优化首屏加载性能与运行时体验\", \"使用 AI 辅助工具（Copilot / Cursor）提升开发效率\"]','[\"互联网产品\", \"企业后台\", \"数据可视化\", \"移动端H5\"]','[\"编程语言\", \"前端框架\", \"构建工具\", \"AI工具\", \"全栈\", \"数据可视化\"]','mid','15K-30K','2026-08-01 19:19:49','2026-08-01 19:19:49'),(12,'数据工程师','existing','[\"大数据工程师\", \"Data Engineer\"]','负责数据平台建设与数据管道开发，当前趋势要求融合 AI/ML 工程化能力。','[\"构建和维护大规模数据处理管道（ETL/ELT）\", \"设计数据仓库与数据湖架构\", \"支撑 AI 模型的训练数据准备与特征工程\"]','[\"互联网数据平台\", \"金融风控\", \"AI 数据中台\"]','[\"编程语言\", \"大数据框架\", \"数据架构\", \"AI工程化\"]','mid','20K-40K','2026-08-01 19:19:49','2026-08-01 19:19:49');
/*!40000 ALTER TABLE `job_position` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `learning_path`
--

DROP TABLE IF EXISTS `learning_path`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `learning_path` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL COMMENT '用户ID',
  `name` varchar(100) NOT NULL COMMENT '路径名称',
  `position_id` int NOT NULL COMMENT '目标岗位ID',
  `position_name` varchar(100) NOT NULL COMMENT '目标岗位名称',
  `steps` json NOT NULL COMMENT '学习步骤列表',
  `total_duration` varchar(50) NOT NULL COMMENT '总学习时长，如 12周',
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `position_id` (`position_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `learning_path_ibfk_1` FOREIGN KEY (`position_id`) REFERENCES `job_position` (`id`),
  CONSTRAINT `learning_path_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `learning_path`
--

LOCK TABLES `learning_path` WRITE;
/*!40000 ALTER TABLE `learning_path` DISABLE KEYS */;
INSERT INTO `learning_path` VALUES (5,1,'Java工程师进阶路径',10,'Java 开发工程师','[{\"id\": \"s-1\", \"order\": 1, \"title\": \"Java 核心基础强化\", \"duration\": \"1-2周\", \"completed\": true, \"resources\": [{\"id\": \"res-1\", \"url\": \"\", \"type\": \"book\", \"title\": \"《深入理解Java虚拟机》\", \"platform\": \"京东读书\"}, {\"id\": \"res-2\", \"url\": \"\", \"type\": \"course\", \"title\": \"Java并发编程实战\", \"platform\": \"慕课网\"}], \"description\": \"深入理解 Java 集合框架、JVM 内存模型、并发编程\"}, {\"id\": \"s-2\", \"order\": 2, \"title\": \"Spring Boot 微服务实战\", \"duration\": \"3-5周\", \"completed\": false, \"resources\": [{\"id\": \"res-3\", \"url\": \"\", \"type\": \"project\", \"title\": \"Spring Cloud 微服务实战\", \"platform\": \"GitHub\"}, {\"id\": \"res-4\", \"url\": \"\", \"type\": \"book\", \"title\": \"微服务架构设计模式\", \"platform\": \"异步社区\"}], \"description\": \"掌握 Spring Cloud、服务注册与发现、网关、配置中心\"}, {\"id\": \"s-3\", \"order\": 3, \"title\": \"Docker & Kubernetes\", \"duration\": \"6-7周\", \"completed\": false, \"resources\": [{\"id\": \"res-5\", \"url\": \"\", \"type\": \"course\", \"title\": \"Kubernetes 入门到实践\", \"platform\": \"阿里云大学\"}], \"description\": \"容器化部署、K8s基础操作、Helm Charts\"}, {\"id\": \"s-4\", \"order\": 4, \"title\": \"LLM API 集成与 Agent 开发\", \"duration\": \"8-10周\", \"completed\": false, \"resources\": [{\"id\": \"res-6\", \"url\": \"\", \"type\": \"article\", \"title\": \"LangChain 实战指南\", \"platform\": \"掘金\"}, {\"id\": \"res-7\", \"url\": \"\", \"type\": \"video\", \"title\": \"RAG 从零到一\", \"platform\": \"B站\"}], \"description\": \"学习大模型 API 调用范式、RAG 系统搭建、LangChain 基础\"}, {\"id\": \"s-5\", \"order\": 5, \"title\": \"综合实战项目\", \"duration\": \"11-12周\", \"completed\": false, \"resources\": [{\"id\": \"res-8\", \"url\": \"\", \"type\": \"article\", \"title\": \"AI-Native 应用开发指南\", \"platform\": \"知乎专栏\"}], \"description\": \"使用 Java + Spring Boot + LLM 构建智能后端系统\"}]','12周','2026-08-01 19:19:49','2026-08-01 19:19:49'),(6,1,'AI智能体开发学习路径',7,'AI 智能体开发工程师','[{\"id\": \"s2-1\", \"order\": 1, \"title\": \"Python 高级编程\", \"duration\": \"1-2周\", \"completed\": false, \"resources\": [{\"id\": \"res2-1\", \"url\": \"\", \"type\": \"book\", \"title\": \"Fluent Python（第二版）\", \"platform\": \"O\'Reilly\"}], \"description\": \"异步编程、装饰器、类型注解、性能优化\"}, {\"id\": \"s2-2\", \"order\": 2, \"title\": \"LLM 基础与 Prompt Engineering\", \"duration\": \"3-4周\", \"completed\": false, \"resources\": [{\"id\": \"res2-2\", \"url\": \"\", \"type\": \"course\", \"title\": \"Prompt Engineering Guide\", \"platform\": \"DeepLearning.AI\"}], \"description\": \"理解 LLM 工作原理、掌握提示工程方法论\"}, {\"id\": \"s2-3\", \"order\": 3, \"title\": \"LangChain & Agent 框架\", \"duration\": \"5-7周\", \"completed\": false, \"resources\": [{\"id\": \"res2-3\", \"url\": \"\", \"type\": \"course\", \"title\": \"LangChain: Chat with Your Data\", \"platform\": \"DeepLearning.AI\"}, {\"id\": \"res2-4\", \"url\": \"\", \"type\": \"video\", \"title\": \"Building Agentic Applications\", \"platform\": \"YouTube\"}], \"description\": \"掌握 LangChain/LangGraph、ReAct 模式、Tool Calling\"}, {\"id\": \"s2-4\", \"order\": 4, \"title\": \"RAG 与向量数据库\", \"duration\": \"8-9周\", \"completed\": false, \"resources\": [{\"id\": \"res2-5\", \"url\": \"\", \"type\": \"project\", \"title\": \"向量数据库实战\", \"platform\": \"GitHub\"}], \"description\": \"搭建企业级 RAG 系统、ChromaDB/Milvus 实践\"}, {\"id\": \"s2-5\", \"order\": 5, \"title\": \"Multi-Agent 系统实战\", \"duration\": \"10周\", \"completed\": false, \"resources\": [{\"id\": \"res2-6\", \"url\": \"\", \"type\": \"article\", \"title\": \"AutoGen 实战教程\", \"platform\": \"微软官方\"}], \"description\": \"构建多Agent协作系统，完成端到端项目\"}]','10周','2026-08-01 19:19:49','2026-08-01 19:19:49');
/*!40000 ALTER TABLE `learning_path` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `match_result`
--

DROP TABLE IF EXISTS `match_result`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `match_result` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL COMMENT '用户ID',
  `resume_id` int NOT NULL COMMENT '简历ID',
  `position_id` int NOT NULL COMMENT '岗位ID',
  `position_name` varchar(100) NOT NULL COMMENT '岗位名称（冗余，方便查询）',
  `resume_name` varchar(100) NOT NULL COMMENT '简历名称（冗余）',
  `total_score` int NOT NULL COMMENT '综合匹配分数 0-100',
  `dimensions` json NOT NULL COMMENT '各维度评分列表',
  `gap_analysis` json NOT NULL COMMENT '差距分析结果',
  `suggestions` json NOT NULL COMMENT '优化建议列表',
  `match_date` datetime NOT NULL COMMENT '匹配时间',
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `position_id` (`position_id`),
  KEY `resume_id` (`resume_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `match_result_ibfk_1` FOREIGN KEY (`position_id`) REFERENCES `job_position` (`id`),
  CONSTRAINT `match_result_ibfk_2` FOREIGN KEY (`resume_id`) REFERENCES `user_resume` (`id`),
  CONSTRAINT `match_result_ibfk_3` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1004 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `match_result`
--

LOCK TABLES `match_result` WRITE;
/*!40000 ALTER TABLE `match_result` DISABLE KEYS */;
/*!40000 ALTER TABLE `match_result` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `position_skill`
--

DROP TABLE IF EXISTS `position_skill`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `position_skill` (
  `id` int NOT NULL AUTO_INCREMENT,
  `position_id` int NOT NULL,
  `name` varchar(100) NOT NULL COMMENT '技能名称',
  `level` varchar(20) NOT NULL COMMENT '重要性: required/preferred/advanced',
  `kind` varchar(20) NOT NULL COMMENT '类型: required=必备, preferred=加分',
  `category` varchar(50) NOT NULL COMMENT '技术栈分类，如后端/前端/AI',
  PRIMARY KEY (`id`),
  KEY `position_id` (`position_id`),
  CONSTRAINT `position_skill_ibfk_1` FOREIGN KEY (`position_id`) REFERENCES `job_position` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=77 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `position_skill`
--

LOCK TABLES `position_skill` WRITE;
/*!40000 ALTER TABLE `position_skill` DISABLE KEYS */;
INSERT INTO `position_skill` VALUES (39,7,'Python','required','required','编程语言'),(40,7,'LangChain / LangGraph','required','required','AI框架'),(41,7,'LLM API 调用与调优','required','required','AI技术'),(42,7,'Prompt Engineering','required','required','AI技术'),(43,7,'RAG 检索增强生成','required','required','AI技术'),(44,7,'Multi-Agent 系统设计','preferred','preferred','AI框架'),(45,7,'向量数据库（Milvus/ChromaDB）','preferred','preferred','数据存储'),(46,7,'FastAPI / Flask','preferred','preferred','后端开发'),(47,8,'Prompt Engineering','required','required','AI技术'),(48,8,'LLM 推理与 Token 优化','required','required','AI技术'),(49,8,'Python','required','required','编程语言'),(50,8,'Agent 框架','preferred','preferred','AI框架'),(51,8,'NLP 基础','preferred','preferred','AI技术'),(52,9,'Python / C++','required','required','编程语言'),(53,9,'ROS / ROS2','required','required','机器人框架'),(54,9,'计算机视觉','required','required','AI技术'),(55,9,'深度强化学习','required','required','AI技术'),(56,9,'NVIDIA Isaac Sim','preferred','preferred','仿真平台'),(57,9,'VLM 模型微调','preferred','preferred','AI技术'),(58,10,'Java / Spring Boot','required','required','编程语言'),(59,10,'MySQL / Redis','required','required','数据存储'),(60,10,'微服务架构','required','required','架构设计'),(61,10,'Docker / K8s','required','required','云原生'),(62,10,'LLM API 集成','required','required','AI集成'),(63,10,'智能体开发','preferred','preferred','AI集成'),(64,10,'全栈能力（Vue/React）','preferred','preferred','前端'),(65,10,'RAG 框架','preferred','preferred','AI集成'),(66,11,'TypeScript','required','required','编程语言'),(67,11,'Vue 3 / React','required','required','前端框架'),(68,11,'Vite / Webpack','required','required','构建工具'),(69,11,'AI 辅助开发工具','required','required','AI工具'),(70,11,'Node.js / SSR','preferred','preferred','全栈'),(71,11,'可视化（G6/ECharts）','preferred','preferred','数据可视化'),(72,12,'Python / SQL','required','required','编程语言'),(73,12,'Spark / Flink','required','required','大数据框架'),(74,12,'数据仓库建模','required','required','数据架构'),(75,12,'ML Pipeline','preferred','preferred','AI工程化'),(76,12,'实时计算','preferred','preferred','大数据框架');
/*!40000 ALTER TABLE `position_skill` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user_resume`
--

DROP TABLE IF EXISTS `user_resume`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_resume` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL COMMENT '所属用户ID',
  `name` varchar(100) NOT NULL COMMENT '简历别名，用户自定义',
  `target_position` varchar(100) DEFAULT NULL COMMENT '目标岗位方向',
  `personal_name` varchar(50) NOT NULL COMMENT '姓名',
  `personal_email` varchar(100) NOT NULL COMMENT '邮箱',
  `personal_phone` varchar(20) NOT NULL COMMENT '手机号',
  `personal_location` varchar(50) NOT NULL COMMENT '所在地',
  `desired_position` varchar(100) DEFAULT NULL COMMENT '期望职位',
  `desired_city` varchar(50) DEFAULT NULL COMMENT '期望城市',
  `salary_expectation` varchar(50) DEFAULT NULL COMMENT '期望薪资',
  `work_mode` varchar(20) DEFAULT NULL COMMENT '工作模式: fulltime/intern/remote',
  `self_evaluation` text NOT NULL COMMENT '自我评价',
  `source_file` varchar(200) DEFAULT NULL COMMENT '上传的原始文件名',
  `source_file_path` varchar(500) DEFAULT NULL COMMENT '上传文件的服务器存储路径',
  `raw_text` text COMMENT '简历提取后的完整纯文本',
  `education_list` json NOT NULL COMMENT '教育经历列表',
  `work_experience_list` json NOT NULL COMMENT '工作经历列表',
  `project_list` json NOT NULL COMMENT '项目经历列表',
  `skill_list` json NOT NULL COMMENT '技能列表',
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `resume_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=59 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_resume`
--

LOCK TABLES `user_resume` WRITE;
/*!40000 ALTER TABLE `user_resume` DISABLE KEYS */;
INSERT INTO `user_resume` VALUES (1,1,'Java后端开发简历','Java 开发工程师','张三','zhangsan@example.com','138****1234','北京','Java 开发工程师','北京','15K-25K','fulltime','三年Java后端开发经验，熟悉企业级应用开发，具备良好的系统设计能力和团队协作精神。',NULL,NULL,NULL,'[{\"major\": \"计算机科学与技术\", \"degree\": \"本科\", \"school\": \"某科技大学\", \"end_date\": \"\", \"start_date\": \"\"}]','[{\"skills\": [\"Java\", \"Spring Boot\", \"MySQL\", \"Redis\", \"Docker\"], \"company\": \"某互联网公司\", \"end_date\": \"\", \"position\": \"Java 后端开发\", \"start_date\": \"\", \"description\": \"负责电商平台订单系统后端开发，使用 Spring Boot + MySQL + Redis 技术栈，参与微服务拆分与容器化部署。\"}]','[{\"name\": \"电商订单系统\", \"role\": \"核心开发\", \"highlights\": [\"系统QPS从500优化至2000\", \"引入消息队列解耦订单流程\"], \"description\": \"负责订单模块的设计与开发，日均处理订单量 10万+，采用微服务架构。\", \"technologies\": [\"Java\", \"Spring Cloud\", \"RocketMQ\", \"MySQL\"]}]','[{\"id\": \"rs1\", \"name\": \"Java\", \"level\": \"advanced\", \"category\": \"编程语言\"}, {\"id\": \"rs2\", \"name\": \"Spring Boot\", \"level\": \"advanced\", \"category\": \"框架\"}, {\"id\": \"rs3\", \"name\": \"MySQL\", \"level\": \"required\", \"category\": \"数据存储\"}, {\"id\": \"rs4\", \"name\": \"Redis\", \"level\": \"required\", \"category\": \"数据存储\"}, {\"id\": \"rs5\", \"name\": \"Docker\", \"level\": \"preferred\", \"category\": \"云原生\"}, {\"id\": \"rs6\", \"name\": \"微服务\", \"level\": \"preferred\", \"category\": \"架构\"}]','2026-07-18 21:21:28','2026-07-20 17:55:17'),(2,1,'AI方向简历','AI 智能体开发工程师','李四','lisi@example.com','139****5678','上海','AI 工程师','上海','25K-40K','fulltime','对 AI Agent 和 RAG 方向有浓厚兴趣，持续跟踪前沿技术，具备独立项目交付能力。',NULL,NULL,NULL,'[{\"major\": \"人工智能\", \"degree\": \"硕士\", \"school\": \"某理工大学\", \"endDate\": \"2024-06\", \"startDate\": \"2021-09\"}]','[{\"skills\": [\"Python\", \"LangChain\", \"FastAPI\", \"向量数据库\"], \"company\": \"某AI公司\", \"endDate\": \"2026-05\", \"position\": \"AI 算法工程师\", \"startDate\": \"2024-07\", \"description\": \"负责基于 LLM 的对话系统开发，使用 LangChain + FastAPI 构建 RAG 问答系统，参与 Agent 框架预研。\"}]','[{\"name\": \"企业智能知识库\", \"role\": \"项目负责人\", \"highlights\": [\"检索召回率 95%+\", \"日均问答量 5000+\"], \"description\": \"搭建基于 RAG 的企业级智能问答系统，支持多文档格式解析与检索。\", \"technologies\": [\"Python\", \"LangChain\", \"ChromaDB\", \"FastAPI\", \"Vue 3\"]}]','[{\"id\": \"rs10\", \"name\": \"Python\", \"level\": \"advanced\", \"category\": \"编程语言\"}, {\"id\": \"rs11\", \"name\": \"LangChain\", \"level\": \"required\", \"category\": \"AI框架\"}, {\"id\": \"rs12\", \"name\": \"LLM API\", \"level\": \"required\", \"category\": \"AI技术\"}, {\"id\": \"rs13\", \"name\": \"RAG\", \"level\": \"required\", \"category\": \"AI技术\"}, {\"id\": \"rs14\", \"name\": \"Prompt Engineering\", \"level\": \"required\", \"category\": \"AI技术\"}, {\"id\": \"rs15\", \"name\": \"FastAPI\", \"level\": \"preferred\", \"category\": \"后端\"}]','2026-07-18 21:21:28','2026-07-18 21:21:28'),(3,1,'AI方向简历 (AI版)','AI 智能体开发工程师','李四','lisi@example.com','139****5678','上海','AI 工程师','上海','25K-40K','fulltime','对 AI Agent 和 RAG 方向有浓厚兴趣，持续跟踪前沿技术，具备独立项目交付能力。熟练掌握 Python、LangChain / LangGraph、LLM API 调用与调优、Prompt Engineering，与「AI 智能体开发工程师」岗位核心要求高度契合。',NULL,NULL,NULL,'[{\"major\": \"人工智能\", \"degree\": \"硕士\", \"school\": \"某理工大学\", \"end_date\": \"\", \"start_date\": \"\"}]','[{\"skills\": [\"Python\", \"LangChain\", \"FastAPI\", \"向量数据库\"], \"company\": \"某AI公司\", \"end_date\": \"\", \"position\": \"AI 算法工程师\", \"start_date\": \"\", \"description\": \"负责基于 LLM 的对话系统开发，使用 LangChain + FastAPI 构建 RAG 问答系统，参与 Agent 框架预研。\"}]','[{\"name\": \"企业智能知识库\", \"role\": \"项目负责人\", \"highlights\": [\"检索召回率 95%+\", \"日均问答量 5000+\"], \"description\": \"搭建基于 RAG 的企业级智能问答系统，支持多文档格式解析与检索。\", \"technologies\": [\"Python\", \"LangChain\", \"ChromaDB\", \"FastAPI\", \"Vue 3\"]}]','[{\"id\": \"rs10\", \"name\": \"Python\", \"level\": \"advanced\", \"category\": \"编程语言\"}, {\"id\": \"rs11\", \"name\": \"LangChain\", \"level\": \"required\", \"category\": \"AI框架\"}, {\"id\": \"rs12\", \"name\": \"LLM API\", \"level\": \"required\", \"category\": \"AI技术\"}, {\"id\": \"rs13\", \"name\": \"RAG\", \"level\": \"required\", \"category\": \"AI技术\"}, {\"id\": \"rs14\", \"name\": \"Prompt Engineering\", \"level\": \"required\", \"category\": \"AI技术\"}, {\"id\": \"rs15\", \"name\": \"FastAPI\", \"level\": \"preferred\", \"category\": \"后端\"}, {\"id\": \"sk-ai-7\", \"name\": \"Multi-Agent 系统设计\", \"level\": \"beginner\", \"category\": \"待提升\"}, {\"id\": \"sk-ai-8\", \"name\": \"向量数据库（Milvus/ChromaDB）\", \"level\": \"beginner\", \"category\": \"待提升\"}]','2026-07-19 01:47:31','2026-07-20 17:56:51');
/*!40000 ALTER TABLE `user_resume` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `skill_change`
--

DROP TABLE IF EXISTS `skill_change`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `skill_change` (
  `id` int NOT NULL AUTO_INCREMENT,
  `position_id` int NOT NULL,
  `skill_name` varchar(100) NOT NULL COMMENT '变化的技能名',
  `change_type` varchar(20) NOT NULL COMMENT '变化类型: added/removed/modified',
  `description` text NOT NULL COMMENT '变化说明',
  `source` varchar(200) NOT NULL COMMENT '数据来源',
  `change_date` varchar(20) NOT NULL COMMENT '变化日期，如 2026-06',
  PRIMARY KEY (`id`),
  KEY `position_id` (`position_id`),
  CONSTRAINT `skill_change_ibfk_1` FOREIGN KEY (`position_id`) REFERENCES `job_position` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `skill_change`
--

LOCK TABLES `skill_change` WRITE;
/*!40000 ALTER TABLE `skill_change` DISABLE KEYS */;
INSERT INTO `skill_change` VALUES (8,10,'智能体开发','added','Java工程师需要了解 Agent 开发框架，能够将 AI Agent 集成到业务系统','招聘平台+行业报告','2026-02'),(9,10,'LLM API 集成','added','大模型能力成为后端基础设施，需要掌握 LLM API 调用与编排','技术博客+JD分析','2025-09'),(10,10,'SSH/SSM 框架','removed','传统框架逐步被 Spring Boot 和微服务替代，招聘需求显著下降','招聘数据趋势','2025-06'),(11,10,'RAG 框架','added','检索增强生成成为企业知识库场景的核心技术','行业技术报告','2026-04'),(12,11,'AI 辅助开发工具','added','Copilot/Cursor 等工具已成为前端必备用具','技术社区调查','2025-12'),(13,11,'TypeScript','modified','从\'加分项\'升级为\'必备技能\'','JD分析趋势','2025-06'),(14,12,'ML Pipeline','added','数据工程与 AI 工程化边界模糊，需要掌握 ML 训练管线','技术大会分享','2026-01');
/*!40000 ALTER TABLE `skill_change` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user`
--

DROP TABLE IF EXISTS `user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL COMMENT '用户名',
  `password_hash` varchar(255) NOT NULL COMMENT '密码哈希',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间',
  `email` varchar(100) NOT NULL COMMENT '邮箱',
  `nickname` varchar(50) DEFAULT NULL COMMENT '昵称',
  `phone` varchar(20) DEFAULT NULL COMMENT '手机号',
  `city` varchar(50) DEFAULT NULL COMMENT '所在城市',
  `education` varchar(50) DEFAULT NULL COMMENT '最高学历',
  `avatar` varchar(500) DEFAULT NULL COMMENT '头像URL',
  `resume_count` int NOT NULL DEFAULT '0' COMMENT '简历数量',
  `match_history_count` int NOT NULL DEFAULT '0' COMMENT '匹配历史次数',
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `uq_user_email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user`
--

LOCK TABLES `user` WRITE;
/*!40000 ALTER TABLE `user` DISABLE KEYS */;
INSERT INTO `user` VALUES (1,'admin','$2b$12$YguI.ThQGWtihsJp4N.hgOFCDBhI8lU9FYXJACkkE49jgZxERscvS','2026-06-15 12:07:27','2026-06-15 12:07:27','admin@jiebang.com',NULL,NULL,NULL,NULL,NULL,0,0);
/*!40000 ALTER TABLE `user` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-08-03 16:21:54
