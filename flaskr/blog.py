from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from werkzeug.exceptions import abort

from flaskr.auth import login_required
from flaskr.db import get_db

import os
from werkzeug.utils import secure_filename

bp = Blueprint("blog", __name__, static_folder = 'static')
APP_ROOT = os.path.dirname(os.path.abspath(__file__))

@bp.route("/")
def index():
    """Show all the posts, most recent first."""
    db = get_db()
    posts = db.execute(
        "SELECT p.id, title, comment, photoname, created, author_id, username"
        " FROM post p JOIN user u ON p.author_id = u.id"
        " ORDER BY created ASC"
    ).fetchall()
    return render_template("blog/index.html", posts=posts)


def get_post(id, check_author=True):
    """Get a post and its author by id.
    Checks that the id exists and optionally that the current user is
    the author.
    :param id: id of post to get
    :param check_author: require the current user to be the author
    :return: the post with author information
    :raise 404: if a post with the given id doesn't exist
    :raise 403: if the current user isn't the author
    """
    post = (
        get_db()
        .execute(
            "SELECT p.id, title, comment, photoname, created, author_id, username"
            " FROM post p JOIN user u ON p.author_id = u.id"
            " WHERE p.id = ?",
            (id,),
        )
        .fetchone()
    )

    if post is None:
        abort(404, "Post id {0} doesn't exist.".format(id))

    if check_author and post["author_id"] != g.user["id"]:
        abort(403)

    return post

def upload():
    target = os.path.join(APP_ROOT, 'static/images/')

    if not os.path.isdir(target):
        os.mkdir(target)

    if request.method == 'POST' and 'photo' in request.files:
        photo = request.files['photo']
        if photo.filename != '':
            destination = "/".join([target, photo.filename])
            photo.save(destination)
            #photo.save(os.path.join('static/images', photo.filename))
    return render_template("blog/create.html")

@bp.route("/create", methods=("GET", "POST"))
@login_required
def create():
    """Create a new post for the current user."""
    if request.method == "POST":
        title = request.form["title"]
        comment = request.form["comment"]
        photo = request.files["photo"]
        photoname = photo.filename
        error = None

        if not title:
            error = "Title is required."

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "INSERT INTO post (title, comment, photoname, author_id) VALUES (?, ?, ?, ?)",
                (title, comment, photoname, g.user["id"]),
            )
            db.commit()
            upload()
            return redirect(url_for("blog.index"))

    return render_template("blog/create.html")

@bp.route("/<int:id>/update", methods=("GET", "POST"))
@login_required
def update(id):
    """Update a post if the current user is the author."""
    post = get_post(id)

    if request.method == "POST":
        title = request.form["title"]
        comment = request.form["comment"]
        photo = request.files["photo"]
        photoname = photo.filename
        error = None

        if not title:
            error = "Title is required."

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "UPDATE post SET title = ?, comment = ?, photoname = ? WHERE id = ?", (title, comment, photoname, id)
            )
            db.commit()
            upload()
            return redirect(url_for("blog.index"))

    return render_template("blog/update.html", post=post)


@bp.route("/<int:id>/delete", methods=("POST",))
@login_required
def delete(id):
    """Delete a post.
    Ensures that the post exists and that the logged in user is the
    author of the post.
    """
    get_post(id)
    db = get_db()
    db.execute("DELETE FROM post WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for("blog.index"))