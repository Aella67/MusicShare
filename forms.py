from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, EmailField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Regexp, ValidationError
from models.user import User
from models.track import Track


class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[
        DataRequired(), Length(min=3, max=50),
        Regexp(r"^[A-Za-z0-9_]+$", message="Use letters, numbers, and underscores only."),
    ])
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField("Confirm password", validators=[
        DataRequired(), EqualTo("password", message="Passwords must match."),
    ])

    def validate_username(self, field):
        if User.find_by_username(field.data.strip()):
            raise ValidationError("That username is already taken.")

    def validate_email(self, field):
        if User.find_by_email(field.data.strip().lower()):
            raise ValidationError("An account with that email already exists.")


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])


class PlaylistForm(FlaskForm):
    name = StringField("Playlist name", validators=[DataRequired(), Length(max=100)])


class TrackForm(FlaskForm):
    url = StringField("Song link", validators=[DataRequired(), Length(max=500)])
    title = StringField("Title", validators=[DataRequired(), Length(max=200)])

    def validate_url(self, field):
        if Track.from_url(0, field.data, "") is None:
            raise ValidationError("Paste a valid YouTube video or SoundCloud link.")


class RoomForm(FlaskForm):
    name = StringField("Room name", validators=[DataRequired(), Length(max=100)])
    playlist_id = SelectField("Playlist", coerce=int)