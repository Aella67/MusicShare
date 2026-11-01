from flask import Flask, render_template, redirect, url_for, flash
import mysql.connector
from config import Config
from forms import RegisterForm
from models.user import User

app = Flask(__name__)
app.config.from_object(Config)


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
        flash("Account created! Login is coming in the next step.", "success")
        return redirect(url_for("home"))
    return render_template("register.html", form=form)


if __name__ == "__main__":
    app.run(debug=True)