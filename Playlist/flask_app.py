from flask import Flask, render_template, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from socket import gethostname
from flask_login import (LoginManager, UserMixin,
    login_user, logout_user, login_required, current_user)
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
    )


#Setup - initialize flask, sqlalchemy, and logins
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project.db"
app.config["SECRET_KEY"] = "ENTER YOUR SECRET KEY"
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "playlists"
login_manager.login_message = "You are not logged in"


########
# Models
########
class Playlist(db.Model):
    __tablename__ = "playlists"

    #playlists
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(4096))
    user_id = db.Column(db.Integer,db.ForeignKey("users.id"))

    author = db.relationship("Users", back_populates="playlists")


class Song(db.Model):
    __tablename__ = "songs"

    #songs
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(4096))
    user_id = db.Column(db.Integer,db.ForeignKey("users.id"))
    youtube_link = db.Column(db.String(4096))


    playlist_id = db.Column(db.Integer, db.ForeignKey("playlists.id"))
    author_song = db.relationship("Users", back_populates="songs")


'''
A note from Mr Jones: this class should have been called
"User" instead of "Users". Python convention is that class names
should be singular nouns. I shared an earlier version of this
code that used "Users", so I'm keeping it to avoid confusion
'''
class Users(UserMixin, db.Model):
    __tablename__ = "users"

    #columns
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True,
                         nullable=False)
    password = db.Column(db.String(250),
                         nullable=False)

    #relationship - notes:
        #There is no column for this relationship. This is still necessary
        #   in the Python side of the ORM class to connect the two models
    playlists = db.relationship("Playlist", back_populates="author")

    songs = db.relationship("Song", back_populates="author_song")

@login_manager.user_loader
def loader_user(user_id):
    return Users.query.get(user_id)


@app.route('/')
def hello_world():
    return redirect("/playlists")

########
# USER CRUD Controllers
########
@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == 'GET':
        return render_template("add_user.html")
    if request.method == "POST":
        password=request.form.get("password")

        #note the password hashing here!
        user = Users(username=request.form.get("username"),
                     password=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'GET':
        return render_template("login_user.html")
    # If a post request was made, find the user by
    # filtering for the username
    if request.method == "POST":
        user = Users.query.filter_by(
            username=request.form.get("username")).first()
        # Check if the password entered is the
        # same as the user's hashed password
        password = request.form.get("password")
        if user and check_password_hash(user.password, password):
            # Use the login_user method to log in the user
            login_user(user)
            flash('You were successfully logged in')
            return redirect("/playlists")
        else:
            flash('Your username or password were incorrect')
            return redirect("/login")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash('You were successfully logged out')
    return redirect("/playlists")

########
# CRUD Controllers
########
@app.route('/add_playlist', methods=['POST', 'GET'])
@login_required
def add_playlist():
    if request.method == 'GET':
        return render_template('add_playlist.html')
    if request.method == 'POST':
        textFromForm = request.form['text']
        #create the Playlist object, and connect it to the user who
        #is currently logged in. Note that Flask gives us a helpful
        #current_user object
        newPlaylist = Playlist(text=textFromForm,author = current_user)
        db.session.add(newPlaylist)
        db.session.commit()
        return redirect("/playlists")

@app.route('/playlists')
def playlists():
    playlists = Playlist.query.all()
    return render_template('playlists.html', playlists=playlists)

@app.route('/edit_playlist/<id>', methods=['POST', 'GET'])
@login_required
def edit_playlist(id):
    if request.method == 'GET':
        toEdit = Playlist.query.get(id)
        #we can check to see if the author of the existing post
        #is the same as the current_user
        if(toEdit.author != current_user):
            flash("You are not the author of this playlist, so you can't edit it!")
            return redirect("/playlists")
        return render_template('edit_playlist.html',playlist=toEdit)
    if request.method == 'POST':
        toEdit = Playlist.query.get(id)
        toEdit.text = request.form['text']
        db.session.commit()
        return redirect("/playlists")

@app.route('/delete_playlist/<id>')
@login_required
def delete_playlist(id):
    toDelete = Playlist.query.get(id)
    if(toDelete.author != current_user):
            flash("You are not the author of this playlist, so you can't delete it!")
            return redirect("/playlists")
    db.session.delete(toDelete)
    db.session.commit()
    return redirect("/playlists")





@app.route('/open_playlist/<id>')
def open_playlist(id):
    songs = Song.query.filter_by(playlist_id=id).all()
    return render_template('open_playlist.html', songs=songs, playlist_id = id)


@app.route('/delete_song/<id>')
@login_required
def delete_song(id):
    toDelete = Song.query.get(id)

    # Get the playlist associated with the song
    playlist = Playlist.query.get(toDelete.playlist_id)

    if playlist.author != current_user:
        flash("You are not the author of this playlist, so you can't delete its songs!")
        return redirect("/playlists")
    db.session.delete(toDelete)
    db.session.commit()
    return redirect(f"/open_playlist/{toDelete.playlist_id}")


@app.route('/add_song/<id>', methods=['POST', 'GET'])
@login_required
def add_song(id):
    if request.method == 'GET':
        return render_template('add_song.html', playlist_id = id)
    if request.method == 'POST':
        textFromForm = request.form['text']
        urlFromForm = request.form['youtube_link']


        ### prohibiting adding to other people's playlists ###
        playlist = Playlist.query.get(id)

        if playlist.author != current_user:
            flash("You are not the author of this playlist, so you can't add songs to it!")
            return redirect("/playlists")
        ###

        newSong = Song(youtube_link = urlFromForm, text=textFromForm, author_song=current_user, playlist_id=id)
        db.session.add(newSong)
        db.session.commit()
        return redirect(f"/open_playlist/{id}") #thank you stack overflow




########
# Code to create/delete tables
########
if __name__ == '__main__':
    with app.app_context():
        db.drop_all()
        db.create_all()
        me = Users(username='admin',password=generate_password_hash("admin"))
        myPlaylist = Playlist(text='''This is a sample playlist''',author=me)

        #note - we do not need to add myPlaylist.
        #we've already connected myPlaylist to me, so when I add me
        #it includes the connected playlist
        db.session.add(me)

        db.session.commit()
    if 'liveconsole' not in gethostname():
        app.run()



