from urllib.parse import urlparse, parse_qs
import re

from db import get_connection

YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com",
                 "music.youtube.com", "youtu.be"}
SOUNDCLOUD_HOSTS = {"soundcloud.com", "www.soundcloud.com", "on.soundcloud.com"}
YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


class Track:
    """Base class: one song saved in a playlist."""
    source = "unknown"

    def __init__(self, id, playlist_id, source_url, title, position=0):
        self.id = id
        self.playlist_id = playlist_id
        self.source_url = source_url
        self.title = title
        self.position = position

    def media_id(self):
        raise NotImplementedError

    def save(self):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT COALESCE(MAX(position), 0) + 1 FROM tracks WHERE playlist_id = %s",
                (self.playlist_id,),
            )
            self.position = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO tracks (playlist_id, source, source_url, title, position) "
                "VALUES (%s, %s, %s, %s, %s)",
                (self.playlist_id, self.source, self.source_url, self.title, self.position),
            )
            conn.commit()
            self.id = cur.lastrowid
        finally:
            conn.close()

    def delete(self):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM tracks WHERE id = %s", (self.id,))
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def from_url(cls, playlist_id, url, title):
        """Return a YouTubeTrack or SoundCloudTrack, or None if the link isn't supported."""
        url = url.strip()
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return None
        host = (parsed.hostname or "").lower()
        if host in YOUTUBE_HOSTS:
            track = YouTubeTrack(None, playlist_id, url, title)
            return track if track.media_id() else None
        if host in SOUNDCLOUD_HOSTS:
            return SoundCloudTrack(None, playlist_id, url, title)
        return None

    @classmethod
    def find_by_id(cls, track_id):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, playlist_id, source, source_url, title, position "
                "FROM tracks WHERE id = %s",
                (track_id,),
            )
            row = cur.fetchone()
            return cls._from_row(row) if row else None
        finally:
            conn.close()

    @classmethod
    def find_by_playlist(cls, playlist_id):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, playlist_id, source, source_url, title, position "
                "FROM tracks WHERE playlist_id = %s ORDER BY position",
                (playlist_id,),
            )
            return [cls._from_row(row) for row in cur.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def _from_row(row):
        id, playlist_id, source, source_url, title, position = row
        kind = YouTubeTrack if source == "youtube" else SoundCloudTrack
        return kind(id, playlist_id, source_url, title, position)


class YouTubeTrack(Track):
    source = "youtube"

    def media_id(self):
        """The 11-character video id, or None if the link has no video."""
        parsed = urlparse(self.source_url)
        host = (parsed.hostname or "").lower()
        if host == "youtu.be":
            candidate = parsed.path.lstrip("/").split("/")[0]
        elif parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [""])[0]
        elif parsed.path.startswith(("/shorts/", "/embed/")):
            parts = parsed.path.split("/")
            candidate = parts[2] if len(parts) > 2 else ""
        else:
            candidate = ""
        return candidate if YOUTUBE_ID.match(candidate) else None


class SoundCloudTrack(Track):
    source = "soundcloud"

    def media_id(self):
        return self.source_url