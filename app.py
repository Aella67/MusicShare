from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, session, abort
from flask_wtf import CSRFProtect
import mysql.connector
from config import Config
from forms import RegisterForm, LoginForm, PlaylistForm, TrackForm
from models.user import User
from models.playlist import Playlist
from models.track import Track

app = Flask(__name__)
app.config.from_object(Config)
csrf = CSRFProtect(app)


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


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(None, form.username.data.strip(),
                    form.email.data.strip().lower(), None, False)
        user.set_password(form.password.data)
        try:
            user.save()
        except mysql.connector.IntegrityError:
            flash("That username or email is already registered.", "danger")
            return render_template("register.html", form=form)
        flash("Account created! You can log in now.", "success")
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
    return render_template("dashboard.html", form=form, playlists=playlists)

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


if __name__ == "__main__":
    app.run(debug=True)