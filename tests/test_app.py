import pytest
import json
from app import app, db, User, Expense, AuditLog

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///:memory:"  # временная БД
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()


def register_and_login(client):
    # Регистрация
    rv = client.post("/register", json={"username": "testuser", "password": "123"})
    assert rv.status_code == 200

    # Логин
    rv = client.post("/login", json={"username": "testuser", "password": "123"})
    assert rv.status_code == 200


def test_crud_and_audit(client):
    register_and_login(client)

    # Добавление расхода
    rv = client.post("/add", json={"amount": 100, "category": "еда", "description": "пицца"})
    data = rv.get_json()
    expense_id = data["id"]
    assert rv.status_code == 200
    assert data["message"] == "Expense added"

    # Проверка аудита после добавления
    audit = AuditLog.query.filter_by(expense_id=expense_id, action="add").first()
    assert audit is not None

    # Просмотр расходов
    rv = client.get("/list")
    data = rv.get_json()
    assert len(data) == 1
    assert data[0]["amount"] == 100

    # Редактирование расхода
    rv = client.post("/edit", json={"id": expense_id, "amount": 150, "description": "пицца обновлена"})
    data = rv.get_json()
    assert rv.status_code == 200
    assert data["message"] == "Expense updated"

    # Проверка аудита после редактирования
    audit = AuditLog.query.filter_by(expense_id=expense_id, action="edit").first()
    assert audit is not None

    # Удаление расхода
    rv = client.post("/delete", json={"id": expense_id})
    data = rv.get_json()
    assert rv.status_code == 200
    assert data["message"] == "Expense deleted"

    # Проверка аудита после удаления
    audit = AuditLog.query.filter_by(expense_id=expense_id, action="delete").first()
    assert audit is not None
