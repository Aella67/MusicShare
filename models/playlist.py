from db import get_connection


class Playlist:
    def __init__(self, id, user_id, name):
        self.id = id
        self.user_id = user_id
        self.name = name

    def save(self):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO playlists (user_id, name) VALUES (%s, %s)",
                (self.user_id, self.name),
            )
            conn.commit()
            self.id = cur.lastrowid
        finally:
            conn.close()

    @classmethod
    def find_by_user(cls, user_id):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, user_id, name FROM playlists "
                "WHERE user_id = %s ORDER BY id DESC",
                (user_id,),
            )
            return [cls(*row) for row in cur.fetchall()]
        finally:
            conn.close()

    @classmethod
    def find_by_id(cls, playlist_id):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, user_id, name FROM playlists WHERE id = %s",
                (playlist_id,),
            )
            row = cur.fetchone()
            return cls(*row) if row else None
        finally:
            conn.close()