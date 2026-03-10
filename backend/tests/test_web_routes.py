"""
Flask 路由集成测试

使用 Flask test client + SQLite 内存数据库，验证 API 路由的请求/响应。
不依赖外部服务。

覆盖路由：
- GET  /api/status
- GET  /api/history
- GET  /api/search
- GET  /api/stats
- DELETE /api/question/<id>
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from db.models import Base
from db import crud


@pytest.fixture
def test_db():
    """内存数据库 + 建表"""
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(test_db):
    """Flask test client，用内存数据库替换 SessionLocal"""
    # 创建一个 context manager 代理，让 with SessionLocal() as db 使用 test_db
    class FakeSessionLocal:
        def __call__(self):
            return self

        def __enter__(self):
            return test_db

        def __exit__(self, *args):
            pass

    with patch("web_app.SessionLocal", FakeSessionLocal()):
        from web_app import app
        app.config["TESTING"] = True
        with app.test_client() as c:
            yield c


# ── /api/status ──────────────────────────────────────────


class TestStatusRoute:
    """GET /api/status"""

    def test_returns_success(self, client):
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "status" in data

    def test_contains_model_info(self, client):
        resp = client.get("/api/status")
        status = resp.get_json()["status"]
        assert "available_models" in status
        assert isinstance(status["available_models"], list)
        assert len(status["available_models"]) >= 1


# ── /api/history ─────────────────────────────────────────


class TestHistoryRoute:
    """GET /api/history"""

    def test_empty_history(self, client):
        resp = client.get("/api/history")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["items"] == []
        assert data["total"] == 0

    def test_pagination_params(self, client):
        resp = client.get("/api/history?page=1&page_size=5")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["page"] == 1
        assert data["page_size"] == 5

    def test_invalid_date_format(self, client):
        resp = client.get("/api/history?start_date=not-a-date")
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False


# ── /api/search ──────────────────────────────────────────


class TestSearchRoute:
    """GET /api/search"""

    def test_requires_search_param(self, client):
        """无搜索条件应返回 400"""
        resp = client.get("/api/search")
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False

    def test_search_by_keyword(self, client):
        resp = client.get("/api/search?keyword=导数")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "items" in data

    def test_search_by_question_type(self, client):
        resp = client.get("/api/search?question_type=选择题")
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True


# ── /api/stats ───────────────────────────────────────────


class TestStatsRoute:
    """GET /api/stats"""

    def test_empty_stats(self, client):
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["total_tags"] == 0


# ── DELETE /api/question/<id> ────────────────────────────


class TestDeleteQuestionRoute:
    """DELETE /api/question/<id>"""

    def test_delete_nonexistent(self, client):
        resp = client.delete("/api/question/99999")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["success"] is False

    def test_delete_existing(self, client, test_db):
        """先入库再删除"""
        from db.crud import save_questions_to_db

        qs = [{
            "question_id": "1",
            "question_type": "选择题",
            "content_blocks": [{"block_type": "text", "content": "测试题目"}],
            "has_formula": False,
            "has_image": False,
        }]
        save_questions_to_db(test_db, qs, {
            "original_filename": "test.pdf",
            "subject": "数学",
        })

        # 查询刚插入的题目 ID
        from db.models import Question
        q = test_db.query(Question).first()
        assert q is not None

        resp = client.delete(f"/api/question/{q.id}")
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True


# ── /api/error-bank ────────────────────────────────────


class TestErrorBankRoute:
    """GET /api/error-bank"""

    def test_empty(self, client):
        resp = client.get("/api/error-bank")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["items"] == []
        assert data["total"] == 0

    def test_with_filters(self, client):
        resp = client.get("/api/error-bank?subject=数学&question_type=选择题")
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_pagination(self, client):
        resp = client.get("/api/error-bank?page=1&page_size=5")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["page"] == 1
        assert data["page_size"] == 5

    def test_invalid_date(self, client):
        resp = client.get("/api/error-bank?start_date=bad")
        assert resp.status_code == 400

    def test_with_data(self, client, test_db):
        from db.crud import save_questions_to_db
        qs = [{
            "question_id": "1",
            "question_type": "选择题",
            "content_blocks": [{"block_type": "text", "content": "错题库测试"}],
            "has_formula": False,
            "has_image": False,
        }]
        save_questions_to_db(test_db, qs, {
            "original_filename": "test.pdf",
            "subject": "数学",
        })
        resp = client.get("/api/error-bank")
        data = resp.get_json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert item["subject"] == "数学"
        assert "knowledge_tags" in item


# ── /api/subjects ──────────────────────────────────────


class TestSubjectsRoute:
    """GET /api/subjects"""

    def test_empty(self, client):
        resp = client.get("/api/subjects")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["subjects"] == []

    def test_with_data(self, client, test_db):
        from db.crud import save_questions_to_db
        save_questions_to_db(test_db, [{
            "question_id": "1",
            "question_type": "选择题",
            "content_blocks": [{"block_type": "text", "content": "t"}],
            "has_formula": False, "has_image": False,
        }], {"original_filename": "a.pdf", "subject": "高中数学"})
        resp = client.get("/api/subjects")
        assert "高中数学" in resp.get_json()["subjects"]


# ── /api/question-types ────────────────────────────────


class TestQuestionTypesRoute:
    """GET /api/question-types"""

    def test_empty(self, client):
        resp = client.get("/api/question-types")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["question_types"] == []


# ── PATCH /api/question/<id>/answer ────────────────────


class TestUpdateAnswerRoute:
    """PATCH /api/question/<id>/answer"""

    def test_missing_field(self, client):
        resp = client.patch("/api/question/1/answer", json={})
        assert resp.status_code == 400

    def test_nonexistent(self, client):
        resp = client.patch("/api/question/99999/answer", json={"user_answer": "A"})
        assert resp.status_code == 404

    def test_save_answer(self, client, test_db):
        from db.crud import save_questions_to_db
        save_questions_to_db(test_db, [{
            "question_id": "1",
            "question_type": "选择题",
            "content_blocks": [{"block_type": "text", "content": "答案测试"}],
            "has_formula": False, "has_image": False,
        }], {"original_filename": "a.pdf", "subject": "数学"})
        from db.models import Question
        q = test_db.query(Question).first()
        resp = client.patch(f"/api/question/{q.id}/answer", json={"user_answer": "选B"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["user_answer"] == "选B"


# ── POST /api/export-from-db ──────────────────────────


class TestExportFromDbRoute:
    """POST /api/export-from-db"""

    def test_empty_ids(self, client):
        resp = client.post("/api/export-from-db", json={"selected_ids": []})
        assert resp.status_code == 400

    def test_nonexistent_ids(self, client):
        resp = client.post("/api/export-from-db", json={"selected_ids": [99999]})
        assert resp.status_code == 404


# ── PATCH /api/question/<id>/review-status ────────────


class TestUpdateReviewStatusRoute:
    """PATCH /api/question/<id>/review-status"""

    def test_missing_field(self, client):
        resp = client.patch("/api/question/1/review-status", json={})
        assert resp.status_code == 400

    def test_invalid_status(self, client, test_db):
        from db.crud import save_questions_to_db
        save_questions_to_db(test_db, [{
            "question_id": "1",
            "question_type": "选择题",
            "content_blocks": [{"block_type": "text", "content": "状态测试"}],
            "has_formula": False, "has_image": False,
        }], {"original_filename": "a.pdf", "subject": "数学"})
        from db.models import Question
        q = test_db.query(Question).first()
        resp = client.patch(f"/api/question/{q.id}/review-status", json={"review_status": "无效"})
        assert resp.status_code == 400

    def test_nonexistent(self, client):
        resp = client.patch("/api/question/99999/review-status", json={"review_status": "已掌握"})
        assert resp.status_code == 404

    def test_update_status(self, client, test_db):
        from db.crud import save_questions_to_db
        save_questions_to_db(test_db, [{
            "question_id": "1",
            "question_type": "选择题",
            "content_blocks": [{"block_type": "text", "content": "复习状态测试"}],
            "has_formula": False, "has_image": False,
        }], {"original_filename": "a.pdf", "subject": "数学"})
        from db.models import Question
        q = test_db.query(Question).first()
        resp = client.patch(f"/api/question/{q.id}/review-status", json={"review_status": "已掌握"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["review_status"] == "已掌握"


# ── GET /api/dashboard-stats ─────────────────────────


class TestDashboardStatsRoute:
    """GET /api/dashboard-stats"""

    def test_empty(self, client):
        resp = client.get("/api/dashboard-stats")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "review_stats" in data
        assert "total_questions" in data
        assert "daily_counts" in data
        assert "tag_stats" in data

    def test_with_data(self, client, test_db):
        from db.crud import save_questions_to_db
        save_questions_to_db(test_db, [{
            "question_id": "1",
            "question_type": "选择题",
            "content_blocks": [{"block_type": "text", "content": "统计测试"}],
            "has_formula": False, "has_image": False,
            "knowledge_tags": ["导数"],
        }], {"original_filename": "a.pdf", "subject": "数学"})
        resp = client.get("/api/dashboard-stats")
        data = resp.get_json()
        assert data["total_questions"] == 1
        assert len(data["daily_counts"]) == 7


# ── GET /api/error-bank?review_status ────────────────


class TestErrorBankReviewStatusFilter:
    """GET /api/error-bank with review_status filter"""

    def test_filter_by_review_status(self, client, test_db):
        from db.crud import save_questions_to_db, update_review_status
        save_questions_to_db(test_db, [
            {
                "question_id": "1",
                "question_type": "选择题",
                "content_blocks": [{"block_type": "text", "content": "待复习题"}],
                "has_formula": False, "has_image": False,
            },
            {
                "question_id": "2",
                "question_type": "选择题",
                "content_blocks": [{"block_type": "text", "content": "已掌握题"}],
                "has_formula": False, "has_image": False,
            },
        ], {"original_filename": "a.pdf", "subject": "数学"})
        from db.models import Question
        qs = test_db.query(Question).all()
        update_review_status(test_db, qs[1].id, "已掌握")

        resp = client.get("/api/error-bank?review_status=已掌握")
        data = resp.get_json()
        assert data["total"] == 1
        assert data["items"][0]["review_status"] == "已掌握"


# ── POST /api/ai-analysis ─────────────────────────────


class TestAiAnalysisRoute:
    """POST /api/ai-analysis"""

    def test_empty_ids(self, client):
        resp = client.post("/api/ai-analysis", json={"question_ids": []})
        assert resp.status_code == 400

    def test_missing_ids(self, client):
        resp = client.post("/api/ai-analysis", json={})
        assert resp.status_code == 400

    def test_too_many_ids(self, client):
        resp = client.post("/api/ai-analysis", json={"question_ids": list(range(1, 22))})
        assert resp.status_code == 400

    def test_nonexistent_ids(self, client):
        resp = client.post("/api/ai-analysis", json={"question_ids": [99999]})
        assert resp.status_code == 404

    def test_success(self, client, test_db):
        from db.crud import save_questions_to_db
        save_questions_to_db(test_db, [{
            "question_id": "1",
            "question_type": "选择题",
            "content_blocks": [{"block_type": "text", "content": "AI分析测试"}],
            "has_formula": False, "has_image": False,
            "knowledge_tags": ["导数"],
        }], {"original_filename": "a.pdf", "subject": "数学"})
        from db.models import Question
        q = test_db.query(Question).first()
        resp = client.post("/api/ai-analysis", json={"question_ids": [q.id]})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "analysis" in data
        analysis = data["analysis"]
        assert "summary" in analysis
        assert "weak_points" in analysis
        assert "suggestions" in analysis
        assert "per_question" in analysis
        assert len(analysis["per_question"]) == 1
