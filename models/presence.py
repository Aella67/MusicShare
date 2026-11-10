from db import get_connection


class Presence:
    """Who is in a room right now. Each room page pings every few seconds;
    anyone who hasn't pinged recently is treated as gone."""

    @staticmethod
    def touch(room_id, display_name):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO room_presence (room_id, display_name, last_seen) "
                "VALUES (%s, %s, NOW()) "
                "ON DUPLICATE KEY UPDATE last_seen = NOW()",
                (room_id, display_name),
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def online(room_id, seconds=12):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT display_name FROM room_presence "
                "WHERE room_id = %s AND last_seen >= NOW() - INTERVAL %s SECOND "
                "ORDER BY display_name",
                (room_id, seconds),
            )
            return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()