from flask import Blueprint, abort, render_template, flash, redirect, url_for, request, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse
from werkzeug.utils import secure_filename
import os
from app.models import User, Story, Comment, Tag, Follow, Novel, Volume, Chapter
from app.forms import LoginForm, RegistrationForm, ProfileForm, StoryForm, CommentForm, SearchForm, PoetryForm, QuoteForm, EssayForm, NovelForm, VolumeForm, ChapterForm, OtherWritingForm
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
    type_filter = request.args.get('type', None)
    query = Story.query.filter_by(is_published=True)
    if type_filter:
        query = query.filter_by(writing_type=type_filter)
    # Always include webnovels in the discovery page
    stories = query.order_by(Story.created_at.desc()).paginate(
        page=page, per_page=6, error_out=False)
    tags = Tag.query.all()
    if Story.query.count() == 0 and current_user.is_authenticated:
        sample_story = Story(
            title="Welcome to ScribeHub",
            content="This is a sample story to demonstrate the platform features.",
            summary="A demonstration of ScribeHub's capabilities.",
            is_published=True,
            author_id=current_user.id
        )
        db.session.add(sample_story)
        db.session.commit()
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

@auth.after_request
def add_no_cache_headers(response):
    # Prevent caching of the login page
    if request.endpoint == 'auth.login':
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

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
    writing_type = request.args.get('type', 'story')
    form_classes = {
        'story': StoryForm,
        'poetry': PoetryForm,
        'quote': QuoteForm,
        'essay': EssayForm,
        'other': OtherWritingForm
    }
    template_map = {
        'story': 'writings/story.html',
        'poetry': 'writings/poetry.html',
        'quote': 'writings/quote.html',
        'essay': 'writings/essay.html',
        'other': 'writings/other.html'
    }
    FormClass = form_classes.get(writing_type, StoryForm)
    template = template_map.get(writing_type, 'writings/story.html')
    form = FormClass()
    if form.validate_on_submit():
        story = Story(
            title=form.title.data if hasattr(form, 'title') else None,
            content=form.content.data,
            summary=form.summary.data if hasattr(form, 'summary') else None,
            author=current_user,
            writing_type=writing_type
        )
        if writing_type == 'poetry':
            # Add poetry-specific fields if you want to store them
            pass
        elif writing_type == 'quote':
            pass
        elif writing_type == 'essay':
            pass
        elif writing_type == 'other':
            pass
        # Handle tags for forms with a tags field
        if hasattr(form, 'tags') and form.tags.data:
            tag_names = [t.strip() for t in form.tags.data.split(',') if t.strip()]
            story.tags = []
            for tag_name in tag_names:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                story.tags.append(tag)
        db.session.add(story)
        db.session.commit()
        flash('Your story has been created!', 'success')
        return redirect(url_for('main.story', story_id=story.id))
    return render_template(template, form=form, title='New ' + writing_type.capitalize())

@main.route('/story/<int:story_id>')
def story(story_id):
    story = Story.query.get_or_404(story_id)
    form = CommentForm()
    return render_template('story/view.html', 
        story=story, 
        form=form, 
        Story=Story, 
        Comment=Comment, 
        Chapter=Chapter,
        Volume=Volume  # Add Volume to the template context
    )

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
        # Handle tags for forms with a tags field
        if hasattr(form, 'tags') and form.tags.data:
            tag_names = [t.strip() for t in form.tags.data.split(',') if t.strip()]
            story.tags = []
            for tag_name in tag_names:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                story.tags.append(tag)
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

# Webnovel creation routes
@main.route('/novel/new', methods=['GET', 'POST'])
@login_required
def new_novel():
    form = NovelForm()
    if form.validate_on_submit():
        story = Story(
            title=form.title.data,
            content='',
            summary=form.summary.data,
            is_premium=False,
            author=current_user,
            is_published=False,
            writing_type='webnovel'
        )
        db.session.add(story)
        db.session.flush()  # Get story.id before commit
        novel = Novel(
            story_id=story.id,
            title=form.title.data,
            summary=form.summary.data,
            cover_image=None
        )
        if form.cover_image.data:
            file = form.cover_image.data
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                novel.cover_image = filename
        db.session.add(novel)
        db.session.commit()
        flash('Novel created! Now add volumes and chapters.')
        return redirect(url_for('main.novel_detail', novel_id=novel.id))
    return render_template('writings/novel.html', form=form)

@main.route('/novel/<int:novel_id>')
def novel_detail(novel_id):
    novel = Novel.query.get_or_404(novel_id)
    volumes = novel.volumes.order_by(Volume.order).all()
    chapters = novel.chapters.order_by(Chapter.order).all()
    return render_template('writings/novel_detail.html', novel=novel, volumes=volumes, chapters=chapters, Chapter=Chapter)

@main.route('/novel/<int:novel_id>/volume/new', methods=['GET', 'POST'])
@login_required
def new_volume(novel_id):
    novel = Novel.query.get_or_404(novel_id)
    form = VolumeForm()
    if form.validate_on_submit():
        volume = Volume(
            novel_id=novel.id,
            title=form.title.data,
            summary=form.summary.data,
            order=int(form.order.data)
        )
        db.session.add(volume)
        db.session.commit()
        flash('Volume added!')
        return redirect(url_for('main.novel_detail', novel_id=novel.id))
    return render_template('writings/volume.html', form=form, novel=novel)

@main.route('/novel/<int:novel_id>/volume/<int:volume_id>/chapter/new', methods=['GET', 'POST'])
@login_required
def new_chapter(novel_id, volume_id):
    novel = Novel.query.get_or_404(novel_id)
    volume = Volume.query.get_or_404(volume_id)
    form = ChapterForm()
    if form.validate_on_submit():
        chapter = Chapter(
            novel_id=novel.id,
            volume_id=volume.id,
            title=form.title.data,
            content=form.content.data,
            order=int(form.order.data)
        )
        db.session.add(chapter)
        db.session.commit()
        flash('Chapter added!')
        return redirect(url_for('main.novel_detail', novel_id=novel.id))
    return render_template('writings/chapter.html', form=form, novel=novel, volume=volume)

