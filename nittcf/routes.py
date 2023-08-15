import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
from nittcf import app, db, bcrypt
from nittcf.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm, SearchForm, CommentForm
from nittcf.models import User, Post, PostVote, CommentVote, Follower, Comment
from flask_login import login_user, current_user, logout_user, login_required


@app.route("/")
@app.route('/index')
def index():
    return render_template('index.html')

@app.route("/home")
@login_required
def home():
    posts = Post.query.order_by(Post.upvotes.desc()).order_by(Post.downvotes).all()
    user=User.query.filter_by(username=current_user.username).first()
    followers=user.followers
    return render_template('home.html',followers=followers,user=user,posts=posts)


@app.route("/about")
def about():
    return render_template('about.html', title='About')


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account',
                           image_file=image_file, form=form)

@app.route("/account/<int:user_id>", methods=['GET', 'POST'])
@login_required
def user_account(user_id):
    user=User.query.get(user_id)
    posts=Post.query.filter_by(user_id=user_id).all()
    image_file=url_for('static',filename='profile_pics/'+ user.image_file)
    return render_template('user_account.html', title=user.username, user=user, posts=posts, image_file=image_file)


@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('home'))
    return render_template('create_post.html', title='New Post',
                           form=form, legend='New Post')


@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def post(post_id):
    user = User.query.filter_by(username=current_user.username).first()
    post = Post.query.get_or_404(post_id)
    comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.upvotes.desc()).order_by(Comment.downvotes).all()
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(content=form.content.data,user_id=user.id,post_id=post_id)
        db.session.add(comment)
        db.session.commit()
        return redirect(url_for('post',post_id=post.id))
    return render_template('post.html', title=post.title, post=post, comments=comments, form=form)


@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('create_post.html', title='Update Post',
                           form=form, legend='Update Post')


@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    for comment in post.comments:
        db.session.delete(comment)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('home'))

@app.route("/search", methods=['GET', 'POST'])
def search():
    form=SearchForm()
    users=[]
    if form.validate_on_submit():
        users=User.query.filter_by(username=form.user.data).all()
    return render_template('search.html',form=form, users=users)

@app.route("/post/<int:post_id>/upvote", methods=['GET', 'POST'])
@login_required
def post_upvote(post_id):
    user = User.query.filter_by(username=current_user.username).first()
    post = Post.query.get_or_404(post_id)
    vote = PostVote.query.filter_by(user_id=user.id,post_id=post_id).first()
    if not vote:
        user_vote= PostVote(user_id=user.id,post_id=post_id,vote_type="upvote")
        db.session.add(user_vote)
        post.upvotes += 1 
        db.session.commit()
    elif vote.vote_type == "downvote":
        vote.vote_type = "upvote"
        post.upvotes += 1
        post.downvotes -= 1
        db.session.commit()

    return redirect(url_for('home'))
    
@app.route("/post/<int:post_id>/downvote", methods=['GET', 'POST'])
@login_required
def post_downvote(post_id):
    user = User.query.filter_by(username=current_user.username).first()
    post = Post.query.get_or_404(post_id)
    vote = PostVote.query.filter_by(user_id=user.id,post_id=post_id).first()
    if not vote:
        user_vote= PostVote(user_id=user.id,post_id=post_id,vote_type="downvote")
        db.session.add(user_vote)
        post.downvotes += 1 
        db.session.commit() 
    elif vote.vote_type == "upvote":
        vote.vote_type = "downvote"
        post.upvotes -= 1
        post.downvotes += 1
        db.session.commit()

    return redirect(url_for('home'))   

@app.route("/follow_user/<int:user_id>", methods=['GET', 'POST'])
@login_required
def follow_user(user_id):
    current=User.query.filter_by(username=current_user.username).first()
    user=User.query.get(user_id)
    if user == current_user:
        abort(403)
    
    follower=Follower(username=current.username, email=current.email,image_file=current.image_file, follower_user_id=current.id,following=user)
    db.session.add(follower)
    db.session.commit()
    flash(f'You are now following {user.username}','info')
    return redirect(url_for('home'))


@app.route("/comment/<int:comment_id>/upvote", methods=['GET', 'POST'])
@login_required
def comment_upvote(comment_id):
    user = User.query.filter_by(username=current_user.username).first()
    comment = Comment.query.get_or_404(comment_id)
    vote = CommentVote.query.filter_by(user_id=user.id,comment_id=comment_id).first()
    if not vote:
        user_vote= CommentVote(user_id=user.id,comment_id=comment_id,vote_type="upvote")
        db.session.add(user_vote)
        comment.upvotes += 1 
        db.session.commit()
    elif vote.vote_type == "downvote":
        vote.vote_type = "upvote"
        comment.upvotes += 1
        comment.downvotes -= 1
        db.session.commit()

    return redirect(url_for('post',post_id=comment.post.id))

@app.route("/comment/<int:comment_id>/downvote", methods=['GET', 'POST'])
@login_required
def comment_downvote(comment_id):
    user = User.query.filter_by(username=current_user.username).first()
    comment = Comment.query.get_or_404(comment_id)
    vote = CommentVote.query.filter_by(user_id=user.id,comment_id=comment_id).first()
    if not vote:
        user_vote= CommentVote(user_id=user.id,comment_id=comment_id,vote_type="downvote")
        db.session.add(user_vote)
        comment.downvotes += 1 
        db.session.commit() 
    elif vote.vote_type == "upvote":
        vote.vote_type = "downvote"
        comment.upvotes -= 1
        comment.downvotes += 1
        db.session.commit()

    return redirect(url_for('post',post_id=comment.post.id))

@app.route("/comment/<int:comment_id>/update", methods=['GET', 'POST'])
@login_required
def update_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if comment.author != current_user:
        abort(403)
    form = CommentForm()
    if form.validate_on_submit():
        comment.content = form.content.data
        db.session.commit()
        flash('Your comment has been updated!', 'success')
        return redirect(url_for('post', post_id=comment.post_id))
    elif request.method == 'GET':
        form.content.data = comment.content
    return render_template('update_comment.html', title='Update Comment',
                           form=form, legend='Update Comment')


@app.route("/comment/<int:comment_id>/delete", methods=['GET','POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if comment.author != current_user:
        abort(403)
    db.session.delete(comment)
    db.session.commit()
    flash('Your comment has been deleted!', 'success')
    return redirect(url_for('home'))