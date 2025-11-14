import pytest
from app import app, db, User, Expense, AuditLog
import json

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///:memory:"  # временная БД для тестов
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()


def register_and_login(client):
    client.post("/register", json={"username": "testuser", "password": "123"})
    client.post("/login", json={"username": "testuser", "password": "123"})


def test_crud_and_audit(client):
    register_and_login(client)

    # Добавление
    rv = client.post("/add", json={"amount": 100, "category": "еда", "description": "пицца"})
    data = json.loads(rv.data)
    expense_id = data["id"]
    assert rv.status_code == 200
    assert data["message"] == "Expense added"

    # Проверяем аудит после добавления
    audit = AuditLog.query.filter_by(expense_id=expense_id, action="add").first()
    assert audit is not None

    # Просмотр
    rv = client.get("/list")
    data = json.loads(rv.data)
    assert len(data) == 1
    assert data[0]["amount"] == 100

    # Редактирование
    rv = client.post("/edit", json={"id": expense_id, "amount": 150, "description": "пицца обновлена"})
    data = json.loads(rv.data)
    assert rv.status_code == 200
    assert data["message"] == "Expense updated"

    # Проверяем аудит после редактирования
    audit = AuditLog.query.filter_by(expense_id=expense_id, action="edit").first()
    assert audit is not None

    # Удаление
    rv = client.post("/delete", json={"id": expense_id})
    data = json.loads(rv.data)
    assert rv.status_code == 200
    assert data["message"] == "Expense deleted"

    # Проверяем аудит после удаления
    audit = AuditLog.query.filter_by(expense_id=expense_id, action="delete").first()
    assert audit is not None
