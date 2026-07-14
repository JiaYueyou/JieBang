# -*- coding: utf-8 -*-
"""
科大讯飞岗位数据清洗 — 两步流水线（对接学长 pipeline 结构）

Step 1: 数据合并与清洗
  输入: 科大讯飞.json
  输出: outputs/merged_jobs_iflytek.json
  字段: title, company, city, salary, experience, education,
        jd_text, responsibilities, requirements, keywords,
        posted_at, url, source, crawled_at,
        source_tag, parsed.salary, parsed.experience,
        parsed.education, quality

Step 2: 岗位名称标准化
  输入: outputs/merged_jobs_iflytek.json
  输出: outputs/merged_jobs_iflytek.json (回写) + outputs/title_mapping_iflytek.json
  新增: standardized_title, canonical_key, level, stack, title_confidence
"""

import json
import re
import os
from datetime import datetime
from collections import Counter, defaultdict

# ================================================================
# 全局配置
# ================================================================
OUTPUT_DIR = 'outputs'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 学历映射表
EDUCATION_MAP = {
    '博士': 'phd',
    '博士及以上': 'phd',
    '硕士及以上': 'master',
    '硕士': 'master',
    '研究生': 'master',
    '研究生及以上': 'master',
    '统招本科': 'bachelor',
    '本科及以上': 'bachelor',
    '本科': 'bachelor',
    '大专及以上': 'college',
    '大专': 'college',
    '学历不限': None,
    '不限': None,
}

# 城市名列表（用于 title 清洗去后缀）
CITIES = sorted([
    '合肥', '深圳', '广州', '北京', '上海', '杭州', '成都', '南京',
    '苏州', '武汉', '西安', '长沙', '郑州', '沈阳', '长春', '哈尔滨',
    '太原', '昆明', '福州', '澳门', '重庆', '天津', '宁波', '厦门',
    '青岛', '大连', '济南', '南宁', '贵阳', '海口', '兰州', '西宁',
    '银川', '拉萨', '呼和浩特', '乌鲁木齐', '石家庄', '南昌', '全国',
    '雅加达',
], key=len, reverse=True)


# ================================================================
# Step 1: 数据合并与清洗
# ================================================================

