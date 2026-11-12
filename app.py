import math
import time
from functools import wraps
from flask import (Flask, render_template, redirect, url_for, flash, session,
                   abort, jsonify, request)
from flask_wtf import CSRFProtect
from flask_mail import Mail, Message as MailMessage
import mysql.connector
from config import Config
from forms import RegisterForm, LoginForm, PlaylistForm, TrackForm, RoomForm, JoinForm, GuestForm
from models.user import User
from models.playlist import Playlist
from models.track import Track
from models.room import Room
from models.reaction import Reaction, ALLOWED_REACTIONS
from models.message import Message, MAX_LENGTH
from models.presence import Presence

app = Flask(__name__)
app.config.from_object(Config)
csrf = CSRFProtect(app)
mail = Mail(app)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_current_user():
    user_id = session.get("user_id")
    return {"current_user": User.find_by_id(user_id) if user_id else None}


def viewer_name():
    """Who is looking at the page: a username, a guest's display name, or None."""
    user_id = session.get("user_id")
    if user_id:
        user = User.find_by_id(user_id)
        if user:
            return user.username
    return session.get("guest_name")


def youtube_queue(room):
    """The room's playable songs (YouTube only). The sync index points into this list."""
    tracks = Track.find_by_playlist(room.playlist_id) if room.playlist_id else []
    return [{"title": t.title, "source": t.source, "media_id": t.media_id()}
            for t in tracks if t.source == "youtube"]


def can_listen(room):
    """The host, or anyone with a name (account or guest) in an open room."""
    is_host = session.get("user_id") == room.host_id
    return is_host or (room.is_open and viewer_name() is not None)


def send_welcome_email(username, email):
    """Sends the welcome email. Returns True if it was sent, False if it failed.
    A failed email must never break registration, so errors are caught here."""
    try:
        msg = MailMessage(
            subject="Welcome to MusicShare!",
            recipients=[email],
            body=(
                f"Hi {username},\n\n"
                "Your MusicShare account is ready.\n\n"
                "You can now log in, build playlists from YouTube and SoundCloud links, "
                "create a room, and share the room code with friends so they can listen along.\n\n"
                "Happy listening!\n"
                "The MusicShare Team"
            ),
        )
        mail.send(msg)
        return True
    except Exception:
        app.logger.exception("Could not send welcome email")
        return False


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip().lower()
        user = User(None, username, email, None, False)
        user.set_password(form.password.data)
        try:
            user.save()
        except mysql.connector.IntegrityError:
            flash("That username or email is already registered.", "danger")
            return render_template("register.html", form=form)
        if send_welcome_email(username, email):
            flash("Account created! We sent a welcome email to your inbox. You can log in now.", "success")
        else:
            flash("Account created! We could not send the welcome email right now, but you can log in.", "warning")
        return redirect(url_for("login"))
    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("home"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.find_by_email(form.email.data.strip().lower())
        if user and user.check_password(form.password.data):
            session.clear()
            session["user_id"] = user.id
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(url_for("dashboard"))
        flash("Wrong email or password.", "danger")
    return render_template("login.html", form=form)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))


@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    form = PlaylistForm()
    if form.validate_on_submit():
        playlist = Playlist(None, session["user_id"], form.name.data.strip())
        playlist.save()
        flash("Playlist created!", "success")
        return redirect(url_for("dashboard"))
    playlists = Playlist.find_by_user(session["user_id"])
    rooms = Room.find_by_host(session["user_id"])
    return render_template("dashboard.html", form=form, playlists=playlists, rooms=rooms)


@app.route("/playlists/<int:playlist_id>", methods=["GET", "POST"])
@login_required
def playlist_detail(playlist_id):
    playlist = Playlist.find_by_id(playlist_id)
    if playlist is None or playlist.user_id != session["user_id"]:
        abort(404)
    form = TrackForm()
    if form.validate_on_submit():
        track = Track.from_url(playlist.id, form.url.data, form.title.data.strip())
        track.save()
        flash("Song added!", "success")
        return redirect(url_for("playlist_detail", playlist_id=playlist.id))
    tracks = Track.find_by_playlist(playlist.id)
    return render_template("playlist.html", playlist=playlist, form=form, tracks=tracks)


