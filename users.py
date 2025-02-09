import secrets
from flask import session
from sqlalchemy.sql import text
from werkzeug.security import check_password_hash, generate_password_hash
from db import db

def login(username, password):
    sql = text("SELECT id, password_hash, role FROM users WHERE username=:username")
    result = db.session.execute(sql, {"username":username})
    user = result.fetchone()
    if user == None:
        return False
    else:
        if check_password_hash(user.password_hash, password):
            session["username"] = username
            session["csrf_token"] = secrets.token_hex(16)
            session["user_id"] = user.id
            session["role"] = user.role
            return True
        return False


def logout():
    del session["user_id"]
    del session["username"]
    del session["csrf_token"]
    if "role" in session:
        del session["role"]


def create_account(username, password):
    # Tarkista, onko käyttäjänimi jo käytössä
    sql = text("SELECT id FROM users WHERE username=:username")
    result = db.session.execute(sql, {"username": username})
    user = result.fetchone()
    if user:
        return False  # Käyttäjänimi on jo käytössä

    # Luo salasanan hash
    hash_value = generate_password_hash(password)

    try:
        # Lisää käyttäjä tietokantaan
        sql = text("INSERT INTO users (username, password_hash) VALUES (:username, :password) RETURNING id")
        result = db.session.execute(sql, {"username": username, "password": hash_value})
        user_id = result.fetchone()[0]
        db.session.commit()

        # Tallenna käyttäjän tiedot istuntoon
        session["username"] = username
        session["csrf_token"] = secrets.token_hex(16)
        session["user_id"] = user_id
        session["role"] = "user"
        
        return True
    except Exception as e:
        print(f"Error creating account: {e}")  # Tulosta tarkka virhekehityksessä
        return False



