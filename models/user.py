from werkzeug.security import generate_password_hash, check_password_hash
from db import get_connection


class User:
    def __init__(self, id=None, username=None, email=None,
                 password_hash=None, is_verified=False):
        self.id = id
        self.username = username
        self.email = email
        self.__password_hash = password_hash   # private: hidden from outside code
        self.is_verified = is_verified

    def set_password(self, password):
        self.__password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.__password_hash, password)

    def save(self):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                (self.username, self.email, self.__password_hash),
            )
            conn.commit()
            self.id = cur.lastrowid
        finally:
            conn.close()

    def update_profile(self, username, email):
        """Changes the username and email. Raises IntegrityError if either is taken."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE users SET username = %s, email = %s WHERE id = %s",
                (username, email, self.id),
            )
            conn.commit()
        finally:
            conn.close()
        self.username = username
        self.email = email

    def update_password(self, new_password):
        """Hashes the new password and saves it."""
        self.set_password(new_password)
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (self.__password_hash, self.id),
            )
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def _find(cls, column, value):
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(f"SELECT * FROM users WHERE {column} = %s", (value,))
            row = cur.fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return cls(row["id"], row["username"], row["email"],
                   row["password_hash"], bool(row["is_verified"]))

    @classmethod
    def find_by_email(cls, email):
        return cls._find("email", email)

    @classmethod
    def find_by_username(cls, username):
        return cls._find("username", username)

    @classmethod
    def find_by_id(cls, user_id):
        return cls._find("id", user_id)