@app.route("/playlists/<int:playlist_id>/rename", methods=["POST"])
@login_required
def rename_playlist(playlist_id):
    playlist = Playlist.find_by_id(playlist_id)
    if playlist is None or playlist.user_id != session["user_id"]:
        abort(404)
    name = request.form.get("name", "").strip()
    if not name or len(name) > 100:
        flash("Playlist name must be 1 to 100 characters.", "danger")
    else:
        playlist.rename(name)
        flash("Playlist renamed.", "success")
    return redirect(url_for("playlist_detail", playlist_id=playlist.id))


@app.route("/playlists/<int:playlist_id>/delete", methods=["POST"])
@login_required
def delete_playlist(playlist_id):
    playlist = Playlist.find_by_id(playlist_id)
    if playlist is None or playlist.user_id != session["user_id"]:
        abort(404)
    playlist.delete()
    flash("Playlist deleted.", "info")
    return redirect(url_for("dashboard"))


@app.route("/playlists/<int:playlist_id>/tracks/<int:track_id>/rename", methods=["POST"])
@login_required
def rename_track(playlist_id, track_id):
    playlist = Playlist.find_by_id(playlist_id)
    if playlist is None or playlist.user_id != session["user_id"]:
        abort(404)
    track = Track.find_by_id(track_id)
    if track is None or track.playlist_id != playlist.id:
        abort(404)
    title = request.form.get("title", "").strip()
    if not title or len(title) > 200:
        flash("Song title must be 1 to 200 characters.", "danger")
    else:
        track.rename(title)
        flash("Song renamed.", "success")
    return redirect(url_for("playlist_detail", playlist_id=playlist.id))


@app.route("/playlists/<int:playlist_id>/tracks/<int:track_id>/delete", methods=["POST"])
@login_required
def delete_track(playlist_id, track_id):
    playlist = Playlist.find_by_id(playlist_id)
    if playlist is None or playlist.user_id != session["user_id"]:
        abort(404)
    track = Track.find_by_id(track_id)
    if track is None or track.playlist_id != playlist.id:
        abort(404)
    track.delete()
    flash("Song removed.", "info")
    return redirect(url_for("playlist_detail", playlist_id=playlist.id))


@app.route("/rooms/new", methods=["GET", "POST"])
@login_required
def new_room():
    form = RoomForm()
    playlists = Playlist.find_by_user(session["user_id"])
    form.playlist_id.choices = [(0, "No playlist yet")] + [(p.id, p.name) for p in playlists]
    if form.validate_on_submit():
        playlist_id = form.playlist_id.data or None
        room = Room(None, session["user_id"], playlist_id, form.name.data.strip())
        room.save()
        flash("Room created! Share the code or link with your listeners.", "success")
        return redirect(url_for("room_page", code=room.share_code))
    return render_template("new_room.html", form=form)


@app.route("/join", methods=["GET", "POST"])
def join():
    form = JoinForm()
    if form.validate_on_submit():
        return redirect(url_for("room_page", code=form.code.data.strip().upper()))
    return render_template("join.html", form=form)


@app.route("/room/<code>", methods=["GET", "POST"])
def room_page(code):
    room = Room.find_by_code(code)
    if room is None:
        abort(404)
    is_host = session.get("user_id") == room.host_id
    guest_form = GuestForm()
    if guest_form.validate_on_submit():
        session["guest_name"] = guest_form.display_name.data.strip()
        return redirect(url_for("room_page", code=room.share_code))
    tracks = Track.find_by_playlist(room.playlist_id) if room.playlist_id else []
    history = [m.to_dict() for m in Message.find_recent(room.id)]
    return render_template("room.html", room=room, is_host=is_host,
                           viewer=viewer_name(), guest_form=guest_form,
                           tracks=tracks, queue=youtube_queue(room),
                           state=room.get_state(),
                           last_reaction_id=Reaction.latest_id(room.id),
                           chat_history=history,
                           last_message_id=history[-1]["id"] if history else 0)


