from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, EmailField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Regexp, ValidationError
from models.user import User
from models.track import Track
from models.room import Room


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


class ProfileForm(FlaskForm):
    """Update name and email. original_user is the logged-in user, so their
    own current username/email do not count as 'already taken'."""
    username = StringField("Username", validators=[
        DataRequired(), Length(min=3, max=50),
        Regexp(r"^[A-Za-z0-9_]+$", message="Use letters, numbers, and underscores only."),
    ])
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=120)])

    def __init__(self, original_user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_user = original_user

    def validate_username(self, field):
        other = User.find_by_username(field.data.strip())
        if other and other.id != self.original_user.id:
            raise ValidationError("That username is already taken.")

    def validate_email(self, field):
        other = User.find_by_email(field.data.strip().lower())
        if other and other.id != self.original_user.id:
            raise ValidationError("An account with that email already exists.")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[DataRequired()])
    new_password = PasswordField("New password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField("Confirm new password", validators=[
        DataRequired(), EqualTo("new_password", message="Passwords must match."),
    ])

    def __init__(self, original_user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_user = original_user

    def validate_current_password(self, field):
        if not self.original_user.check_password(field.data):
            raise ValidationError("Current password is incorrect.")


class PhotoForm(FlaskForm):
    """Profile photo upload. The extension is checked here; the real file
    contents are checked again in app.py."""
    photo = FileField("Profile photo", validators=[
        FileRequired(message="Choose an image first."),
        FileAllowed(["jpg", "jpeg", "png"], "Only JPG or PNG images are allowed."),
    ])


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


class JoinForm(FlaskForm):
    code = StringField("Room code", validators=[DataRequired(), Length(max=8)])

    def validate_code(self, field):
        room = Room.find_by_code(field.data)
        if room is None:
            raise ValidationError("No room with that code.")
        if not room.is_open:
            raise ValidationError("That room is closed.")


class GuestForm(FlaskForm):
    display_name = StringField("Display name", validators=[DataRequired(), Length(min=2, max=30)])