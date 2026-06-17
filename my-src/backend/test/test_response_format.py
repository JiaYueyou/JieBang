"""统一响应格式测试"""

from app.schemas.common import ApiResponse


class TestApiResponse:
    def test_success_default(self):
        r = ApiResponse(data={"key": "val"})
        d = r.model_dump()
        assert d["code"] == 200
        assert d["message"] == "success"
        assert d["data"] == {"key": "val"}
        assert d["meta"] is None

    def test_error_response(self):
        r = ApiResponse(code=40001, message="用户名或密码错误")
        d = r.model_dump()
        assert d["code"] == 40001
        assert d["data"] is None

    def test_list_response_with_meta(self):
        from app.schemas.common import PageMeta
        r = ApiResponse(data=[1, 2, 3], meta=PageMeta(page=1, page_size=20, total=100, total_pages=5))
        d = r.model_dump()
        assert d["code"] == 200
        assert d["data"] == [1, 2, 3]
        assert d["meta"]["page"] == 1
        assert d["meta"]["total"] == 100