@app.route("/room/<code>/delete", methods=["POST"])
@login_required
def delete_room(code):
    room = Room.find_by_code(code)
    if room is None or room.host_id != session["user_id"]:
        abort(404)
    room.delete()
    flash("Room deleted.", "info")
    return redirect(url_for("dashboard"))


@app.route("/room/<code>/state", methods=["GET", "POST"])
def room_state(code):
    """GET: anyone in the room reads what the host's player is doing.
    POST: only the host updates it (checked here on the server)."""
    room = Room.find_by_code(code)
    if room is None:
        abort(404)
    is_host = session.get("user_id") == room.host_id

    if request.method == "GET":
        if not (is_host or (room.is_open and viewer_name())):
            abort(403)
        return jsonify(room.get_state())

    if not is_host:
        abort(403)
    data = request.get_json(silent=True) or {}
    try:
        index = int(data.get("index"))
        position = float(data.get("position"))
    except (TypeError, ValueError):
        abort(400)
    playing = bool(data.get("playing"))
    if not math.isfinite(position) or position < 0 or position > 86400:
        abort(400)
    if index < 0 or index >= len(youtube_queue(room)):
        abort(400)
    room.save_state(index, position, playing)
    return jsonify({"ok": True})


@app.route("/room/<code>/listeners")
def room_listeners(code):
    """Pings the room (so you count as present) and returns who is here right now."""
    room = Room.find_by_code(code)
    if room is None:
        abort(404)
    if not can_listen(room):
        abort(403)
    Presence.touch(room.id, viewer_name())
    host = User.find_by_id(room.host_id)
    host_name = host.username if host else None
    names = Presence.online(room.id)
    return jsonify({
        "listeners": [{"name": n, "host": n == host_name} for n in names],
        "count": len(names),
    })


@app.route("/room/<code>/react", methods=["POST"])
def room_react(code):
    """Anyone in the room (host, member or guest) can send one reaction."""
    room = Room.find_by_code(code)
    if room is None:
        abort(404)
    if not can_listen(room):
        abort(403)
    data = request.get_json(silent=True) or {}
    emoji = data.get("emoji")
    if not isinstance(emoji, str) or emoji not in ALLOWED_REACTIONS:
        abort(400)
    now = time.time()
    if now - session.get("last_react", 0) < 0.5:   # simple anti-spam: 2 per second max
        abort(429)
    session["last_react"] = now
    Reaction(None, room.id, viewer_name(), emoji).save()
    return jsonify({"ok": True})


@app.route("/room/<code>/reactions")
def room_reactions(code):
    """Reactions newer than ?since=<id>, for the page to float up on screen."""
    room = Room.find_by_code(code)
    if room is None:
        abort(404)
    if not can_listen(room):
        abort(403)
    since = request.args.get("since", 0, type=int)
    items = Reaction.find_since(room.id, since)
    last_id = items[-1].id if items else since
    return jsonify({
        "reactions": [{"id": r.id, "name": r.display_name, "emoji": r.emoji} for r in items],
        "last_id": last_id,
    })


@app.route("/room/<code>/chat", methods=["POST"])
def room_chat(code):
    """Anyone in the room (host, member or guest) can send a chat message."""
    room = Room.find_by_code(code)
    if room is None:
        abort(404)
    if not can_listen(room):
        abort(403)
    data = request.get_json(silent=True) or {}
    body = data.get("body")
    if not isinstance(body, str):
        abort(400)
    body = body.strip()
    if not body or len(body) > MAX_LENGTH:
        abort(400)
    now = time.time()
    if now - session.get("last_chat", 0) < 1:   # simple anti-spam: 1 message per second
        abort(429)
    session["last_chat"] = now
    Message(None, room.id, viewer_name(), body).save()
    return jsonify({"ok": True})


@app.route("/room/<code>/messages")
def room_messages(code):
    """Chat messages newer than ?since=<id>."""
    room = Room.find_by_code(code)
    if room is None:
        abort(404)
    if not can_listen(room):
        abort(403)
    since = request.args.get("since", 0, type=int)
    items = Message.find_since(room.id, since)
    last_id = items[-1].id if items else since
    return jsonify({"messages": [m.to_dict() for m in items], "last_id": last_id})


if __name__ == "__main__":
    app.run(debug=True)