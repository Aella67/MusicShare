from db import get_connection

# Reactions are stored as short keys; the page turns each key into an emoji.
ALLOWED_REACTIONS = {"heart", "fire", "clap", "laugh", "wow", "music"}


class Reaction:
    """One emoji reaction sent by someone in a room."""

    def __init__(self, id, room_id, display_name, emoji):
        self.id = id
        self.room_id = room_id
        self.display_name = display_name
        self.emoji = emoji

    def save(self):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO reactions (room_id, display_name, emoji) VALUES (%s, %s, %s)",
                (self.room_id, self.display_name, self.emoji),
            )
            conn.commit()
            self.id = cur.lastrowid
        finally:
            conn.close()

    @classmethod
    def find_since(cls, room_id, since_id, limit=50):
        """Reactions in this room that are newer than since_id, oldest first."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, room_id, display_name, emoji FROM reactions "
                "WHERE room_id = %s AND id > %s ORDER BY id LIMIT %s",
                (room_id, since_id, limit),
            )
            return [cls(*row) for row in cur.fetchall()]
        finally:
            conn.close()

    @classmethod
    def latest_id(cls, room_id):
        """Id of the newest reaction in the room (0 if none), so a new page starts from 'now'."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT COALESCE(MAX(id), 0) FROM reactions WHERE room_id = %s",
                (room_id,),
            )
            return cur.fetchone()[0]
        finally:
            conn.close()