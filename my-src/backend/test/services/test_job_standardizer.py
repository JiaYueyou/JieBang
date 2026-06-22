"""岗位标题标准化规则测试。"""

from app.domain.job_standardizer import infer_job_stack, standardize_job_title


def test_standardize_title_removes_noise_but_keeps_specialization():
    name, key, level, confidence = standardize_job_title(
        "急聘 高级 Python 后端开发工程师（双休）"
    )
    assert name == "Python后端开发工程师"
    assert key == "python后端开发工程师"
    assert level == "senior"
    assert confidence >= 0.9


def test_stack_and_level_inference():
    assert infer_job_stack("大模型算法工程师") == "ai"
    assert infer_job_stack("Flink 数据开发工程师") == "data"
    assert infer_job_stack("SRE 运维工程师") == "devops"
