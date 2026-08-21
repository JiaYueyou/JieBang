from app.services.resume_profile_extractor import ResumeProfileExtractor


def test_extracts_labelled_profile_fields_without_external_model():
    profile = ResumeProfileExtractor().extract(
        "姓名：张三\n求职意向：AI 应用工程师\n手机：138 0013 8000\n邮箱：ZHANG.SAN@example.com\n5年工作经验\n教育背景：某大学计算机硕士"
    )

    assert profile == {
        "name": "张三",
        "current_position": "AI 应用工程师",
        "experience": "5年",
        "education": "硕士",
        "phone": "13800138000",
        "email": "zhang.san@example.com",
    }


def test_profile_pseudonym_is_stable_and_does_not_expose_name():
    extractor = ResumeProfileExtractor()

    first = extractor.pseudonym("张三", "ignored")
    second = extractor.pseudonym("张三", "other text")

    assert first == second
    assert "张三" not in first


def test_extracts_extended_position_labels_and_role_fallback():
    extractor = ResumeProfileExtractor()

    assert extractor.extract("期望岗位：算法工程师\n技能：Python")["current_position"] == "算法工程师"
    assert extractor.extract("个人优势\n曾任后端开发并负责平台建设")["current_position"] == "后端开发"


def test_contact_fields_are_none_when_resume_does_not_contain_them():
    profile = ResumeProfileExtractor().extract("姓名：李四\n求职意向：测试工程师")

    assert profile["phone"] is None
    assert profile["email"] is None


def test_does_not_guess_school_or_contact_label_as_a_person_name():
    extractor = ResumeProfileExtractor()

    assert extractor.extract("教育背景\n浙江大学\n计算机本科")["name"] is None
    assert extractor.extract("联系电话：\n教育经历")["name"] is None
    assert extractor.extract("海外QS前100\n项目经历")["name"] is None
