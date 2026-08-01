"""岗位标题标准化规则测试。"""

from app.domain.job_standardizer import infer_job_stack, normalize_job_title, standardize_job_title


def test_standardize_title_removes_noise_but_keeps_specialization():
    name, key, level, confidence = standardize_job_title(
        "急聘 高级 Python 后端开发工程师（双休）"
    )
    assert name == "Python后端开发工程师"
    assert key == "python后端开发工程师:senior"
    assert level == "senior"
    assert confidence >= 0.9


def test_stack_and_level_inference():
    assert infer_job_stack("大模型算法工程师") == "ai"
    assert infer_job_stack("Flink 数据开发工程师") == "data"
    assert infer_job_stack("SRE 运维工程师") == "devops"


def test_region_and_company_are_dimensions_not_standard_job_identity():
    beijing = normalize_job_title(
        "北京-高级 Java 研发工程师（双休）",
        city="北京市",
        company="示例科技有限公司",
    )
    shanghai = normalize_job_title(
        "高级 Java 开发工程师-上海",
        city="上海",
        company="示例科技公司",
    )
    assert beijing.canonical_key == shanghai.canonical_key
    assert beijing.city_code == "110000"
    assert shanghai.city_code == "310000"
    assert beijing.company_key == shanghai.company_key == "示例科技"
    assert beijing.version == "job-title-v2"


def test_seniority_is_part_of_standard_job_identity():
    senior = normalize_job_title("高级 Python 开发工程师")
    junior = normalize_job_title("初级 Python 开发工程师")
    assert senior.name == junior.name
    assert senior.canonical_key != junior.canonical_key
    assert senior.occupation_code != junior.occupation_code
