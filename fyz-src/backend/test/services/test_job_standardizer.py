"""岗位标题标准化规则测试。"""

from app.domain.job_standardizer import (
    infer_job_stack,
    normalize_city_names,
    normalize_job_title,
    standardize_job_title,
)


def test_city_level_normalization_merges_suffixes_and_splits_multi_city_values():
    assert normalize_city_names("北京") == ("北京",)
    assert normalize_city_names("北京市") == ("北京",)
    assert normalize_city_names("北京、上海") == ("北京", "上海")
    assert normalize_city_names("上海北京") == ("上海", "北京")
    assert normalize_city_names("北京市、上海市、深圳市") == ("北京", "上海", "深圳")


def test_city_level_normalization_excludes_provinces_and_understands_addresses():
    assert normalize_city_names("广东省") == ()
    assert normalize_city_names("广东") == ()
    assert normalize_city_names("安徽省·合肥市") == ("合肥",)
    assert normalize_city_names("北京市 海淀区、浙江 拱墅区") == ("北京", "杭州")
    assert normalize_city_names("江西省南昌市青山湖区北京东路") == ("南昌",)


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
    assert beijing.version == "job-title-v5"


def test_seniority_is_part_of_standard_job_identity():
    senior = normalize_job_title("高级 Python 开发工程师")
    junior = normalize_job_title("初级 Python 开发工程师")
    assert senior.name == junior.name
    assert senior.canonical_key != junior.canonical_key
    assert senior.occupation_code != junior.occupation_code


def test_business_line_suffix_is_not_part_of_standard_job_identity():
    sales = normalize_job_title("大客户销售-抖音生活服务")
    product = normalize_job_title("AI产品经理-TikTok")
    fde = normalize_job_title("ForwardDeployedEngineer-火山引擎FDE")

    assert sales.name == "大客户销售"
    assert sales.canonical_key == "大客户销售:middle"
    assert product.name == "AI产品经理"
    assert product.canonical_key == "ai产品经理:middle"
    assert fde.name == "前置部署工程师"
    assert fde.role_family == "devops"


def test_business_line_prefix_is_not_part_of_standard_job_identity():
    flash_sale = normalize_job_title("闪购-Java开发工程师")
    company_label = normalize_job_title("Keeta技术-Java工程师")

    assert flash_sale.name == "Java开发工程师"
    assert flash_sale.canonical_key == "java开发工程师:middle"
    assert company_label.name == "Java开发工程师"
    assert company_label.canonical_key == flash_sale.canonical_key
    assert company_label.role_family == "backend"
