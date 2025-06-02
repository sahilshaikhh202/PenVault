from flask import Blueprint, abort, render_template, flash, redirect, url_for, request, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse
from werkzeug.utils import secure_filename
import os
from app.models import User, Story, Comment, Tag, Follow
from app.forms import LoginForm, RegistrationForm, ProfileForm, StoryForm, CommentForm, SearchForm
from app import db

main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

@main.route('/')
@main.route('/index')
def index():
    # Get all tags for the sidebar
    tags = Tag.query.all()
    
    return render_template('index.html', title='Home', tags=tags)

@main.route('/discover')
def discover():
    page = request.args.get('page', 1, type=int)
    # Get published stories and order by most recent
    stories = Story.query.filter_by(is_published=True).order_by(Story.created_at.desc()).paginate(
        page=page, per_page=6, error_out=False)
    
    # Get all tags for filtering
    tags = Tag.query.all()
    
    # Create a sample story if none exist (for demonstration purposes)
    if Story.query.count() == 0 and current_user.is_authenticated:
        # Create a sample story for demonstration
        sample_story = Story(
            title="Welcome to ScribeHub",
            content="This is a sample story to demonstrate the platform features.",
            summary="A demonstration of ScribeHub's capabilities.",
            is_published=True,
            author_id=current_user.id
        )
        db.session.add(sample_story)
        db.session.commit()
        # Refresh the stories query to include the new story
        stories = Story.query.filter_by(is_published=True).order_by(Story.created_at.desc()).paginate(
            page=page, per_page=6, error_out=False)
    
    return render_template('discover.html', title='Discover Stories', stories=stories, tags=tags)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password', 'error')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.index')
        flash('Welcome back!', 'success')
        return redirect(next_page)
    
    # Log form errors when validation fails
    print("Login form validation errors:", form.errors)
    
    return render_template('auth/login.html', title='Sign In', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', title='Register', form=form)

@main.route('/profile/<username>')
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    stories = Story.query.filter_by(author=user).order_by(Story.created_at.desc()).all()
    return render_template('profile.html', user=user, stories=stories)

@main.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = ProfileForm()
    if form.validate_on_submit():
        if form.profile_picture.data:
            file = form.profile_picture.data
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                current_user.profile_picture = filename
        current_user.username = form.username.data
        current_user.bio = form.bio.data
        db.session.commit()
        flash('Your profile has been updated.')
        return redirect(url_for('main.profile', username=current_user.username))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.bio.data = current_user.bio
    return render_template('edit_profile.html', title='Edit Profile', form=form)

@main.route('/story/new', methods=['GET', 'POST'])
@login_required
def new_story():
    form = StoryForm()
    if form.validate_on_submit():
        publish_mode = request.form.get('publish_mode', 'draft')
        is_published = True if publish_mode == 'publish' else False
        # Create the story
        story = Story(
            title=form.title.data,
            content=form.content.data,
            summary=form.summary.data,
            is_premium=form.is_premium.data,
            author=current_user,
            is_published=is_published
        )
        # Handle cover image upload
        if form.cover_image.data:
            file = form.cover_image.data
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                story.cover_image = filename
        # Save the story
        db.session.add(story)
        db.session.commit()
        if is_published:
            flash('Your story has been published and is now visible in the Discover section!')
        else:
            flash('Your story has been saved as a draft. You can publish it later from your profile.')
        return redirect(url_for('main.story', story_id=story.id))
    return render_template('story/new.html', title='New Story', form=form)

@main.route('/story/<int:story_id>')
def story(story_id):
    story = Story.query.get_or_404(story_id)
    form = CommentForm()
    return render_template('story/view.html', story=story, form=form, Story=Story, Comment=Comment)

@main.route('/story/<int:story_id>/publish', methods=['POST'])
@login_required
def publish_story(story_id):
    story = Story.query.get_or_404(story_id)
    if story.author != current_user:
        abort(403)  # Forbidden
    
    # Publish the story
    story.is_published = True
    db.session.commit()
    
    flash('Your story has been published and is now visible in the Discover section!')
    return redirect(url_for('main.story', story_id=story.id))

@main.route('/story/<int:story_id>/comment', methods=['POST'])
@login_required
def comment(story_id):
    story = Story.query.get_or_404(story_id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(
            content=form.content.data,
            author=current_user,
            story=story
        )
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been added.')
    return redirect(url_for('main.story', story_id=story.id))

@main.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('main.index'))
    if user == current_user:
        flash('You cannot follow yourself!')
        return redirect(url_for('main.profile', username=username))
    current_user.follow(user)
    db.session.commit()
    flash('You are following {}!'.format(username))
    return redirect(url_for('main.profile', username=username))

@main.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('main.index'))
    if user == current_user:
        flash('You cannot unfollow yourself!')
        return redirect(url_for('main.profile', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash('You are not following {}.'.format(username))
    return redirect(url_for('main.profile', username=username))

@main.route('/tag/<tag_name>')
def tag(tag_name):
    tag = Tag.query.filter_by(name=tag_name).first_or_404()
    page = request.args.get('page', 1, type=int)
    stories = tag.stories.filter_by(is_published=True).order_by(Story.created_at.desc()).paginate(
        page=page, per_page=9, error_out=False)
    return render_template('tag.html', tag=tag, stories=stories)

@main.route('/search', methods=['GET', 'POST'])
def search():
    form = SearchForm()
    results = []
    
    if form.validate_on_submit() or request.args.get('query'):
        query = form.query.data if form.validate_on_submit() else request.args.get('query')
        # Search for users with similar usernames
        results = User.query.filter(User.username.ilike(f'%{query}%')).all()
        
    return render_template('search.html', form=form, results=results, query=request.args.get('query', ''))

@main.route('/story/<int:story_id>/like')
@login_required
def like_story(story_id):
    story = Story.query.get_or_404(story_id)
    # Increment the like count
    story.likes += 1
    db.session.commit()
    flash('Story liked!')
    return redirect(url_for('main.story', story_id=story_id))

@main.route('/story/<int:story_id>/save')
@login_required
def save_story(story_id):
    story = Story.query.get_or_404(story_id)
    
    # Check if the story is already in the user's reading list
    if story in current_user.saved_stories:
        flash('This story is already in your reading list.')
    else:
        # Add the story to the user's reading list
        current_user.saved_stories.append(story)
        db.session.commit()
        flash('Story saved to your reading list!')
        
    return redirect(url_for('main.story', story_id=story_id))

@main.route('/story/<int:story_id>/delete', methods=['POST'])
@login_required
def delete_story(story_id):
    story = Story.query.get_or_404(story_id)
    if story.author != current_user:
        abort(403)
    db.session.delete(story)
    db.session.commit()
    flash('Story deleted successfully.', 'success')
    return redirect(url_for('main.profile', username=current_user.username))

@main.route('/story/<int:story_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_story(story_id):
    story = Story.query.get_or_404(story_id)
    if story.author != current_user:
        abort(403)
    form = StoryForm(obj=story)
    if form.validate_on_submit():
        story.title = form.title.data
        story.summary = form.summary.data
        story.content = form.content.data
        story.is_premium = form.is_premium.data
        # Handle cover image upload
        if form.cover_image.data:
            file = form.cover_image.data
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                story.cover_image = filename
        db.session.commit()
        flash('Your story has been updated.', 'success')
        return redirect(url_for('main.story', story_id=story.id))
    # Pre-fill form for GET
    if request.method == 'GET':
        form.title.data = story.title
        form.summary.data = story.summary
        form.content.data = story.content
        form.is_premium.data = story.is_premium
    return render_template('story/edit.html', title='Edit Story', form=form, story=story)

@main.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    story = comment.story
    if current_user != comment.author and current_user != story.author:
        abort(403)
    db.session.delete(comment)
    db.session.commit()
    flash('Comment deleted successfully.', 'success')
    return redirect(url_for('main.story', story_id=story.id))

@main.route('/api/comment/<int:comment_id>/reply', methods=['POST'])
@login_required
def api_reply_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    data = request.get_json()
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'success': False, 'error': 'Content required'}), 400
    reply = Comment(
        content=content,
        author=current_user,
        story=comment.story,
        parent=comment
    )
    db.session.add(reply)
    db.session.commit()
    return jsonify({'success': True, 'reply_id': reply.id})

@main.route('/story/<int:story_id>/unsave', methods=['POST'])
@login_required
def unsave_story(story_id):
    story = Story.query.get_or_404(story_id)
    if story in current_user.saved_stories:
        current_user.saved_stories.remove(story)
        db.session.commit()
        flash('Story removed from your reading list.')
    else:
        flash('Story was not in your reading list.')
    return redirect(request.referrer or url_for('main.profile', username=current_user.username))

@main.route('/settings')
@login_required
def settings():
    return render_template('settings.html', title='Settings')