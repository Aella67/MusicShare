import secrets

import mysql.connector

from db import get_connection

# No 0/O or 1/I, so codes are easy to read out loud and type
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
COLUMNS = "id, host_id, playlist_id, name, share_code, status"


class Room:
    def __init__(self, id, host_id, playlist_id, name, share_code=None, status="open"):
        self.id = id
        self.host_id = host_id
        self.playlist_id = playlist_id
        self.name = name
        self.share_code = share_code
        self.status = status

    @staticmethod
    def _new_code(length=6):
        return "".join(secrets.choice(CODE_ALPHABET) for _ in range(length))

    @property
    def is_open(self):
        return self.status == "open"

    def save(self):
        """Insert the room with a random unique share code."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            for _ in range(5):
                self.share_code = self._new_code()
                try:
                    cur.execute(
                        "INSERT INTO rooms (host_id, playlist_id, name, share_code) "
                        "VALUES (%s, %s, %s, %s)",
                        (self.host_id, self.playlist_id, self.name, self.share_code),
                    )
                    conn.commit()
                    self.id = cur.lastrowid
                    return
                except mysql.connector.IntegrityError as err:
                    if err.errno != 1062:  # 1062 = duplicate share code, try another
                        raise
            raise RuntimeError("Could not generate a unique room code.")
        finally:
            conn.close()

    def close(self):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE rooms SET status = 'closed' WHERE id = %s", (self.id,))
            conn.commit()
            self.status = "closed"
        finally:
            conn.close()

    def save_state(self, index, position, playing):
        """Remember what the host's player is doing right now."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE rooms SET current_index = %s, position_seconds = %s, "
                "is_playing = %s, state_updated_at = NOW() WHERE id = %s",
                (index, position, 1 if playing else 0, self.id),
            )
            conn.commit()
        finally:
            conn.close()

    def get_state(self):
        """What the host's player is doing, adjusted for time passed since the last update."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT current_index, position_seconds, is_playing, "
                "COALESCE(TIMESTAMPDIFF(SECOND, state_updated_at, NOW()), 0) "
                "FROM rooms WHERE id = %s",
                (self.id,),
            )
            index, position, playing, elapsed = cur.fetchone()
        finally:
            conn.close()
        if playing:
            position = position + elapsed  # the song kept playing since the last update
        return {"index": index, "position": float(position), "playing": bool(playing)}

    @classmethod
    def _find(cls, column, value):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(f"SELECT {COLUMNS} FROM rooms WHERE {column} = %s", (value,))
            row = cur.fetchone()
            return cls(*row) if row else None
        finally:
            conn.close()

    @classmethod
    def find_by_id(cls, room_id):
        return cls._find("id", room_id)

    @classmethod
    def find_by_code(cls, code):
        return cls._find("share_code", code.strip().upper())

    @classmethod
    def find_by_host(cls, host_id):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                f"SELECT {COLUMNS} FROM rooms WHERE host_id = %s ORDER BY id DESC",
                (host_id,),
            )
            return [cls(*row) for row in cur.fetchall()]
        finally:
            conn.close()