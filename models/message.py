from db import get_connection

MAX_LENGTH = 300


class Message:
    """One chat message sent by someone in a room."""

    def __init__(self, id, room_id, display_name, body):
        self.id = id
        self.room_id = room_id
        self.display_name = display_name
        self.body = body

    def to_dict(self):
        return {"id": self.id, "name": self.display_name, "body": self.body}

    def save(self):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO messages (room_id, display_name, body) VALUES (%s, %s, %s)",
                (self.room_id, self.display_name, self.body),
            )
            conn.commit()
            self.id = cur.lastrowid
        finally:
            conn.close()

    @classmethod
    def find_since(cls, room_id, since_id, limit=50):
        """Messages in this room newer than since_id, oldest first."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, room_id, display_name, body FROM messages "
                "WHERE room_id = %s AND id > %s ORDER BY id LIMIT %s",
                (room_id, since_id, limit),
            )
            return [cls(*row) for row in cur.fetchall()]
        finally:
            conn.close()

    @classmethod
    def find_recent(cls, room_id, limit=30):
        """The newest messages in the room, oldest first, to show when the page opens."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, room_id, display_name, body FROM messages "
                "WHERE room_id = %s ORDER BY id DESC LIMIT %s",
                (room_id, limit),
            )
            rows = cur.fetchall()
        finally:
            conn.close()
        return [cls(*row) for row in reversed(rows)]