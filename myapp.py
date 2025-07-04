from flask import Flask, render_template, request, redirect, flash, get_flashed_messages
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import pytz
from datetime import datetime

import os


app = Flask(__name__)

csrf = CSRFProtect(app)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev_secret_key")

#2.ログイン管理システム
login_manager = LoginManager()
login_manager.init_app(app)

db = SQLAlchemy()
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://eiei:@localhost/postgres"
)
db.init_app(app)

migrate = Migrate(app,db)

tokyo_timezone = pytz.timezone("Asia/Tokyo")

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100),nullable=False)
    body = db.Column(db.String(1000),nullable=False)
    created_at = db.Column(db.DateTime,nullable=False,default=lambda: datetime.now(pytz.timezone("Asia/Tokyo")))
    img_name = db.Column(db.String,nullable=True)

class User(UserMixin,db.Model):
    id = db.Column(db.Integer,primary_key=True)
    username = db.Column(db.String(30),nullable=False,unique=True)
    password = db.Column(db.String(200),nullable=False)

#3.現在のユーザーを識別するための関数
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/admin")
@login_required
def admin():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template("admin.html",posts = posts)

@app.route("/create", methods=["GET","POST"])
@login_required
def create():
    #リクエストできた情報の取得
    if request.method == "POST":
        title = request.form.get("title")
        body = request.form.get("body")
        #1.画像情報の取得
        file = request.files.get("img")
        #2.画像ファイル名の取得
        #画像があるか確認
        if file and file.filename != "":
            filename = secure_filename(file.filename)
            #4.画像を保存する
            save_path = os.path.join(app.static_folder, "img", filename)
            file.save(save_path)
        else:
            filename = None
        #3.データベースにファイル名を保存
        post = Post(title=title,body=body,img_name=filename)
        db.session.add(post)
        db.session.commit()
        return redirect("/admin")
    elif request.method == "GET":
        return render_template("create.html",method="GET")

@app.route("/<int:post_id>/update", methods=["GET","POST"])
@login_required
def update(post_id):
    post = Post.query.get(post_id)
    if request.method == "POST":
        post.title = request.form.get("title")
        post.body = request.form.get("body")

        file = request.files.get("img")
        if file and file.filename != "":
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.static_folder, "img", filename)
            file.save(save_path)
            post.img_name = filename
        db.session.commit()
        return redirect("/admin")
    elif request.method == "GET":
        return render_template("update.html",post=post)

@app.route("/<int:post_id>/delete", methods=["POST"])
@login_required
def delete(post_id):
    post = Post.query.get_or_404(post_id)
    if post.img_name:
        img_path = os.path.join(app.static_folder, "img", post.img_name)
        if os.path.exists(img_path):
            os.remove(img_path)
    db.session.delete(post)
    db.session.commit()
    return redirect("/admin")

@app.route("/", methods=["GET"])
def index():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template("index.html",posts=posts)

@app.route("/<int:post_id>/content")
def readmore(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template("readmore.html",post=post)

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        hashed_pass = generate_password_hash(password)
        user = User(username=username, password=hashed_pass)
        db.session.add(user)
        db.session.commit()
        return redirect("/login")
    elif request.method == "GET":
        return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        #ユーザー名とパスワードの受け取り
        username = request.form.get("username")
        password = request.form.get("password")
        #ユーザー名をもとにデータベースから情報を取得
        user = User.query.filter_by(username=username).first()
        #入力パスワードとデータベースのパスが一致しているか確認
        if user and check_password_hash(user.password, password=password):
            #一致していれば、ログインさせて、管理画面にリダイレクト
            login_user(user)
            return redirect("/admin")
        #間違っている場合、エラー分と共にログイン画面へリダイレクト
        else:
            flash("ユーザー名またはパスワードが違います")
            return redirect("/login")
    elif request.method == "GET":
        messages = get_flashed_messages()
        return render_template("login.html",messages=messages)
    
@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect("/")

