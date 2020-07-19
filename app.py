import os

from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError
from forms import UserAddForm, LoginForm, MessageForm, EditUserForm
from models import db, connect_db, User, Message

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "postgres:///warbler"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = False
app.config["DEBUG_TB_INTERCEPT_REDIRECTS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "it's a secret")
toolbar = DebugToolbarExtension(app)

connect_db(app)


# ============ PART ONE - STEP SIX ============ #
# - The logged in user is being tracked by saving the username in the browser's session
# - g is a global object. A simple namespace object that uses session or a db to store data for the liftime of the application
# - stores the user info to the application context, in this case g-object
# - @app.before_request runs the function before any requests are made.

##############################################################################
# User signup/login/logout


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]

def do_authorize():
    """Authorize user."""
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """
    do_logout()  #<-- confirm user is logged out

    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", "danger")
            return render_template("users/signup.html", form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template("users/signup.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data, form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", "danger")

    return render_template("users/login.html", form=form)


@app.route("/logout")
def logout():
    """Handle logout of user."""

    # IMPLEMENT THIS
    do_logout()
    flash("You have been succesfully logged out", "danger")
    return redirect("/")


##############################################################################
# General user routes:


@app.route("/users")
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    search = request.args.get("q")

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template("users/index.html", users=users)


@app.route("/users/<int:user_id>")
def users_show(user_id):
    """Show user profile."""

    user = User.query.get_or_404(user_id)

    # snagging messages in order from the database;
    # user.messages won't be in order by default
    messages = (
        Message.query.filter(Message.user_id == user_id)
        .order_by(Message.timestamp.desc())
        .limit(100)
        .all()
    )
    return render_template("users/show.html", user=user, messages=messages)


@app.route("/users/<int:user_id>/following")
def show_following(user_id):
    """Show list of people this user is following."""

    do_authorize()

    user = User.query.get_or_404(user_id)
    return render_template("users/following.html", user=user)


@app.route("/users/<int:user_id>/followers")
def users_followers(user_id):
    """Show list of followers of this user."""

    do_authorize()

    user = User.query.get_or_404(user_id)
    return render_template("users/followers.html", user=user)


@app.route("/users/follow/<int:follow_id>", methods=["POST"])
def add_follow(follow_id):
    """Add a follow for the currently-logged-in user."""

    do_authorize()

    followed_user = User.query.get_or_404(follow_id)
    g.user.following.append(followed_user)
    flash("User followed", "success")
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route("/users/stop-following/<int:follow_id>", methods=["POST"])
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user."""

    do_authorize()

    followed_user = User.query.get(follow_id)
    g.user.following.remove(followed_user)
    flash("User unfollowed", "danger")
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route("/users/profile", methods=["GET", "POST"])
def profile():
    """Update profile for current user."""

    # IMPLEMENT THIS
    do_authorize()

    profile = User.query.get_or_404(g.user.id)
    form = EditUserForm(obj=profile)
    if form.validate_on_submit():
        if User.authenticate(g.user.username, form.password.data):
            profile.username = form.username.data
            profile.email = form.email.data
            profile.image_url = form.image_url.data
            profile.header_image_url = form.header_image_url.data
            profile.bio = form.bio.data
            profile.location = form.location.data

            db.session.commit()
            flash("Profile edited", "success")
            return redirect(f"/users/{g.user.id}")

        flash("You are unauthorized", "danger")
        # return redirect("/")

    return render_template("/users/edit.html", form=form, user_id=g.user.id)


@app.route("/users/delete", methods=["POST"])
def delete_user():
    """Delete user."""

    do_authorize()
    do_logout()

    db.session.delete(g.user)
    db.session.commit()

    return redirect("/signup")


##############################################################################
# Messages routes:


@app.route("/messages/new", methods=["GET", "POST"])
def messages_add():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    do_authorize()

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")

    return render_template("messages/new.html", form=form)


@app.route("/messages/<int:message_id>", methods=["GET"])
def messages_show(message_id):
    """Show a message."""

    msg = Message.query.get(message_id)
    return render_template("messages/show.html", message=msg)


@app.route("/messages/<int:message_id>/delete", methods=["POST"])
def messages_destroy(message_id):
    """Delete a message."""

    do_authorize()

    msg = Message.query.get_or_404(message_id)

    if msg.user_id != g.user.id:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    db.session.delete(msg)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")


# ====================== PART TWO ==================== #


@app.route("/users/<int:user_id>/likes", methods=["GET"])
def show_liked_msgs(user_id):
    """Show likes messages"""
    do_authorize()

    user = User.query.get_or_404(user_id)
    return render_template("/users/likes.html", user=user, likes=user.likes)


@app.route("/messages/<int:msg_id>/like", methods=["POST"])
def like_message(msg_id):
    """Show a likes message."""
    do_authorize()

    like_msg = Message.query.get_or_404(msg_id)
    if like_msg.user_id == g.user.id:
        flash("you cannot like your own messages", "danger")
        return redirect(f"/users/{g.user.id}")

    if like_msg in g.user.likes:
        flash("message unliked!", "danger")
        g.user.likes = [like for like in g.user.likes if like != like_msg]
    else:
        flash("message liked!", "success")
        g.user.likes.append(like_msg)

    db.session.commit()
    return redirect("/")


##############################################################################
# Homepage and error pages


@app.route("/")
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users
    """
    if g.user:
        following_ids = [user.id for user in g.user.following] + [g.user.id]

        messages = (
            Message.query.filter(Message.user_id.in_(following_ids))
            .order_by(Message.timestamp.desc())
            .limit(100)
            .all()
        )
        likes_ids = [msg.id for msg in g.user.likes]
        return render_template("home.html", messages=messages, likes=likes_ids)

    else:
        return render_template("home-anon.html")


@app.errorhandler(404)
def page_not_found(e):
    """404 NOT FOUND page."""

    return render_template('404.html'), 404


##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask


@app.after_request
def add_header(req):
    """Add non-caching headers on every request."""

    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers["Cache-Control"] = "public, max-age=0"
    return req
