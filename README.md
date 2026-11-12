# MusicShare

MusicShare is a web app where a host creates a room, shares a code or link, and everyone listens to the same songs together. Guests need no account. The host controls playback and listeners follow along live, with chat and emoji reactions. Songs come from YouTube or SoundCloud links.

Built with Flask, MySQL and Bootstrap 5 for Laguna University (BSIT: IPT1, OOP and Web Systems).

## Features

- Own logo, branding and responsive purple theme  
- Home page, registration, login and logout  
- Session management (secure sessions, CSRF-protected forms)  
- Dashboard with playlists and rooms  
- Profile management: change name, email, password and profile photo  
- CRUD on core data: playlists, songs and rooms (create, view, rename, delete)  
- Rooms with a random share code and link, guest join, and host-to-listener playback sync  
- Live chat, emoji reactions and a "Listening now" list  
- SMTP email: a welcome email is sent on registration  
- Client-side and server-side form validation, with custom error pages (400, 403, 404, 429, 500\)  
- Object-oriented design: models for User, Playlist, Track (YouTubeTrack and SoundCloudTrack subclasses), Room, Reaction, Message and Presence

## Security

- Passwords are hashed and never stored in plain text  
- CSRF protection on all forms and POST requests (Flask-WTF)  
- Parameterized SQL queries (protection against SQL injection)  
- Output is escaped in templates and written with `textContent` in JavaScript (protection against XSS)  
- Server-side checks that only the host can control a room  
- Unpredictable room codes  
- Secrets are kept in `.env`, which is excluded from Git  
- Uploads limited to JPG/PNG, 2 MB

## Requirements

- Python 3.10 or newer  
- MySQL Server 8.0 or newer (and MySQL Workbench, optional)  
- A Gmail account with an App Password (only needed for the welcome email)  
- All Python packages are listed in `requirements.txt` (Flask, Flask-WTF, Flask-Mail, mysql-connector-python, python-dotenv, email-validator and their dependencies)

## Setup

### 1\. Get the code

```
git clone <repository-url>
cd MusicShare
```

### 2\. Create a virtual environment and install packages

Windows:

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

macOS / Linux:

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3\. Create the database

Make sure MySQL is running. Then use either option.

Option A: MySQL Workbench. Open `database/musicshare.sql` and run it with the lightning bolt button.

Option B: command line:

```
mysql -u root -p < database/musicshare.sql
```

This creates the `musicshare` database and all tables: `users`, `playlists`, `tracks`, `rooms`, `reactions`, `messages` and `room_presence`. The file contains structure only, no data.

### 4\. Configure the environment

Create a file named `.env` in the project folder (next to `app.py`) with these settings:

```
SECRET_KEY=put-a-long-random-string-here
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your-mysql-password
DB_NAME=musicshare

MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-gmail-address@gmail.com
MAIL_PASSWORD=your-gmail-app-password
```

To generate a random `SECRET_KEY`:

```
python -c "import secrets; print(secrets.token_hex(32))"
```

For `MAIL_PASSWORD`, turn on 2-Step Verification on the Gmail account, then create an App Password at [https\://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords). Use that 16-character password, not your normal Gmail password. If the email settings are missing or wrong, the app still works. Registration succeeds and only the welcome email is skipped.

Never commit `.env` to Git.

### 5\. Check the upload folder

Profile photos are saved to `static/uploads/avatars/`. Create this folder if it does not exist.

## Running the app

With the virtual environment active:

```
python app.py
```

Open [http\://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

## Trying out a room

1. Register an account and log in.  
2. On the dashboard, create a playlist and add YouTube or SoundCloud songs by link.  
3. Click **Create room**, choose the playlist, and copy the room code or share link.  
4. Open the link in a private/incognito window as a guest, enter a display name and click **Start listening**.  
5. The host plays, pauses or skips songs. The guest follows automatically and can chat and send reactions.

## Project structure

```
app.py            Routes and app setup
config.py         Settings read from .env
db.py             MySQL connection
forms.py          Flask-WTF forms and validation
models/           User, Playlist, Track, Room, Reaction, Message, Presence
templates/        Jinja2 pages (Bootstrap 5)
static/           CSS, images and uploaded avatars
database/         musicshare.sql (database structure)
requirements.txt  Python packages
```

## Known limitations

- Playback sync uses polling every 2 seconds, so a listener can be a moment behind the host.  
- SoundCloud songs can be saved in playlists but are not yet played inside rooms. Only YouTube songs play.  
- Guest song requests and host approval are not implemented.  
- Account email verification links are not implemented.