def step1_merge_clean(input_path):
    """Step 1: 读取原始JSON → 合并为标准字段 → 解析 → 质量评分"""
    with open(input_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    print(f"[Step 1] 读取到 {len(raw_data)} 条原始数据")
    print(f"[Step 1] 原始字段: {list(raw_data[0].keys())}")

    output = []
    removed_empty_jd = 0

    for job in raw_data:
        title = (job.get('title') or '').strip()
        jd_text = (job.get('jd_text') or '').strip()

        # 丢弃空JD
        if not jd_text:
            removed_empty_jd += 1
            continue

        # ---- 14个标准字段 ----
        record = {
            'title': title,
            'company': (job.get('company') or '科大讯飞').strip(),
            'city': _format_city(job.get('city')),
            'salary': job.get('salary') or None,
            'experience': (job.get('experience') or '').strip() or None,
            'education': (job.get('education') or '').strip() or None,
            'jd_text': jd_text,
            'responsibilities': (job.get('duty') or '').strip() or None,
            'requirements': (job.get('require') or '').strip() or None,
            'keywords': _format_keywords(job.get('keywords')),
            'posted_at': _format_posted_at(job.get('post_date')),
            'url': job.get('url') or None,
            'source': (job.get('source') or '科大讯飞招聘').strip(),
            'crawled_at': (job.get('crawled_at') or '').strip() or None,
        }

        # ---- source_tag ----
        record['source_tag'] = 'iflytek'

        # ---- parsed 结构化解析 ----
        parsed = {}
        parsed['salary'] = _parse_salary(record['salary'])
        parsed['experience'] = _parse_experience(record['experience'])
        parsed['education'] = _parse_education(record['education'])
        record['parsed'] = parsed

        # ---- quality 质量评分 ----
        record['quality'] = _calc_quality(record)

        output.append(record)

    print(f"[Step 1] 丢弃空JD: {removed_empty_jd} 条")
    print(f"[Step 1] 有效记录: {len(output)} 条")

    # 保存
    output_path = os.path.join(OUTPUT_DIR, 'merged_jobs_iflytek.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"[Step 1] 已保存 → {output_path}")

    return output_path


def _format_city(city_field):
    """标准化城市字段"""
    if not city_field:
        return None
    if isinstance(city_field, list):
        cities = city_field
    else:
        cities = [c.strip() for c in city_field.replace('，', ',').split(',')]
    processed = []
    for c in cities:
        parts = c.replace('·', '/').split('/')
        city_name = parts[-1].replace('市', '').strip()
        if city_name:
            processed.append(city_name)
    return '、'.join(processed) if processed else None


def _format_keywords(kw):
    """标准化关键词为逗号分隔字符串"""
    if not kw:
        return None
    if isinstance(kw, list):
        return '、'.join(kw)
    return str(kw)


def _format_posted_at(date_str):
    """标准化发布时间"""
    if not date_str:
        return None
    # ISO 格式 "2026-06-12T13:41:56"
    date_str = date_str.replace('T', ' ').split('+')[0].split('Z')[0].strip()
    return date_str if date_str else None


def _parse_salary(salary_str):
    """解析薪资: "15K-25K" → {"min": 15000, "max": 25000}"""
    if not salary_str:
        return None
    salary_str = str(salary_str).strip()
    if not salary_str or salary_str in ('面议', '未公开', 'None'):
        return None
    # 匹配 "15K-25K" 或 "15k-25k" 或 "15-25K" 等
    m = re.search(r'(\d+\.?\d*)\s*[Kk]\s*[-~]\s*(\d+\.?\d*)\s*[Kk]', salary_str)
    if m:
        return {'min': int(float(m.group(1)) * 1000), 'max': int(float(m.group(2)) * 1000)}
    # 匹配 "15K以上" 或 "15K+"
    m = re.search(r'(\d+\.?\d*)\s*[Kk]\s*[以+上]?', salary_str)
    if m:
        base = int(float(m.group(1)) * 1000)
        return {'min': base, 'max': base * 2}
    # 匹配纯数字"15000-25000"
    m = re.search(r'(\d{4,})\s*[-~]\s*(\d{4,})', salary_str)
    if m:
        return {'min': int(m.group(1)), 'max': int(m.group(2))}
    return None


def _parse_experience(exp_str):
    """解析经验: "3-5年" → {"min": 3, "max": 5}"""
    if not exp_str:
        return None
    exp_str = str(exp_str).strip()
    if exp_str in ('经验不限', '应届生', 'None', ''):
        return None
    # "3-5年"
    m = re.search(r'(\d+)\s*[-~]\s*(\d+)', exp_str)
    if m:
        return {'min': int(m.group(1)), 'max': int(m.group(2))}
    # "3年以上" / "5年及以上"
    m = re.search(r'(\d+)\s*年[以和及]*上', exp_str)
    if m:
        val = int(m.group(1))
        return {'min': val, 'max': val * 2}
    # "3年"
    m = re.search(r'(\d+)\s*年', exp_str)
    if m:
        val = int(m.group(1))
        return {'min': val, 'max': val + 2}
    return None


def _parse_education(edu_str):
    """标准化学历: "本科及以上" → "bachelor" """
    if not edu_str:
        return None
    edu_str = str(edu_str).strip()
    if edu_str in ('学历不限', '不限', 'None', ''):
        return None
    for cn, en in EDUCATION_MAP.items():
        if cn in edu_str:
            return en
    return None


def _calc_quality(record):
    """
    质量评分：14个标准字段的填充率，0~1
    jd_text为空直接0
    """
    # 检查字段填充数
    fields_to_check = [
        'title', 'company', 'city', 'salary', 'experience', 'education',
        'jd_text', 'responsibilities', 'requirements', 'keywords',
        'posted_at', 'url', 'source', 'crawled_at'
    ]
    filled = sum(1 for f in fields_to_check if record.get(f))
    return round(filled / len(fields_to_check), 2)


# ================================================================
# Step 2: 岗位名称标准化
# ================================================================

# 部门前缀
DEPT_PREFIXES = sorted([
    '科大讯飞运营商事业部', '科大讯飞',
    'AI研究院', '研究院',
    '教育BG',
    '运营商BU', '运营商B8', '运营商事业部', '运营商',
    '政法军团', '城市军团AIPC业务', '城市军团',
    '聆动通用', '聆动',
    'BU', 'BG',
    '数据中台',
], key=len, reverse=True)

# canonical_key 映射
CANONICAL_MAP = {
    '大数据工程师': 'big-data-engineer',
    '研究算法工程师': 'research-algorithm-engineer',
    '算法研究员-多模态理解': 'multimodal-algorithm-researcher',
    '多模态交互研究员': 'multimodal-interaction-researcher',
    '算法工程师': 'algorithm-engineer',
    'AI算法工程师': 'ai-algorithm-engineer',
    'AI测试工程师': 'ai-test-engineer',
    'AI应用架构师': 'ai-application-architect',
    'AI技术产品经理': 'ai-technical-product-manager',
    'NLP算法工程师': 'nlp-algorithm-engineer',
    '端到端感知算法': 'end-to-end-perception-algorithm',
    '软件开发工程师': 'software-development-engineer',
    'C++软件开发工程师': 'cpp-software-development-engineer',
    '安卓开发工程师': 'android-developer',
    '嵌入式软件开发工程师': 'embedded-software-engineer',
    '系统测试工程师': 'system-test-engineer',
    '系统架构师': 'system-architect',
    '解决方案架构师': 'solution-architect',
    '安全解决方案工程师': 'security-solution-engineer',
    '硬件工程师': 'hardware-engineer',
    '硬件产品经理': 'hardware-product-manager',
    'TOC硬件产品经理': 'toc-hardware-product-manager',
    '平台硬件产品经理': 'platform-hardware-product-manager',
    '硬件销售经理': 'hardware-sales-manager',
    '硬件系统架构师': 'hardware-system-architect',
    '机器人硬件产品经理': 'robot-hardware-product-manager',
    '硬件质量工程师': 'hardware-quality-engineer',
    '结构工程师': 'structural-engineer',
    '声学工程师': 'acoustics-engineer',
    '产品经理': 'product-manager',
    '行业应用产品经理': 'industry-product-manager',
    '平台软件产品经理': 'platform-software-product-manager',
    '交付产品经理': 'delivery-product-manager',
    '客服产品经理': 'customer-service-product-manager',
    '解决方案产品经理': 'solution-product-manager',
    'UI设计师': 'ui-designer',
    '交互设计师': 'interaction-designer',
    '项目经理': 'project-manager',
    '交付项目经理': 'delivery-project-manager',
    '研发项目经理': 'rd-project-manager',
    '产研项目经理': 'product-rd-project-manager',
    '项目经理上海LT': 'shanghai-project-manager',
    '项目经理北方多语种方向': 'multilingual-project-manager',
    '供应商管理工程师': 'supplier-management-engineer',
    '供应链管理部总监': 'supply-chain-director',
    '计划工程师': 'planning-engineer',
    '采购工程师': 'procurement-engineer',
    '履约管理工程师': 'fulfillment-engineer',
    '仓储管理': 'warehouse-management',
    '用户研究工程师': 'user-research-engineer',
    '市场经理': 'marketing-manager',
    '产品线市场经理': 'product-line-marketing-manager',
    '区域市场经理': 'regional-marketing-manager',
    '客户群市场经理': 'customer-segment-marketing-manager',
    '品牌经理-品牌内容': 'brand-content-manager',
    '品牌经理-品牌资源': 'brand-resource-manager',
    '产品销售客户经理': 'product-sales-account-manager',
    '解决方案客户经理': 'solution-account-manager',
    '渠道经理': 'channel-manager',
    '渠道销售经理': 'channel-sales-manager',
    '客户经理': 'account-manager',
    '高阶运营商渠道经理': 'operator-channel-manager',
    '销售经理': 'sales-manager',
    '产品运营经理': 'product-operations-manager',
    '数据中台运营': 'data-platform-operations',
    '校园运营': 'campus-operations',
    '运营管理师': 'operations-manager',
    '高阶硬件产品经理': 'senior-hardware-product-manager',
    '财务BP': 'finance-bp',
    '售前咨询经理': 'pre-sales-consultant',
    '招聘调配管理师': 'recruitment-specialist',
    'HRBP': 'hrbp',
    '机械臂运动规划算法工程师': 'robotic-arm-algorithm-engineer',
    '证券行业专家': 'securities-industry-expert',
    '风控行业专家': 'risk-control-expert',
    '法律科技高阶市场渠道': 'legal-tech-market-channel',
    '实施工程师': 'implementation-engineer',
    '服务支持专员粤语': 'service-support-cantonese',
    '服务支持专员英语': 'service-support-english',
    '服务支持专员葡语': 'service-support-portuguese',
}

# 技术栈方向推断
STACK_KEYWORDS = {
    'backend': ['后端', 'Java', 'Spring', 'MyBatis', 'Go', '服务端', 'API', '微服务', '分布式'],
    'frontend': ['前端', 'Vue', 'React', 'HTML', 'CSS', 'JavaScript', 'UI', '交互'],
    'ai': ['算法', '研究算法', 'AI', 'NLP', 'LLM', '大模型', '深度学习', '机器学习',
           'PyTorch', 'TensorFlow', '多模态', '计算机视觉', '语音', '声学',
           '感知算法', '运动规划', 'RAG', '推荐'],
    'data': ['大数据', '数据', 'Spark', 'Flink', 'Hadoop', 'ETL', '数据仓库', '数据分析'],
    'devops': ['运维', 'DevOps', 'CI/CD', '运维开发', 'SRE'],
    'mobile': ['Android', 'iOS', '安卓', '移动端'],
    'embedded': ['嵌入式', 'C++', 'C语言', 'FPGA', 'ARM', '驱动', '硬件', '电路'],
    'fullstack': ['全栈', '全端'],
    'product': ['产品经理', '产品设计', '需求分析'],
    'test': ['测试', 'QA', '质量'],
    'hardware': ['硬件', '结构', '电子', '电气', '机械'],
    'sales': ['销售', '客户经理', '渠道', '市场', '商务', '售前'],
    'hr': ['HR', '人力', '招聘', 'BP'],
    'finance': ['财务', '会计', '风控', '证券'],
    'operation': ['运营', '项目管理', '采购', '供应链', '仓储', '履约'],
}

# 级别关键词
LEVEL_KEYWORDS = {
    'senior': ['高级', '资深', '专家', '总监', '高阶', '首席'],
    'mid': ['中级', '中级/高级'],
    'junior': ['初级', '助理', '应届', '实习', '校招'],
}


def step2_normalize_titles(input_path):
    """Step 2: 岗位名称标准化 → 级别推断 → 技术栈推断"""
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"\n[Step 2] 读取 {len(data)} 条记录")

    title_mapping = {}  # 原始title → 标准化信息
    filtered = 0
    for job in data[:]:  # 用切片遍历以便修改原列表
        raw_title = job.get('title', '')

        # 标准化名称
        std_title = _normalize_title(raw_title)

        # 过滤无意义占位记录
        if std_title == '运营商通用岗位':
            print(f'  [过滤] {raw_title} → 占位记录，已跳过')
            data.remove(job)
            filtered += 1
            continue

        # 级别推断
        level = _infer_level(raw_title, std_title)
        # 技术栈推断
        stack = _infer_stack(std_title, job)
        # 置信度
        confidence = _calc_confidence(raw_title, std_title)

        job['standardized_title'] = std_title
        job['canonical_key'] = _get_canonical_key(std_title)
        job['level'] = level
        job['stack'] = stack
        job['title_confidence'] = confidence

        # 记录映射表
        if raw_title not in title_mapping:
            title_mapping[raw_title] = {
                'standardized': std_title,
                'canonical_key': _get_canonical_key(std_title),
                'level': level,
                'stack': stack,
                'confidence': confidence,
                'sample_company': job.get('company', ''),
            }

    # 保存回写
    with open(input_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[Step 2] 已回写 → {input_path}")

    # 保存映射表
    mapping_path = os.path.join(OUTPUT_DIR, 'title_mapping_iflytek.json')
    with open(mapping_path, 'w', encoding='utf-8') as f:
        json.dump(title_mapping, f, ensure_ascii=False, indent=2)
    print(f"[Step 2] 映射表已保存 → {mapping_path}")
    print(f"[Step 2] 过滤占位记录: {filtered} 条")
    print(f"[Step 2] 有效记录: {len(data)} 条")
    print(f"[Step 2] 唯一原始title: {len(title_mapping)} 个")
    print(f"[Step 2] 唯一标准化title: {len(set(j['standardized_title'] for j in data))} 个")

    return input_path


def _normalize_title(raw_title):
    """
    完整标准化流程:
    "AI研究院-中级研究算法工程师-医疗方向(J12559)" → "研究算法工程师"
    """
    t = raw_title.strip()
    # 0. 特殊处理：无连词符的部门前缀
    if t.startswith('城市军团AIPC业务'):
        t = t.replace('城市军团AIPC业务', '').strip()
    if t.startswith('政法军团'):
        t = t.replace('政法军团', '').strip()
    # 1. 去掉J编号
    t = re.sub(r'\(J\d+\)', '', t).strip()
    # 2. 去掉部门前缀
    for dept in DEPT_PREFIXES:
        if t.startswith(dept + '-'):
            t = t[len(dept) + 1:].strip()
            break
    # 3. 去掉级别
    t, _ = _strip_level(t)
    # 4. 去掉城市后缀（含 "合肥/深圳" 双城市格式）
    t = _strip_city(t)
    # 5. 去掉方向后缀
    t = re.sub(r'[-/][^-/]*方向$', '', t).strip()
    t = re.sub(r'[-/]通用$', '', t).strip()
    t = re.sub(r'[-/]内容$', '', t).strip()
    t = re.sub(r'[-/]资源$', '', t).strip()
    t = re.sub(r'[-/]智能$', '', t).strip()
    t = re.sub(r'-AI资源$', '', t).strip()
    t = re.sub(r'-硬件方向$', '', t).strip()
    t = re.sub(r'-基建方向$', '', t).strip()
    t = re.sub(r'-工程前端$', '', t).strip()
    t = re.sub(r'-成本工程师$', '', t).strip()
    t = re.sub(r'-大数据-JAVA$', '', t).strip()
    t = re.sub(r'^研究算法[-/]', '', t).strip()
    # 6. 清理
    t = re.sub(r'\s+', '', t)
    t = t.strip('-').strip()
    # 7. 特殊处理
    if t in ('通用', '运营商'):
        return '运营商通用岗位'
    if t.startswith('会计师-') or t.endswith('会计师-'):
        t = t.replace('会计师-', '').strip()
        return '财务BP'
    return t if t else raw_title


def _strip_level(title):
    """剥离级别关键词，返回 (clean_title, level)"""
    for kw in ['高级', '资深']:
        if kw in title:
            return title.replace(kw, '').strip(), 'senior'
    if '中级' in title:
        return title.replace('中级', '').strip(), 'mid'
    if '初级' in title or '助理' in title:
        return title.replace('初级', '').replace('助理', '').strip(), 'junior'
    return title.strip(), 'mid'


def _strip_city(title):
    """去掉末尾城市后缀"""
    # 双城市 "合肥/深圳"
    for c1 in CITIES:
        for c2 in CITIES:
            if c1 != c2:
                suffix = f'-{c1}/{c2}'
                if title.endswith(suffix):
                    return title[:-len(suffix)].strip()
    # 单城市
    for city in CITIES:
        suffix = f'-{city}'
        if title.endswith(suffix):
            return title[:-len(suffix)].strip()
    return title.strip()


def _infer_level(raw_title, std_title):
    """推断岗位级别"""
    for kw in ['高级', '资深', '专家', '总监', '高阶', '首席']:
        if kw in raw_title:
            return 'senior'
    if '中级' in raw_title:
        return 'mid'
    if '初级' in raw_title or '助理' in raw_title:
        return 'junior'
    return 'mid'


# 非技术岗黑名单 → 强制指定 stack
NON_TECH_STACK_MAP = {
    'HRBP': 'hr',
    '招聘调配管理师': 'hr',
    '品牌经理': 'sales',
    '品牌经理-品牌内容': 'sales',
    '品牌经理-品牌资源': 'sales',
    '产品销售客户经理': 'sales',
    '解决方案客户经理': 'sales',
    '客户经理': 'sales',
    '渠道经理': 'sales',
    '渠道销售经理': 'sales',
    '销售经理': 'sales',
    '硬件销售经理': 'sales',
    '高阶运营商渠道经理': 'sales',
    '售前咨询经理': 'sales',
    '产品线市场经理': 'sales',
    '区域市场经理': 'sales',
    '客户群市场经理': 'sales',
    '市场经理': 'sales',
    '法律科技高阶市场/渠道': 'sales',
    '财务BP': 'finance',
    '证券行业专家': 'finance',
    '风控行业专家': 'finance',
    '校园运营': 'operation',
    '运营管理师': 'operation',
    '数据中台运营': 'operation',
    '产品运营经理': 'operation',
    '仓储管理': 'operation',
    '采购工程师': 'operation',
    '履约管理工程师': 'operation',
    '计划工程师': 'operation',
    '供应商管理工程师': 'operation',
    '供应链管理部总监': 'operation',
    '项目经理（上海LT）': 'operation',
    '项目经理（北方多语种方向）': 'operation',
    '交付项目经理': 'operation',
    '研发项目经理': 'operation',
    '产研项目经理': 'operation',
    '客服产品经理': 'product',
    '平台硬件产品经理': 'product',
    '平台软件产品经理': 'product',
    '交付产品经理': 'product',
    '解决方案产品经理': 'product',
    '行业应用产品经理': 'product',
    '机器人硬件产品经理': 'product',
    '高阶硬件产品经理': 'product',
    'TOC硬件产品经理': 'product',
    '产品经理': 'product',
    'AI技术产品经理': 'product',
    '品牌经理': 'sales',
    '服务支持专员（粤语）': 'unknown',
    '服务支持专员（英语）': 'unknown',
    '服务支持专员（葡语）': 'unknown',
    '实施工程师': 'operation',
}


def _infer_stack(std_title, job):
    """
    从标准化名称+JD综合推断技术方向
    返回 backend/frontend/ai/data/devops/mobile/embedded/test/hardware/sales/hr/finance/operation/unknown
    """
    # 黑名单优先匹配
    if std_title in NON_TECH_STACK_MAP:
        return NON_TECH_STACK_MAP[std_title]

    text = std_title
    jd = (job.get('jd_text') or '') + ' ' + (job.get('requirements') or '')
    combined = text + ' ' + jd

    scores = {}
    for stack_key, keywords in STACK_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw in text:
                score += 3  # title中权重高
            if kw in jd:
                score += 1
        if score > 0:
            scores[stack_key] = score

    if not scores:
        return 'unknown'
    return max(scores, key=scores.get)


def _calc_confidence(raw_title, std_title):
    """
    标准化置信度:
    如果改动很小（仅去掉编号/部门前缀）→ 高
    如果大幅改动 → 中
    """
    raw_clean = re.sub(r'\(J\d+\)', '', raw_title).strip()
    if raw_clean == std_title:
        return 1.0
    # 仅去掉前缀/级别
    t = raw_clean
    for dept in DEPT_PREFIXES:
        if t.startswith(dept + '-'):
            t = t[len(dept) + 1:].strip()
            break
    t = re.sub(r'中级|高级|资深', '', t).strip()
    if t == std_title:
        return 0.95
    if len(std_title) / max(len(raw_clean), 1) > 0.5:
        return 0.85
    return 0.75


def _get_canonical_key(std_title):
    """获取canonical_key"""
    if std_title in CANONICAL_MAP:
        return CANONICAL_MAP[std_title]
    # 自动生成
    key = std_title.lower()
    key = re.sub(r'[（）()（）]', '', key)
    key = re.sub(r'[-/]', '-', key)
    key = re.sub(r'\s+', '-', key)
    return key


# ================================================================
# 主流程
# ================================================================
if __name__ == '__main__':
    input_file = '科大讯飞.json'

    print("=" * 60)
    print("科大讯飞岗位数据清洗流水线")
    print("=" * 60)

    # Step 1
    merged_path = step1_merge_clean(input_file)

    # Step 2
    step2_normalize_titles(merged_path)

    # 统计输出
    print("\n" + "=" * 60)
    print("清洗完成！")
    print("=" * 60)
    print(f"输出文件:")
    print(f"  {merged_path}")
    print(f"  {os.path.join(OUTPUT_DIR, 'title_mapping_iflytek.json')}")

import csv
# 导出CSV，适配入库脚本读取
out_csv_name = "岗位数据_清洗完成.csv"
if final_data:
    field_names = final_data[0].keys()
    with open(out_csv_name, "w", newline="", encoding="utf-8-sig") as fw:
        writer = csv.DictWriter(fw, fieldnames=field_names)
        writer.writeheader()
        writer.writerows(final_data)
    print(f"\n✅ 已生成文件：{out_csv_name}")