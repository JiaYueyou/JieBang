# -*- coding: utf-8 -*-
"""
科大讯飞岗位数据清洗脚本
输入: 爬虫/科大讯飞.json (220条)
输出: 清洗后_岗位数据.csv
功能: 提取35+个标准化维度，方便导入MySQL
"""

import json
import re
import csv
from collections import Counter


# 1. 读取数据
with open('科大讯飞.json', 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

print(f"✅ 读取到 {len(raw_data)} 条原始数据")


# 2. 定义技能库（用于文本匹配提取）
# 2.1 编程语言
PATTERN_LANGUAGES = {
    'Java': r'Java(?![Sscript])',
    'Python': r'Python',
    'C++': r'C\+\+',
    'C': r'(?<![a-zA-Z])C(?![a-zA-Z+])',
    'Go': r'(?<![a-zA-Z])Go(?![a-zA-Z])',
    'SQL': r'(?<![a-zA-Z])SQL(?![a-zA-Z])',
    'Shell': r'Shell|Bash',
    'JavaScript': r'JavaScript|JS(?![ON])',
    'TypeScript': r'TypeScript',
    'Scala': r'Scala',
    'Rust': r'Rust',
    'Ruby': r'Ruby',
    'MATLAB': r'MATLAB',
}

# 2.2 后端框架
PATTERN_BACKEND = {
    'Spring': r'Spring(?![\s-]*Boot|\s*Cloud)',
    'Spring Boot': r'Spring[\s-]*Boot',
    'Spring Cloud': r'Spring[\s-]*Cloud',
    'Spring MVC': r'Spring[\s-]*MVC',
    'MyBatis': r'MyBatis',
    'Netty': r'Netty',
    'Tomcat': r'Tomcat',
    'Nginx': r'Nginx',
    'SSH': r'SSH|Struts|Hibernate',
    'Django': r'Django',
    'Flask': r'Flask',
    'FastAPI': r'FastAPI',
}

# 2.3 数据库
PATTERN_DATABASES = {
    'MySQL': r'\bMySQL\b',
    'PostgreSQL': r'\bPostgreSQL|Postgres\b',
    'Oracle': r'\bOracle\b',
    'Redis': r'\bRedis\b',
    'MongoDB': r'\bMongoDB\b',
    'Elasticsearch': r'\bElasticsearch|ES\b',
    'HBase': r'\bHBase\b',
    'Hive': r'\bHive\b',
    'SQLite': r'\bSQLite\b',
    'ClickHouse': r'\bClickHouse\b',
}

# 2.4 中间件/消息队列
PATTERN_MIDDLEWARE = {
    'Kafka': r'\bKafka\b',
    'RabbitMQ': r'\bRabbitMQ\b',
    'RocketMQ': r'\bRocketMQ\b',
    'ActiveMQ': r'\bActiveMQ\b',
    'ZooKeeper': r'\bZooKeeper|ZK\b',
    'Nacos': r'\bNacos\b',
    'Consul': r'\bConsul\b',
    'ETCD': r'\bETCD\b',
}

# 2.5 DevOps/云/工具
PATTERN_DEVOPS = {
    'Docker': r'\bDocker\b',
    'Kubernetes': r'\bKubernetes|K8s|k8s\b',
    'Jenkins': r'\bJenkins\b',
    'GitLab CI': r'\bGitLab[-\s]*CI\b',
    'CI/CD': r'\bCI/CD\b',
    'Git': r'\bGit\b',
    'Maven': r'\bMaven\b',
    'Gradle': r'\bGradle\b',
    'Linux': r'\bLinux\b',
    '云原生': r'云原生',
}

# 2.6 大数据技术栈
PATTERN_BIGDATA = {
    'Hadoop': r'\bHadoop\b',
    'Spark': r'\bSpark\b',
    'Flink': r'\bFlink\b',
    'Storm': r'\bStorm\b',
    'HDFS': r'\bHDFS\b',
    'MapReduce': r'\bMapReduce\b',
    'Flume': r'\bFlume\b',
    'Sqoop': r'\bSqoop\b',
    'Presto': r'\bPresto\b',
    'Ray': r'\bRay\b',
    'ETL': r'\bETL\b',
    '数据仓库': r'数仓|数据仓库',
    '数据中台': r'数据中台',
}

# 2.7 AI/ML框架与库
PATTERN_ML_FRAMEWORKS = {
    'PyTorch': r'\bPyTorch\b',
    'TensorFlow': r'\bTensorFlow\b',
    'Keras': r'\bKeras\b',
    'scikit-learn': r'\bsklearn|scikit[-\s]learn\b',
    'XGBoost': r'\bXGBoost\b',
    'LightGBM': r'\bLightGBM\b',
    'ONNX': r'\bONNX\b',
    'TensorRT': r'\bTensorRT\b',
}

# 2.8 AI细分方向
PATTERN_AI_FIELDS = {
    '自然语言处理(NLP)': r'\bNLP\b|自然语言处理',
    '计算机视觉(CV)': r'计算机视觉|\bCV\b(?![a-zA-Z])',
    '语音识别': r'语音|音频',
    '多模态': r'多模态',
    '强化学习': r'强化学习|\bRL\b(?!ogi)',
    '异常检测': r'异常检测|异音检测|缺陷检测|质检',
    '推荐系统': r'推荐系统',
    '知识图谱': r'知识图谱',
    '数据挖掘': r'数据挖掘',
    'OCR': r'\bOCR\b',
}

# 2.9 大模型相关
PATTERN_LLM = {
    '大模型(LLM)': r'大模型|\bLLM\b',
    'RAG': r'\bRAG\b',
    'Agent': r'\bAgent\b',
    'Prompt工程': r'\bPrompt\b',
    'LangChain': r'\bLangChain\b',
    '模型微调': r'微调|fine[-\s]tune|Fine[-\s]Tune',
    '模型训练': r'模型训练|训练',
    '推理加速': r'推理加速|推理优化',
    '模型压缩': r'模型压缩|量化(?!分析)|剪枝|蒸馏',
    'Transformer': r'\bTransformer\b',
    'BERT': r'\bBERT\b',
    'GPT': r'\bGPT\b',
}

# 2.10 工程能力
PATTERN_ENGINEERING = {
    '架构设计': r'架构设计',
    '微服务': r'微服务',
    '分布式系统': r'分布式',
    '高并发': r'高并发',
    '高可用': r'高可用',
    '性能优化': r'性能优化|性能调优|SQL优化',
    '设计模式': r'设计模式',
    '代码规范': r'代码规范|编码规范|开发规范',
    '重构': r'重构',
    '单元测试': r'单元测试|测试用例',
    '面向对象(OOP)': r'面向对象|\bOOP\b',
    'DevOps': r'\bDevOps\b',
}

# 2.11 数据处理能力
PATTERN_DATA = {
    '数据分析': r'数据分析',
    '数据清洗': r'数据清洗',
    '特征工程': r'特征工程|特征构建',
    '数据标注': r'标注',
    '数据采集': r'数据采集',
    '数据闭环': r'数据闭环',
    '数据质量': r'数据质量|质量评估',
    '数据增强': r'数据增强|数据扩增',
    '归一化': r'归一化',
    '数据治理': r'数据治理',
}

# 2.12 协议/标准
PATTERN_PROTOCOLS = {
    'TCP/IP': r'\bTCP/IP\b',
    'HTTP/HTTPS': r'\bHTTP|HTTPS\b',
    'RESTful': r'\bRESTful|REST\b',
    'WebSocket': r'\bWebSocket\b',
    'MQTT': r'\bMQTT\b',
    'Modbus': r'\bModbus\b',
    'AMQP': r'\bAMQP\b',
    'OPC UA': r'\bOPC[-\s]*UA\b',
}

# 2.13 硬件/平台
PATTERN_HARDWARE = {
    'ARM': r'\bARM\b',
    'GPU': r'\bGPU\b',
    'FPGA': r'\bFPGA\b',
    'CUDA': r'\bCUDA\b',
    '嵌入式': r'嵌入式',
    '边缘计算': r'边缘计算|边缘设备|边缘侧',
    '物联网(IoT)': r'物联网|\bIoT\b',
    'Linux平台': r'\bLinux\b',
    'Android': r'\bAndroid\b',
    'iOS': r'\biOS\b',
    'Windows': r'\bWindows\b',
    '容器化': r'容器|容器化|K8s|k8s|Kubernetes|Docker',
}

# 2.14 行业领域
PATTERN_INDUSTRY = {
    '工业制造': r'工业',
    '轨道交通': r'轨交|轨道交通',
    '汽车电子': r'汽车电子',
    '金融': r'金融',
    '教育': r'教育',
    '医疗': r'医疗',
    '声学/音频': r'声学|音频|语音',
    '信号处理': r'信号处理',
    '内容安全': r'内容安全|数字水印|安全攻防',
}

# 2.15 软技能
PATTERN_SOFT_SKILLS = {
    '沟通能力': r'沟通',
    '团队协作': r'团队[协作合作]|协作',
    '责任心': r'责任[心感]',
    '学习能力': r'学习能力|自驱|自我驱动',
    '逻辑思维': r'逻辑思维|逻辑',
    '解决问题': r'解决问题|问题解决|问题拆解',
    '抗压能力': r'抗压|承压',
    '执行力': r'执行力',
    '结果导向': r'结果导向|目标导向',
    '创新精神': r'创新|钻研',
    '主动性': r'主动',
    '严谨细致': r'严谨|细心|细致',
    '文档能力': r'文档|编写',
}

# 2.16 管理能力
PATTERN_MANAGEMENT = {
    '项目管理': r'项目管理',
    '团队管理': r'团队管理|带领团队|管理团队|管理经验',
    '跨部门协作': r'跨部门|跨团队',
    '需求分析': r'需求分析|需求抽象',
    '技术规划': r'技术规划|Roadmap|roadmap',
}

# 2.17 专业要求
PATTERN_MAJORS = {
    '计算机类': r'计算机',
    '软件工程': r'软件工程',
    '自动化': r'自动化',
    '电子工程': r'电子工程|电子信息',
    '通信工程': r'通信',
    '数学/统计': r'数学|统计学',
    '人工智能': r'人工智能',
    '声学': r'声学',
    '物理': r'物理',
}

# 2.18 语言能力
PATTERN_LANGUAGE = {
    '英语六级': r'英语[六6]级|CET[-\s]*6',
    '英语四级': r'英语[四4]级|CET[-\s]*[44]',
    '英文文献调研': r'中英[文语]|英文|论文调研|文献',
}

# 2.19 证书认证
PATTERN_CERT = {
    'PMP': r'\bPMP\b',
    'NPDP': r'\bNPDP\b',
    '系统架构师认证': r'系统架构师',
}



# 3. 辅助函数

def extract_skills(text, pattern_dict):
    """从文本中提取技能，返回逗号分隔的字符串"""
    if not text:
        return ''
    found = set()
    for skill_name, pattern in pattern_dict.items():
        # 统一传入 re.IGNORECASE，避免  在非开头位置报错
        try:
            if re.search(pattern, text, re.IGNORECASE):
                found.add(skill_name)
        except re.error:
            pass
    return '、'.join(sorted(found))


def extract_city_list(city_field):
    """标准化城市字段"""
    if not city_field:
        return ''
    if isinstance(city_field, list):
        cities = city_field
    else:
        # 处理 "安徽省·合肥市, 北京市" 或 "河南省·信阳市/郑州市"
        cities = [c.strip() for c in city_field.replace('，', ',').split(',')]

    processed = []
    for c in cities:
        # 去掉省份前缀 "安徽省·合肥市" -> "合肥"
        parts = c.replace('·', '/').split('/')
        city_name = parts[-1].replace('市', '').strip()
        if city_name:
            processed.append(city_name)
    return '、'.join(processed)


def standardize_experience(exp_str):
    """标准化经验要求为统一的描述"""
    if not exp_str:
        return '未要求', 0

    exp_str = exp_str.strip()

    if exp_str in ['经验不限', '应届生']:
        return '经验不限', 0

    # "5年以上" -> 5, "3-5年" -> 3, "1-3年" -> 1
    m = re.match(r'(\d+)[-~](\d+)', exp_str)
    if m:
        return f'{m.group(1)}-{m.group(2)}年', int(m.group(1))

    m = re.match(r'(\d+)\s*年[以及]\s*上', exp_str)
    if m:
        return f'{m.group(1)}年以上', int(m.group(1))

    m = re.match(r'(\d+)\s*年?$', exp_str)
    if m:
        return f'{m.group(1)}年', int(m.group(1))

    m = re.match(r'(\d+)\s*年?\s*[以]?[上及]?', exp_str)
    if m:
        return f'{m.group(1)}年以上', int(m.group(1))

    return exp_str, 0


def standardize_education(edu_str):
    """标准化学历要求"""
    if not edu_str:
        return '学历不限'

    edu_str = edu_str.strip()

    if edu_str in ['学历不限', '不限']:
        return '学历不限'
    if '博士' in edu_str:
        return '博士'
    if '硕士' in edu_str or '研究生' in edu_str:
        return '硕士及以上'
    if '本科' in edu_str:
        if '统招' in edu_str:
            return '统招本科'
        return '本科'

    return edu_str


def extract_tech_levels(title):
    """从岗位名称提取级别"""
    if '初级' in title or '助理' in title:
        return '初级'
    if '高级' in title or '资深' in title or '专家' in title:
        if '中级' in title:
            return '中级'
        return '高级'
    if '中级' in title or '经理' in title or '总监' in title:
        return '中级'
    return '未标注'


def extract_job_category(title):
    """从岗位名称提取职能分类"""
    categories = []

    # 按优先级从高到低匹配
    if re.search(r'算法|研究', title):
        categories.append('算法研究')
    if re.search(r'开发|研发', title) and '算法' not in title:
        categories.append('软件开发')
    if re.search(r'测试', title):
        categories.append('软件测试')
    if re.search(r'运维', title):
        categories.append('运维')
    if re.search(r'大数据', title):
        categories.append('大数据')
    if re.search(r'架构师|架构', title) and '产品' not in title:
        categories.append('架构')
    if re.search(r'安全', title):
        categories.append('安全')
    if re.search(r'数据挖掘', title):
        categories.append('数据挖掘')
    if re.search(r'Agent|AI[-\s]*研发|prompt', title, re.I):
        categories.append('AI')
    if re.search(r'产品经理|产品线|产品运营', title):
        categories.append('产品经理')
    if re.search(r'讲师', title):
        categories.append('讲师')
    if re.search(r'售前|咨询', title):
        categories.append('售前/咨询')
    if re.search(r'交付|实施', title):
        categories.append('交付/实施')
    if re.search(r'硬件工程师|结构工程师|硬件工程|硬件质量', title):
        categories.append('硬件工程')
    if re.search(r'UI设计师|交互设计', title):
        categories.append('设计')
    if re.search(r'销售|客户经理|渠道经理|市场经理|区域市场', title):
        categories.append('销售/市场')
    if re.search(r'HRBP|招聘|人力', title):
        categories.append('人力资源')
    if re.search(r'运营|运营管理', title):
        categories.append('运营')
    if re.search(r'采购|供应商管理|仓储|供应链', title):
        categories.append('供应链/采购')
    if re.search(r'项目经理', title):
        categories.append('项目管理')
    if re.search(r'会计|财务|风控|证券', title):
        categories.append('财务/风控')
    if re.search(r'品牌|市场', title):
        categories.append('品牌/市场')

    return '、'.join(categories) if categories else '其他'


def extract_ai_subfield(title, text):
    """提取AI方向的细分领域"""
    fields = []
    text_lower = title + ' ' + (text or '')

    if re.search(r'NLP|自然语言|语音|语义|对话|文本|摘要|问答', text_lower, re.I):
        fields.append('NLP/语音')
    if re.search(r'计算机视觉|CV|图像|视觉|OCR', text_lower, re.I):
        fields.append('计算机视觉')
    if re.search(r'多模态', text_lower):
        fields.append('多模态')
    if re.search(r'Agent|智能体', text_lower, re.I):
        fields.append('AI Agent')
    if re.search(r'大模型|LLM', text_lower, re.I):
        fields.append('大模型')
    if re.search(r'推荐|搜索|广告', text_lower):
        fields.append('推荐/搜索')
    if re.search(r'异常检测|异音检测|缺陷|质检', text_lower):
        fields.append('异常检测')
    if re.search(r'强化学习|RL', text_lower):
        fields.append('强化学习')
    if re.search(r'知识图谱', text_lower):
        fields.append('知识图谱')
    if re.search(r'内容安全|数字水印|安全攻防', text_lower):
        fields.append('AI安全')
    if re.search(r'教育', text_lower, re.I):
        fields.append('AI+教育')
    if re.search(r'医疗', text_lower, re.I):
        fields.append('AI+医疗')

    return '、'.join(fields) if fields else '无明确AI方向'



# 4. 核心清洗逻辑

cleaned_data = []
invalid_data_count = 0
raw_total = len(raw_data)

for idx, job in enumerate(raw_data):
    # 无效岗位过滤规则
    title = job.get("title","").strip()
    require_text = job.get('require', '') or ''
    jd_text = job.get('jd_text', '') or ''
    all_text = require_text + ' ' + jd_text

    # 过滤：岗位名为空、JD文本过短
    if not title or len(all_text.strip()) < 10:
        invalid_data_count += 1
        continue
    # 合并待分析的文本
    require_text = job.get('require', '') or ''
    jd_text = job.get('jd_text', '') or ''
    duty_text = job.get('duty', '') or ''
    all_text = require_text + ' ' + jd_text + ' ' + duty_text
    title = job.get('title', '')
    keywords_raw = job.get('keywords', []) or []

    if isinstance(keywords_raw, list):
        keywords_str = '、'.join(keywords_raw)
    else:
        keywords_str = str(keywords_raw)

    # 标准化经验
    exp_std, exp_years = standardize_experience(job.get('experience', ''))

    record = {
        # ========== 基础信息（清洗后） ==========
        '岗位名称': title,
        '公司': job.get('company', ''),
        '工作城市': extract_city_list(job.get('city', '')),
        '薪资': job.get('salary') or '未公开',
        '经验要求(原始)': job.get('experience', ''),
        '经验要求(标准化)': exp_std,
        '经验要求(年)': exp_years,
        '学历要求(原始)': job.get('education', ''),
        '学历要求(标准化)': standardize_education(job.get('education', '')),
        '发布时间': job.get('post_date', ''),
        '数据来源': job.get('source', ''),
        '原始关键词': keywords_str,

        # ========== 岗位分类 ==========
        '岗位级别': extract_tech_levels(title),
        '技术职能': extract_job_category(title),
        'AI方向细分': extract_ai_subfield(title, all_text),

        # ========== 编程与技术栈 ==========
        '编程语言': extract_skills(all_text, PATTERN_LANGUAGES),
        '后端框架': extract_skills(all_text, PATTERN_BACKEND),
        '数据库': extract_skills(all_text, PATTERN_DATABASES),
        '中间件/消息队列': extract_skills(all_text, PATTERN_MIDDLEWARE),
        'DevOps/云工具': extract_skills(all_text, PATTERN_DEVOPS),
        '大数据技术栈': extract_skills(all_text, PATTERN_BIGDATA),
        'AI/ML框架': extract_skills(all_text, PATTERN_ML_FRAMEWORKS),
        'AI细分方向': extract_skills(all_text, PATTERN_AI_FIELDS),
        '大模型相关': extract_skills(all_text, PATTERN_LLM),
        '协议/标准': extract_skills(all_text, PATTERN_PROTOCOLS),
        '硬件/平台': extract_skills(all_text, PATTERN_HARDWARE),

        # ========== 工程能力 ==========
        '工程能力': extract_skills(all_text, PATTERN_ENGINEERING),
        '数据处理能力': extract_skills(all_text, PATTERN_DATA),

        # ========== 行业领域 ==========
        '行业领域': extract_skills(all_text, PATTERN_INDUSTRY),
        '专业要求': extract_skills(all_text, PATTERN_MAJORS),

        # ========== 软技能与素质 ==========
        '软技能': extract_skills(all_text, PATTERN_SOFT_SKILLS),
        '管理能力': extract_skills(all_text, PATTERN_MANAGEMENT),

        # ========== 资质门槛 ==========
        '语言能力': extract_skills(all_text, PATTERN_LANGUAGE),
        '证书认证': extract_skills(all_text, PATTERN_CERT),

        # ========== 能力要求(标准化)
        # 用"具备XX能力"术语表述岗位要求
        # ========== 岗位要求标准化摘要（原格式保留） ==========
        # 整合成一句可读的描述
    }


    # 构建"具备XX能力"标准化字段
    ability_parts = []

    # 编程语言能力
    languages = record['编程语言']
    if languages:
        langs = languages.replace('、', '/')
        ability_parts.append(f'具备{langs}编程能力')

    # 后端框架能力
    frameworks = record['后端框架']
    if frameworks:
        ability_parts.append(f'具备{frameworks}框架应用能力')

    # 数据库能力
    dbs = record['数据库']
    if dbs:
        ability_parts.append(f'具备{dbs}数据库应用能力')

    # 中间件能力
    middleware = record['中间件/消息队列']
    if middleware:
        ability_parts.append(f'具备{middleware}等中间件应用能力')

    # DevOps/云工具能力
    devops = record['DevOps/云工具']
    if devops:
        ability_parts.append(f'具备{devops}等运维工具应用能力')

    # 大数据能力
    bigdata = record['大数据技术栈']
    if bigdata:
        ability_parts.append(f'具备{bigdata}等大数据技术应用能力')

    # AI/ML框架能力
    ml = record['AI/ML框架']
    if ml:
        ability_parts.append(f'具备{ml}等AI框架应用能力')

    # AI能力
    ai_direction = record['AI细分方向']
    if ai_direction:
        ability_parts.append(f'具备{ai_direction}领域能力')

    # 大模型能力
    llm = record['大模型相关']
    if llm:
        ability_parts.append(f'具备{llm}等大模型技术能力')

    # 工程能力
    engineering = record['工程能力']
    if engineering:
        ability_parts.append(f'具备{engineering}等工程能力')

    # 数据处理能力
    data_ability = record['数据处理能力']
    if data_ability:
        ability_parts.append(f'具备{data_ability}等数据处理能力')

    # 协议/标准
    proto = record['协议/标准']
    if proto:
        ability_parts.append(f'掌握{proto}等协议标准')

    # 硬件/平台
    hw = record['硬件/平台']
    if hw:
        ability_parts.append(f'熟悉{hw}等硬件平台')

    # 行业领域知识
    domain = record['行业领域']
    if domain:
        ability_parts.append(f'具备{domain}领域知识')

    # 专业背景
    major = record['专业要求']
    if major:
        ability_parts.append(f'{major}等相关专业背景')

    # 软技能
    soft = record['软技能']
    if soft:
        # 把"沟通能力、团队协作、责任心"转成"沟通协作能力、责任心"
        soft_clean = soft
        ability_parts.append(f'具备{soft_clean}')

    # 管理能力
    mgmt = record['管理能力']
    if mgmt:
        ability_parts.append(f'具备{mgmt}等管理能力')

    # 语言能力
    lang = record['语言能力']
    if lang:
        ability_parts.append(f'具备{lang}')

    # 证书
    cert = record['证书认证']
    if cert:
        ability_parts.append(f'持有{cert}等认证')

    record['能力要求(标准化)'] = '；'.join(ability_parts) if ability_parts else '无明确技能要求'


    # 构建原"岗位要求标准化摘要"字段
    parts = []

    parts.append(record['学历要求(标准化)'])

    if exp_years > 0:
        parts.append(f'{exp_std}经验')
    elif exp_std == '经验不限':
        parts.append('经验不限')

    if languages:
        parts.append(f'编程语言({languages})')
    if frameworks:
        parts.append(f'框架({frameworks})')
    if dbs:
        parts.append(f'数据库({dbs})')
    if middleware:
        parts.append(f'中间件({middleware})')
    if ai_direction:
        parts.append(f'AI方向({ai_direction})')
    if llm:
        parts.append(f'大模型({llm})')
    if bigdata:
        parts.append(f'大数据({bigdata})')
    if domain:
        parts.append(f'领域({domain})')
    if engineering:
        parts.append(f'工程能力({engineering})')
    if soft:
        parts.append(f'软技能({soft})')

    record['岗位要求(标准化摘要)'] = '；'.join(parts)

    cleaned_data.append(record)

success_count = len(cleaned_data)
success_rate = success_count / raw_total if raw_total > 0 else 0

print(f"✅ ========== 数据清洗统计 ==========")
print(f"原始抓取总条数：{raw_total} 条")
print(f"过滤无效岗位条数：{invalid_data_count} 条")
print(f"清洗后有效入库条数：{success_count} 条")
print(f"数据有效成功率：{success_rate:.2%}")


# 5. 统计与验证
print("\n=== 清洗后各字段填充率 ===")
for field in cleaned_data[0].keys():
    non_empty = sum(1 for r in cleaned_data if r.get(field))
    print(f"  {field}: {non_empty}/{len(cleaned_data)} ({non_empty/len(cleaned_data)*100:.0f}%)")

print("\n=== 岗位级别分布 ===")
level_counter = Counter(r['岗位级别'] for r in cleaned_data)
for k, v in level_counter.most_common():
    print(f"  {k}: {v}条")

print("\n=== 技术职能分布 ===")
cat_counter = Counter(r['技术职能'] for r in cleaned_data)
for k, v in cat_counter.most_common():
    print(f"  {k}: {v}条")

print("\n=== 学历要求分布(标准化后) ===")
edu_counter = Counter(r['学历要求(标准化)'] for r in cleaned_data)
for k, v in edu_counter.most_common():
    print(f"  {k}: {v}条")

print("\n=== 经验要求分布(标准化后) ===")
exp_counter = Counter(r['经验要求(标准化)'] for r in cleaned_data)
for k, v in exp_counter.most_common():
    print(f"  {k}: {v}条")


# 6. 输出为CSV（方便导入MySQL）
output_file = '岗位数据_清洗完成.csv'
fieldnames = list(cleaned_data[0].keys())

with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(cleaned_data)

print(f"\n 已保存到 {output_file}")
print(f"   共 {len(fieldnames)} 个字段, {len(cleaned_data)} 条记录")


# 7. 输出SQL建表语句（方便导入MySQL）
print("\n" + "="*60)
print(" MySQL建表语句（可以直接用）")
print("="*60)

sql = """
-- 创建岗位信息表
CREATE TABLE IF NOT EXISTS job_postings (
    id INT AUTO_INCREMENT PRIMARY KEY,
"""
for field in fieldnames:
    col_type = 'VARCHAR(500)'
    if field == '经验要求(年)':
        col_type = 'INT'
    elif field == '发布时间':
        col_type = 'DATETIME'
    sql += f"    `{field}` {col_type} DEFAULT NULL,\n"
sql += "    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n"
sql += f") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n\n"

sql += """-- 导入CSV到MySQL (在MySQL命令行中执行)
LOAD DATA LOCAL INFILE '岗位数据_清洗完成.csv'
INTO TABLE job_postings
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\\n'
IGNORE 1 ROWS;
"""

print(sql)
