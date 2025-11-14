import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# загрузка .env
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")

db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)


# -----------------------------
# МОДЕЛИ
# -----------------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(255))

    def set_password(self, pwd):
        self.password_hash = generate_password_hash(pwd)

    def check_password(self, pwd):
        return check_password_hash(self.password_hash, pwd)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float)
    category = db.Column(db.String(100))
    description = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(50))
    user_id = db.Column(db.Integer)
    expense_id = db.Column(db.Integer, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


# -----------------------------
# LOGIN MANAGER
# -----------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# -----------------------------
# АУДИТ
# -----------------------------
def log_action(user_id, action, expense_id=None):
    entry = AuditLog(user_id=user_id, action=action, expense_id=expense_id)
    db.session.add(entry)
    db.session.commit()


# -----------------------------
# АУТЕНТИФИКАЦИЯ
# -----------------------------
@app.post("/register")
def register():
    data = request.json
    username = data["username"]
    password = data["password"]

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 400

    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User created"})


@app.post("/login")
def login():
    data = request.json
    username = data["username"]
    password = data["password"]

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    login_user(user)
    return jsonify({"message": "Logged in"})


@app.get("/logout")
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out"})


# -----------------------------
# CRUD РАСХОДОВ
# -----------------------------
@app.post("/add")
@login_required
def add_expense():
    data = request.json
    expense = Expense(
        amount=data["amount"],
        category=data["category"],
        description=data["description"],
        user_id=current_user.id
    )
    db.session.add(expense)
    db.session.commit()

    log_action(current_user.id, "add", expense.id)

    return jsonify({"message": "Expense added", "id": expense.id})


@app.get("/list")
@login_required
def list_expenses():
    expenses = Expense.query.filter_by(user_id=current_user.id).all()
    result = [
        {
            "id": e.id,
            "amount": e.amount,
            "category": e.category,
            "description": e.description
        }
        for e in expenses
    ]
    return jsonify(result)


@app.post("/edit")
@login_required
def edit_expense():
    data = request.json
    expense = Expense.query.filter_by(id=data["id"], user_id=current_user.id).first()

    if not expense:
        return jsonify({"error": "Not found"}), 404

    expense.amount = data.get("amount", expense.amount)
    expense.category = data.get("category", expense.category)
    expense.description = data.get("description", expense.description)

    db.session.commit()
    log_action(current_user.id, "edit", expense.id)

    return jsonify({"message": "Expense updated"})


@app.post("/delete")
@login_required
def delete_expense():
    data = request.json
    expense = Expense.query.filter_by(id=data["id"], user_id=current_user.id).first()

    if not expense:
        return jsonify({"error": "Not found"}), 404

    db.session.delete(expense)
    db.session.commit()
    log_action(current_user.id, "delete", data["id"])

    return jsonify({"message": "Expense deleted"})


# -----------------------------
# ЗАПУСК
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