@main.route('/novel/<int:novel_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_novel(novel_id):
    novel = Novel.query.get_or_404(novel_id)
    story = novel.story
    if story.author != current_user:
        abort(403)
    form = NovelForm(obj=novel)
    if form.validate_on_submit():
        novel.title = form.title.data
        novel.summary = form.summary.data
        novel.genre = form.genre.data
        novel.status = form.status.data
        novel.is_mature = form.is_mature.data
        if form.cover_image.data:
            file = form.cover_image.data
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                novel.cover_image = filename
                story.cover_image = filename
        # Sync Story fields with Novel
        story.title = form.title.data
        story.summary = form.summary.data
        # Handle tags for forms with a tags field
        if hasattr(form, 'tags') and form.tags.data:
            tag_names = [t.strip() for t in form.tags.data.split(',') if t.strip()]
            story.tags = []
            for tag_name in tag_names:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                story.tags.append(tag)
        db.session.commit()
        flash('Novel updated!', 'success')
        return redirect(url_for('main.novel_detail', novel_id=novel.id))
    return render_template('writings/novel.html', form=form, novel=novel)

@main.route('/novel/<int:novel_id>/delete', methods=['POST'])
@login_required
def delete_novel(novel_id):
    novel = Novel.query.get_or_404(novel_id)
    story = novel.story
    if story.author != current_user:
        abort(403)
    db.session.delete(novel)
    db.session.delete(story)
    db.session.commit()
    flash('Novel and all its volumes and chapters deleted.', 'success')
    return redirect(url_for('main.profile', username=current_user.username))

@main.route('/volume/<int:volume_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_volume(volume_id):
    volume = Volume.query.get_or_404(volume_id)
    novel = volume.novel
    story = novel.story
    if story.author != current_user:
        abort(403)
    form = VolumeForm(obj=volume)
    if form.validate_on_submit():
        volume.title = form.title.data
        volume.summary = form.summary.data
        volume.order = int(form.order.data)
        db.session.commit()
        flash('Volume updated!', 'success')
        return redirect(url_for('main.novel_detail', novel_id=novel.id))
    return render_template('writings/volume.html', form=form, novel=novel, volume=volume)

@main.route('/volume/<int:volume_id>/delete', methods=['POST'])
@login_required
def delete_volume(volume_id):
    volume = Volume.query.get_or_404(volume_id)
    novel = volume.novel
    story = novel.story
    if story.author != current_user:
        abort(403)
    db.session.delete(volume)
    db.session.commit()
    flash('Volume and all its chapters deleted.', 'success')
    return redirect(url_for('main.novel_detail', novel_id=novel.id))

@main.route('/chapter/<int:chapter_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_chapter(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    novel = chapter.novel
    story = novel.story
    if story.author != current_user:
        abort(403)
    form = ChapterForm(obj=chapter)
    if form.validate_on_submit():
        chapter.title = form.title.data
        chapter.content = form.content.data
        chapter.order = int(form.order.data)
        chapter.author_notes = form.author_notes.data
        chapter.is_draft = form.is_draft.data
        db.session.commit()
        flash('Chapter updated!', 'success')
        return redirect(url_for('main.novel_detail', novel_id=novel.id))
    return render_template('writings/chapter.html', form=form, novel=novel, volume=chapter.volume, chapter=chapter)

@main.route('/chapter/<int:chapter_id>/delete', methods=['POST'])
@login_required
def delete_chapter(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    novel = chapter.novel
    story = novel.story
    if story.author != current_user:
        abort(403)
    db.session.delete(chapter)
    db.session.commit()
    flash('Chapter deleted.', 'success')
    return redirect(url_for('main.novel_detail', novel_id=novel.id))

@main.route('/chapter/<int:chapter_id>')
def view_chapter(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    novel = chapter.novel
    volume = chapter.volume
    return render_template('writings/chapter_view.html', chapter=chapter, novel=novel, volume=volume)

# Add new pretty URL routes for novels, volumes, and chapters using slugs
@main.route('/novel/<novel_slug>')
def novel_detail_slug(novel_slug):
    novel = Novel.query.filter_by(slug=novel_slug).first_or_404()
    volumes = novel.volumes.order_by(Volume.order).all()
    chapters = novel.chapters.order_by(Chapter.order).all()
    return render_template('writings/novel_detail.html', novel=novel, volumes=volumes, chapters=chapters, Chapter=Chapter)

@main.route('/novel/<novel_slug>/<volume_slug>')
def volume_detail_slug(novel_slug, volume_slug):
    novel = Novel.query.filter_by(slug=novel_slug).first_or_404()
    volume = Volume.query.filter_by(novel_id=novel.id, slug=volume_slug).first_or_404()
    chapters = volume.chapters.order_by(Chapter.order).all()
    return render_template('writings/volume_detail.html', novel=novel, volume=volume, chapters=chapters)

@main.route('/novel/<novel_slug>/<volume_slug>/<chapter_slug>')
def chapter_view_slug(novel_slug, volume_slug, chapter_slug):
    novel = Novel.query.filter_by(slug=novel_slug).first_or_404()
    volume = Volume.query.filter_by(novel_id=novel.id, slug=volume_slug).first_or_404()
    chapter = Chapter.query.filter_by(volume_id=volume.id, slug=chapter_slug).first_or_404()
    return render_template('writings/chapter_view.html', chapter=chapter, novel=novel, volume=volume)