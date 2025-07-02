from flask import Blueprint, abort, render_template, flash, redirect, url_for, request, current_app, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
import os
from app.models import User, Story, Comment, Tag, Follow, Novel, Volume, Chapter, ReadingHistory, PointsTransaction, UnlockedContent, ChapterReadingHistory
from app.forms import LoginForm, RegistrationForm, ProfileForm, StoryForm, CommentForm, SearchForm, PoetryForm, QuoteForm, EssayForm, NovelForm, VolumeForm, ChapterForm, OtherWritingForm, EditCommentForm
from app import db
from datetime import datetime, timedelta
import math
from slugify import slugify  # or your own slugify function

main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

def generate_unique_slug(base_slug, model):
    slug = base_slug
    counter = 2
    while model.query.filter_by(slug=slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug

@main.route('/')
@main.route('/index')
def index():
    tags = Tag.query.all()
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    featured_stories = Story.query.filter(
        Story.is_featured == True, 
        Story.is_published == True,
        Story.featured_at >= twenty_four_hours_ago
    ).order_by(Story.featured_at.desc()).limit(5).all()

    if current_user.is_authenticated:
        # Referral card flag
        referral_card = True

        # --- Continue Reading Section ---
        continue_novel = None
        continue_chapter = None
        # Find the most recent novel in chapter reading history where not all chapters are read
        from app.models import ChapterReadingHistory, Novel, Chapter
        # Get all chapter reading history for user, most recent first
        recent_chapter_histories = ChapterReadingHistory.query.filter_by(user_id=current_user.id).order_by(ChapterReadingHistory.timestamp.desc()).all()
        seen_novel_ids = set()
        for ch in recent_chapter_histories:
            if ch.novel_id in seen_novel_ids:
                continue
            seen_novel_ids.add(ch.novel_id)
            novel = Novel.query.get(ch.novel_id)
            if not novel:
                continue
            total_chapters = Chapter.query.filter_by(novel_id=novel.id).count()
            # Find the highest order chapter the user has read
            last_read_chapter = Chapter.query.get(ch.chapter_id)
            if not last_read_chapter:
                continue
            last_order = last_read_chapter.order
            # Check if there are more chapters after this
            next_chapter = Chapter.query.filter_by(novel_id=novel.id).filter(Chapter.order > last_order).order_by(Chapter.order.asc()).first()
            if next_chapter:
                continue_novel = novel
                continue_chapter = next_chapter
                break
        # --- Weekly Stats Preview ---
        week_ago = datetime.utcnow() - timedelta(days=7)
        stories_published = Story.query.filter(
            Story.author_id == current_user.id,
            Story.created_at >= week_ago,
            Story.is_published == True
        ).count()
        likes_received = db.session.query(db.func.sum(Story.likes)).filter(
            Story.author_id == current_user.id,
            Story.created_at >= week_ago
        ).scalar() or 0
        weekly_stats = {
            'stories_published': stories_published,
            'likes_received': likes_received
        }
        return render_template('index.html', title='Home', tags=tags, featured_stories=featured_stories, timedelta=timedelta,
            referral_card=referral_card, continue_novel=continue_novel, continue_chapter=continue_chapter, weekly_stats=weekly_stats)
    else:
        return render_template('index.html', title='Home', tags=tags, featured_stories=featured_stories, timedelta=timedelta)

@main.route('/discover')
def discover():
    page = request.args.get('page', 1, type=int)
    type_filter = request.args.get('type', None)
    ajax = request.args.get('ajax', None)
    query = Story.query.filter_by(is_published=True)
    query = query.join(User).filter(
        (User.is_disabled.is_(None) | (User.is_disabled == False)) &
        (User.deletion_requested_at.is_(None))
    )
    if type_filter:
        query = query.filter(Story.writing_type == type_filter)
    stories = query.order_by(Story.created_at.desc()).paginate(
        page=page, per_page=9, error_out=False)
    tags = Tag.query.all()
    if ajax:
        # Return JSON for infinite scroll
        def story_to_dict(story):
            return {
                'id': story.id,
                'title': story.title,
                'summary': story.summary or '',
                'writing_type': story.writing_type,
                'is_premium': story.is_premium,
                'likes': story.likes,
                'views': story.views,
                'comments_count': story.comments.count(),
                'author': {
                    'username': story.author.username,
                    'profile_picture': story.author.profile_picture or 'default.jpg',
                },
                'tags': [{'name': tag.name} for tag in story.tags],
                'url': url_for('main.novel_detail_slug', novel_slug=story.novel.slug) if story.writing_type == 'webnovel' and story.novel else url_for('main.story_by_slug', story_slug=story.slug)
            }
        return jsonify({
            'stories': [story_to_dict(story) for story in stories.items],
            'page': stories.page,
            'has_next': stories.has_next
        })
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
            page=page, per_page=9, error_out=False)
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
        
        # Check account status
        if user.is_disabled:
            # Re-enable account on successful login
            user.enable_account()
            flash('Your account has been re-enabled!', 'success')
        elif user.is_scheduled_for_deletion():
            # Allow login but show deletion warning
            login_user(user, remember=form.remember_me.data)
            days_left = user.days_until_deletion()
            flash(f'Your account is scheduled for deletion in {days_left} days. You can cancel this in your settings.', 'warning')
            next_page = request.args.get('next')
            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('main.index')
            return redirect(next_page)
        elif not user.is_account_active():
            # Account has been permanently deleted (past 20 days)
            flash('This account has been permanently deleted and cannot be accessed.', 'error')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        
        try:
            # Award daily login points
            if user.can_earn_daily_login_points():
                user.add_points(5, 'daily_login')
                user.last_daily_login = datetime.utcnow().date()
                db.session.commit()
                flash('You earned 5 points for logging in today!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error awarding points. Please try again.', 'error')
        
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.index')
        
        # Check if user should see the tour
        if not user.tour_completed:
            flash('Welcome to PenVault! Let\'s take a quick tour to help you get started.', 'success')
        else:
            flash('Welcome back!', 'success')
            
        return redirect(next_page)
    
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
        
        # Handle referral code
        referral_bonus_awarded = False
        if form.referral_code.data:
            referrer = User.query.filter_by(referral_code=form.referral_code.data).first()
            if referrer and referrer.can_earn_referral_points():
                user.referred_by = referrer.id
                # Process referral and award points to referrer
                referrer.process_referral(user)
                referral_bonus_awarded = True
                flash(f'Welcome! You were referred by {referrer.username}. You both earned 25 points!', 'success')
            else:
                flash('Invalid or expired referral code. Registration completed without referral bonus.', 'warning')
        else:
            flash('Congratulations, you are now a registered user!', 'success')
        
        db.session.add(user)
        db.session.commit()  # Commit user first to get user.id
        
        # Award welcome bonus points to the new user after commit
        if referral_bonus_awarded:
            user.add_points(25, 'referral_welcome', f'Welcome bonus for using referral code')
        
        next_page = request.args.get('next')
        return redirect(url_for('auth.login', next=next_page))
    
    return render_template('auth/register.html', title='Register', form=form)

@main.route('/profile/<username>')
def profile(username):  # Remove @login_required decorator
    user = User.query.filter_by(username=username).first_or_404()
    
    # Check if user account is active
    if not user.is_account_active():
        if user.is_disabled:
            flash('This account has been disabled by the user.', 'info')
        elif user.is_scheduled_for_deletion():
            days_left = user.days_until_deletion()
            flash(f'This account is scheduled for deletion in {days_left} days.', 'warning')
        else:
            flash('This account has been permanently deleted.', 'error')
        return redirect(url_for('main.index'))
    
    # Only show published stories from active accounts
    stories = Story.query.filter_by(author=user, is_published=True).order_by(Story.created_at.desc()).all()
    
    # Get combined reading history (stories + chapters)
    combined_history = []
    
    # Get story reading history
    story_history = user.reading_history.order_by(ReadingHistory.timestamp.desc()).limit(20).all()
    for entry in story_history:
        combined_history.append({
            'type': 'story',
            'title': entry.story.title,
            'timestamp': entry.timestamp,
            'story': entry.story,
            'novel': None,
            'chapter': None,
            'history_id': entry.id
        })
    
    # Get chapter reading history
    chapter_history = user.chapter_reading_history.order_by(ChapterReadingHistory.timestamp.desc()).limit(20).all()
    for entry in chapter_history:
        combined_history.append({
            'type': 'chapter',
            'title': f"{entry.chapter.title} ({entry.novel.title})",
            'timestamp': entry.timestamp,
            'story': entry.novel.story,
            'novel': entry.novel,
            'chapter': entry.chapter,
            'history_id': entry.id
        })
    
    # Sort combined history by timestamp (most recent first) and take top 20
    combined_history.sort(key=lambda x: x['timestamp'], reverse=True)
    combined_history = combined_history[:20]
    
    return render_template('profile.html', user=user, stories=stories, ReadingHistory=ReadingHistory, combined_history=combined_history)

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
        if writing_type == 'quote':
            title = form.title.data if form.title.data else form.content.data[:50] + '...' if len(form.content.data) > 50 else form.content.data
        else:
            title = form.title.data if hasattr(form, 'title') else None
        base_slug = slugify(title) if title else "quote"
        slug = generate_unique_slug(base_slug, Story)  # Story is your model
        story = Story(
            title=title,
            content=form.content.data,
            summary=form.summary.data if hasattr(form, 'summary') else None,
            author=current_user,
            writing_type=writing_type,
            form_type=form.form_type.data if hasattr(form, 'form_type') else None,
            notes=form.notes.data if hasattr(form, 'notes') else None,
            quote_author=form.author.data if hasattr(form, 'author') else None,
            quote_source=form.source.data if hasattr(form, 'source') else None,
            quote_category=form.category.data if hasattr(form, 'category') else None,
            subtitle=form.subtitle.data if hasattr(form, 'subtitle') else None,
            essay_category=form.category.data if hasattr(form, 'category') else None,
            references=form.references.data if hasattr(form, 'references') else None,
            custom_type=form.custom_type.data if hasattr(form, 'custom_type') else None,
            is_published=not form.save_draft.data,  # Set is_published based on which button was clicked
            slug=slug
        )
        # Always handle tags for all types
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
        
        try:
            # Award points for new post
            if current_user.can_earn_post_points():
                current_user.add_points(25, 'new_post', f'Posted {writing_type}')
                current_user.last_post_points = datetime.utcnow().date()
                db.session.commit()
                flash('You earned 25 points for posting!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error awarding points. Please try again.', 'error')
        
        if form.save_draft.data:
            flash('Your draft has been saved!', 'success')
            return redirect(url_for('main.drafts'))
        else:
            flash('Your story has been published!', 'success')
            return redirect(url_for('main.story_by_slug', story_slug=story.slug))
    return render_template(template, form=form, title='New ' + writing_type.capitalize())

@main.route('/story/<int:story_id>')
def story(story_id):
    story = Story.query.get_or_404(story_id)
    form = CommentForm()
    
    login_form = LoginForm() if not current_user.is_authenticated else None
    
    unlocked = False
    if current_user.is_authenticated and story.is_premium and current_user != story.author:
        unlocked = UnlockedContent.query.filter_by(user_id=current_user.id, story_id=story_id).first() is not None

    # For quotes, increment view immediately (normal behavior)
    if story.writing_type == 'quote':
        if (not current_user.is_authenticated) or (current_user.is_authenticated and current_user.id != story.author_id):
            story.views = (story.views or 0) + 1
            db.session.commit()
            # Add to reading history (FIFO, max 20) only if logged in
            if current_user.is_authenticated:
                existing = ReadingHistory.query.filter_by(user_id=current_user.id, story_id=story.id).first()
                if existing:
                    existing.timestamp = datetime.utcnow()
                else:
                    db.session.add(ReadingHistory(user_id=current_user.id, story_id=story.id))
                db.session.commit()
                # Keep only 20 most recent
                history = ReadingHistory.query.filter_by(user_id=current_user.id).order_by(ReadingHistory.timestamp.desc()).all()
                if len(history) > 20:
                    for h in history[20:]:
                        db.session.delete(h)
                    db.session.commit()
    # For other types, handled by JS/API
    return render_template('story/view.html', 
        story=story, 
        form=form, 
        login_form=login_form,
        Story=Story, 
        Comment=Comment, 
        Chapter=Chapter,
        Volume=Volume,
        unlocked=unlocked)

@main.route('/story/<story_slug>')
def story_by_slug(story_slug):
    story = Story.query.filter_by(slug=story_slug).first_or_404()
    form = CommentForm()
    
    login_form = LoginForm() if not current_user.is_authenticated else None
    
    unlocked = False
    if current_user.is_authenticated and story.is_premium and current_user != story.author:
        unlocked = UnlockedContent.query.filter_by(user_id=current_user.id, story_id=story.id).first() is not None

    # For quotes, increment view immediately (normal behavior)
    if story.writing_type == 'quote':
        if (not current_user.is_authenticated) or (current_user.is_authenticated and current_user.id != story.author_id):
            story.views = (story.views or 0) + 1
            db.session.commit()
            # Add to reading history (FIFO, max 20) only if logged in
            if current_user.is_authenticated:
                existing = ReadingHistory.query.filter_by(user_id=current_user.id, story_id=story.id).first()
                if existing:
                    existing.timestamp = datetime.utcnow()
                else:
                    db.session.add(ReadingHistory(user_id=current_user.id, story_id=story.id))
                db.session.commit()
                # Keep only 20 most recent
                history = ReadingHistory.query.filter_by(user_id=current_user.id).order_by(ReadingHistory.timestamp.desc()).all()
                if len(history) > 20:
                    for h in history[20:]:
                        db.session.delete(h)
                    db.session.commit()
    # For other types, handled by JS/API
    return render_template('story/view.html', 
        story=story, 
        form=form, 
        login_form=login_form,
        Story=Story, 
        Comment=Comment, 
        Chapter=Chapter,
        Volume=Volume,
        unlocked=unlocked)

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
    return redirect(url_for('main.story_by_slug', story_slug=story.slug))

@main.route('/story/<int:story_id>/comment', methods=['POST'])
def comment(story_id):
    if not current_user.is_authenticated:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Please log in to comment.'}), 401
        flash('Please log in to comment.', 'info')
        return redirect(url_for('auth.login', next=url_for('main.story_by_slug', story_slug=story.slug)))
    
    story = Story.query.get_or_404(story_id)
    form = CommentForm()

    if form.validate_on_submit():
        try:
            parent_id = request.form.get('parent_id')
            parent_comment = None
            if parent_id:
                parent_comment = Comment.query.get(parent_id)
                if not parent_comment or parent_comment.story_id != story.id:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'success': False, 'error': 'Invalid parent comment.'}), 400
                    flash('Invalid parent comment.', 'danger')
                    return redirect(url_for('main.story_by_slug', story_slug=story.slug))
            
            comment = Comment(
                content=form.content.data,
                author=current_user,
                story=story,
                parent=parent_comment
            )
            db.session.add(comment)
            
            # Award points logic
            points_earned = 0
            word_count = len(form.content.data.split())
            if word_count >= 20 and current_user.can_earn_comment_points():
                current_user.add_points(4, 'meaningful_comment', f'Comment on {story.title}')
                current_user.comment_points_count += 1
                points_earned = 4
            
            if word_count >= 10 and story.author.can_earn_comment_points():
                story.author.add_points(3, 'received_comment', f'Comment on {story.title}')
                story.author.comment_points_count += 1
            
                db.session.commit()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                response_data = {
                    'success': True,
                    'message': 'Comment posted successfully.'
                }
                if points_earned > 0:
                    response_data['points_earned'] = points_earned
                return jsonify(response_data)
            
            if points_earned > 0:
                flash(f'You earned {points_earned} points for your meaningful comment!', 'success')
            flash('Your comment has been added.', 'success')
            return redirect(url_for('main.story_by_slug', story_slug=story.slug))

        except Exception as e:
            db.session.rollback()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'An internal error occurred while posting the comment.'}), 500
            flash('Error processing comment.', 'error')
        return redirect(url_for('main.story_by_slug', story_slug=story.slug))
    
    # Handle form validation failure
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': False, 'error': 'Invalid data provided.', 'errors': form.errors}), 400
    
    flash('Could not post comment. Please check your input.', 'danger')
    return redirect(url_for('main.story_by_slug', story_slug=story.slug))

@main.route('/story/<story_slug>/comment', methods=['POST'])
def comment_by_slug(story_slug):
    if not current_user.is_authenticated:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Please log in to comment.'}), 401
        flash('Please log in to comment.', 'info')
        return redirect(url_for('auth.login', next=url_for('main.story_by_slug', story_slug=story_slug)))
    
    story = Story.query.filter_by(slug=story_slug).first_or_404()
    form = CommentForm()

    if form.validate_on_submit():
        try:
            parent_id = request.form.get('parent_id')
            parent_comment = None
            if parent_id:
                parent_comment = Comment.query.get(parent_id)
                if not parent_comment or parent_comment.story_id != story.id:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'success': False, 'error': 'Invalid parent comment.'}), 400
                    flash('Invalid parent comment.', 'danger')
                    return redirect(url_for('main.story_by_slug', story_slug=story_slug))
            
            comment = Comment(
                content=form.content.data,
                author=current_user,
                story=story,
                parent=parent_comment
            )
            db.session.add(comment)
            
            # Award points logic
            points_earned = 0
            word_count = len(form.content.data.split())
            if word_count >= 20 and current_user.can_earn_comment_points():
                current_user.add_points(4, 'meaningful_comment', f'Comment on {story.title}')
                current_user.comment_points_count += 1
                points_earned = 4
            
            if word_count >= 10 and story.author.can_earn_comment_points():
                story.author.add_points(3, 'received_comment', f'Comment on {story.title}')
                story.author.comment_points_count += 1
            
            db.session.commit()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                response_data = {
                    'success': True,
                    'message': 'Comment posted successfully.'
                }
                if points_earned > 0:
                    response_data['points_earned'] = points_earned
                return jsonify(response_data)
            
            if points_earned > 0:
                flash(f'You earned {points_earned} points for your meaningful comment!', 'success')
            flash('Your comment has been added.', 'success')
            return redirect(url_for('main.story_by_slug', story_slug=story_slug))

        except Exception as e:
            db.session.rollback()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'An internal error occurred while posting the comment.'}), 500
            flash('Error processing comment.', 'error')
        return redirect(url_for('main.story_by_slug', story_slug=story_slug))
        
    # Handle form validation failure
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': False, 'error': 'Invalid data provided.', 'errors': form.errors}), 400
    
    flash('Could not post comment. Please check your input.', 'danger')
    return redirect(url_for('main.story_by_slug', story_slug=story_slug))

@main.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first_or_404()
    if user == current_user:
        flash('You cannot follow yourself!', 'error')
        return redirect(url_for('main.profile', username=username))
    
    try:
        current_user.follow(user)
        db.session.commit()
        
        # Award points to followed user
        user.add_points(5, 'new_follower', f'Followed by {current_user.username}')
        db.session.commit()
        
        flash(f'You are now following {username}!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error processing follow request. Please try again.', 'error')
    
    return redirect(url_for('main.profile', username=username))

@main.route('/unfollow/<username>')
def unfollow(username):
    if not current_user.is_authenticated:
        flash('Please log in to unfollow users.', 'info')
        return redirect(url_for('auth.login', next=url_for('main.profile', username=username)))
    
    user = User.query.filter_by(username=username).first_or_404()
    if user == current_user:
        flash('You cannot unfollow yourself!', 'warning')
        return redirect(url_for('main.profile', username=username))
    
    current_user.unfollow(user)
    db.session.commit()
    flash(f'You are no longer following {username}.', 'info')
    return redirect(url_for('main.profile', username=username))

@main.route('/tags', methods=['GET', 'POST'])
def tags():
    if request.method == 'POST':
        # Handle interest management
        action = request.form.get('action')
        
        if action == 'add_interest':
            new_interest = request.form.get('new_interest', '').strip().lower()
            if new_interest:
                current_interests = [t.strip().lower() for t in current_user.interests.split(',') if t.strip()] if current_user.interests else []
                if new_interest not in current_interests:
                    current_interests.append(new_interest)
                    current_user.interests = ','.join(current_interests)
                    current_user.has_set_interests = True
                    db.session.commit()
                    flash(f'Added "{new_interest}" to your interests!', 'success')
        
        elif action == 'remove_interest':
            interest_to_remove = request.form.get('interest', '').strip().lower()
            if interest_to_remove and current_user.interests:
                current_interests = [t.strip().lower() for t in current_user.interests.split(',') if t.strip()]
                current_interests = [t for t in current_interests if t != interest_to_remove]
                current_user.interests = ','.join(current_interests) if current_interests else ''
                db.session.commit()
                flash(f'Removed "{interest_to_remove}" from your interests!', 'success')
        
        elif action == 'filter_interests':
            selected_interests = request.form.getlist('selected_interests')
            if selected_interests:
                # Store filtered interests in session for this page
                session['filtered_interests'] = selected_interests
                flash(f'Showing stories for {len(selected_interests)} selected interests!', 'success')
            else:
                session.pop('filtered_interests', None)
                flash('Showing all your interests!', 'success')
        
        return redirect(url_for('main.tags'))
    
    # GET request - display page
    # If user is logged in and has selected interests, show stories matching those interests
    if current_user.is_authenticated and current_user.interests:
        # Get list of interests (tags/genres)
        all_interests = [t.strip().lower() for t in current_user.interests.split(',') if t.strip()]
        
        # Check if user has filtered interests in session
        filtered_interests = session.get('filtered_interests', all_interests)
        
        # Find Tag objects matching these interests (case-insensitive)
        tags = Tag.query.filter(db.func.lower(Tag.name).in_(filtered_interests)).all()
        tag_ids = [tag.id for tag in tags]
        
        # Get stories that have any of these tags, published only, order by newest
        stories = []
        if tag_ids:
            stories = Story.query.filter(
                Story.tags.any(Tag.id.in_(tag_ids)),
                Story.is_published == True
            ).order_by(Story.created_at.desc()).limit(18).all()
        
        # For display, get the tag names (for heading)
        return render_template('tag.html', 
                             user_interests=all_interests, 
                             filtered_interests=filtered_interests,
                             interest_tags=tags, 
                             interest_stories=stories)
    
    # Default: show tag explorer
    return render_template('tag.html')

@main.route('/tags/manage-interests', methods=['POST'])
@login_required
def manage_interests():
    """API endpoint for managing interests from tag page"""
    try:
        data = request.get_json()
        action = data.get('action')
        
        if action == 'add':
            new_interest = data.get('interest', '').strip().lower()
            if new_interest:
                current_interests = [t.strip().lower() for t in current_user.interests.split(',') if t.strip()] if current_user.interests else []
                if new_interest not in current_interests:
                    current_interests.append(new_interest)
                    current_user.interests = ','.join(current_interests)
                    current_user.has_set_interests = True
                    db.session.commit()
                    return jsonify({'success': True, 'message': f'Added "{new_interest}" to your interests!'})
                else:
                    return jsonify({'success': False, 'message': 'Interest already exists!'})
        
        elif action == 'remove':
            interest_to_remove = data.get('interest', '').strip().lower()
            if interest_to_remove and current_user.interests:
                current_interests = [t.strip().lower() for t in current_user.interests.split(',') if t.strip()]
                current_interests = [t for t in current_interests if t != interest_to_remove]
                current_user.interests = ','.join(current_interests) if current_interests else ''
                db.session.commit()
                return jsonify({'success': True, 'message': f'Removed "{interest_to_remove}" from your interests!'})
        
        elif action == 'filter':
            selected_interests = data.get('interests', [])
            if selected_interests:
                session['filtered_interests'] = selected_interests
                return jsonify({'success': True, 'message': f'Showing stories for {len(selected_interests)} selected interests!'})
            else:
                session.pop('filtered_interests', None)
                return jsonify({'success': True, 'message': 'Showing all your interests!'})
        
        return jsonify({'success': False, 'message': 'Invalid action!'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error processing request!'}), 500

@main.route('/tag', methods=['GET'])
def tag_search():
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    tag = None
    stories = None
    
    # Check if search starts with '#' and has content after it
    if search and search.startswith('#') and len(search) > 1:
        # Remove the '#' before searching
        tag_name = search[1:]
        tag = Tag.query.filter(Tag.name.ilike(tag_name)).first()
        if tag:
            stories = Story.query.filter(
                Story.tags.any(id=tag.id),
                Story.is_published == True
            ).order_by(Story.created_at.desc()).paginate(
                page=page, per_page=9, error_out=False)
    
    return render_template('tag.html', tag=tag, stories=stories, search=search)

@main.route('/tag/<tag_name>')
def tag(tag_name):
    tag = Tag.query.filter_by(name=tag_name).first_or_404()
    page = request.args.get('page', 1, type=int)
    stories = Story.query.filter(
        Story.tags.any(id=tag.id),
        Story.is_published == True
    ).order_by(Story.created_at.desc()).paginate(
        page=page, per_page=9, error_out=False)
    return render_template('tag.html', tag=tag, stories=stories, search=None)

@main.route('/search', methods=['GET', 'POST'])
def search():
    form = SearchForm()
    results = []
    
    if form.validate_on_submit() or request.args.get('query'):
        query = form.query.data if form.validate_on_submit() else request.args.get('query')
        # Search for users with similar usernames
        results = User.query.filter(User.username.ilike(f'%{query}%')).all()
        
    return render_template('search.html', form=form, results=results, query=request.args.get('query', ''))

@main.route('/story/<int:story_id>/like', methods=['GET', 'POST'])  # Add POST to allowed methods
def like_story(story_id):
    if not current_user.is_authenticated:
        flash('Please log in to like stories.', 'info')
        return redirect(url_for('auth.login', next=url_for('main.story_by_slug', story_slug=story.slug)))
    
    story = Story.query.get_or_404(story_id)
    if story.author == current_user:
        flash('You cannot like your own story.', 'warning')
        return redirect(url_for('main.story_by_slug', story_slug=story.slug))
    
    if story in current_user.liked_stories:
        current_user.liked_stories.remove(story)
        story.likes = (story.likes or 0) - 1
        db.session.commit()
        flash('You have unliked this story.', 'info')
    else:
        current_user.liked_stories.append(story)
        story.likes = (story.likes or 0) + 1
        db.session.commit()
        flash('You have liked this story.', 'success')
    
    return redirect(url_for('main.story_by_slug', story_slug=story.slug))

@main.route('/story/<story_slug>/like', methods=['GET', 'POST'])
def like_story_by_slug(story_slug):
    if not current_user.is_authenticated:
        flash('Please log in to like stories.', 'info')
        return redirect(url_for('auth.login', next=url_for('main.story_by_slug', story_slug=story_slug)))
    
    story = Story.query.filter_by(slug=story_slug).first_or_404()
    if story.author == current_user:
        flash('You cannot like your own story.', 'warning')
        return redirect(url_for('main.story_by_slug', story_slug=story_slug))
    
    if story in current_user.liked_stories:
        current_user.liked_stories.remove(story)
        story.likes = (story.likes or 0) - 1
        db.session.commit()
        flash('You have unliked this story.', 'info')
    else:
        current_user.liked_stories.append(story)
        story.likes = (story.likes or 0) + 1
        db.session.commit()
        flash('You have liked this story.', 'success')
    
    return redirect(url_for('main.story_by_slug', story_slug=story.slug))

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
        
    return redirect(url_for('main.story_by_slug', story_slug=story.slug))

@main.route('/story/<story_slug>/save')
@login_required
def save_story_by_slug(story_slug):
    story = Story.query.filter_by(slug=story_slug).first_or_404()
    
    # Check if the story is already in the user's reading list
    if story in current_user.saved_stories:
        flash('This story is already in your reading list.')
    else:
        # Add the story to the user's reading list
        current_user.saved_stories.append(story)
        db.session.commit()
        flash('Story saved to your reading list!')
        
    return redirect(url_for('main.story_by_slug', story_slug=story_slug))

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
    # Use the correct form class based on writing_type
    form_classes = {
        'story': StoryForm,
        'poetry': PoetryForm,
        'quote': QuoteForm,
        'essay': EssayForm,
        'other': OtherWritingForm
    }
    FormClass = form_classes.get(story.writing_type, StoryForm)
    form = FormClass(obj=story)
    if form.validate_on_submit():
        story.title = form.title.data if hasattr(form, 'title') else story.title
        story.summary = form.summary.data if hasattr(form, 'summary') else story.summary
        story.content = form.content.data
        story.is_premium = form.is_premium.data if hasattr(form, 'is_premium') else story.is_premium
        story.form_type = form.form_type.data if hasattr(form, 'form_type') else story.form_type
        story.notes = form.notes.data if hasattr(form, 'notes') else story.notes
        story.quote_author = form.author.data if hasattr(form, 'author') else story.quote_author
        story.quote_source = form.source.data if hasattr(form, 'source') else story.quote_source
        story.quote_category = form.category.data if hasattr(form, 'category') else story.quote_category
        story.subtitle = form.subtitle.data if hasattr(form, 'subtitle') else story.subtitle
        story.essay_category = form.category.data if hasattr(form, 'category') else story.essay_category
        story.references = form.references.data if hasattr(form, 'references') else story.references
        story.custom_type = form.custom_type.data if hasattr(form, 'custom_type') else story.custom_type
        # Handle cover image upload
        if hasattr(form, 'cover_image') and form.cover_image.data:
            file = form.cover_image.data
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                story.cover_image = filename
        # Always handle tags for all types
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
        flash('Your story has been updated.', 'success')
        return redirect(url_for('main.story_by_slug', story_slug=story.slug))
    # Pre-fill form for GET
    if request.method == 'GET':
        if hasattr(form, 'title'): form.title.data = story.title
        if hasattr(form, 'summary'): form.summary.data = story.summary
        if hasattr(form, 'content'): form.content.data = story.content
        if hasattr(form, 'is_premium'): form.is_premium.data = story.is_premium
        if hasattr(form, 'form_type'): form.form_type.data = story.form_type
        if hasattr(form, 'notes'): form.notes.data = story.notes
        if hasattr(form, 'author'): form.author.data = story.quote_author
        if hasattr(form, 'source'): form.source.data = story.quote_source
        if hasattr(form, 'category'): form.category.data = story.quote_category or story.essay_category
        if hasattr(form, 'subtitle'): form.subtitle.data = story.subtitle
        if hasattr(form, 'references'): form.references.data = story.references
        if hasattr(form, 'custom_type'): form.custom_type.data = story.custom_type
        if hasattr(form, 'tags'): form.tags.data = ', '.join([tag.name for tag in story.tags])
    return render_template('story/edit.html', title='Edit Story', form=form, story=story)

@main.route('/comment/<int:comment_id>/edit', methods=['POST'])
def edit_comment(comment_id):
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'error': 'Please log in to edit comments.'}), 401
    
    comment = Comment.query.get_or_404(comment_id)
    
    # Check if user can edit this comment
    if comment.author != current_user:
        return jsonify({'success': False, 'error': 'You can only edit your own comments.'}), 403
    
    try:
        data = request.get_json()
        new_content = data.get('content', '').strip()
        
        if not new_content:
            return jsonify({'success': False, 'error': 'Comment cannot be empty.'}), 400
        
        comment.content = new_content
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Comment updated successfully.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Error updating comment.'}), 500

@main.route('/comment/<int:comment_id>/delete', methods=['POST'])
def delete_comment(comment_id):
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'error': 'Please log in to delete comments.'}), 401
    
    comment = Comment.query.get_or_404(comment_id)
    
    # Check if user can delete this comment
    if comment.author != current_user and comment.story.author != current_user:
        return jsonify({'success': False, 'error': 'You can only delete your own comments or comments on your stories.'}), 403
    
    try:
        # Delete replies first
        for reply in comment.replies:
            db.session.delete(reply)
        
        db.session.delete(comment)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Comment deleted successfully.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Error deleting comment.'}), 500

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

@main.route('/story/<story_slug>/unsave', methods=['POST'])
@login_required
def unsave_story_by_slug(story_slug):
    story = Story.query.filter_by(slug=story_slug).first_or_404()
    if story in current_user.saved_stories:
        current_user.saved_stories.remove(story)
        db.session.commit()
        flash('Story removed from your reading list.')
    else:
        flash('Story was not in your reading list.')
    return redirect(request.referrer or url_for('main.story_by_slug', story_slug=story_slug))

@main.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        hide_saved = request.form.get('hide_saved_list') == 'on'
        hide_recent_reads = request.form.get('hide_recent_reads') == 'on'
        current_user.hide_saved_list = hide_saved
        current_user.hide_recent_reads = hide_recent_reads
        db.session.commit()
        flash('Settings updated!', 'success')
        return redirect(url_for('main.settings'))
    return render_template('settings.html', title='Settings', current_theme=current_user.theme)

@main.route('/settings/theme', methods=['POST'])
@login_required
def update_theme():
    try:
        print('Theme update route called')
        data = request.get_json()
        print('Received data:', data)
        if not data:
            print('No data provided')
            return jsonify({'error': 'No data provided'}), 400
        theme = data.get('theme', 'light')
        print('Theme to save:', theme)
        if theme not in ['light', 'dark']:
            print('Invalid theme value')
            return jsonify({'error': 'Invalid theme'}), 400
        current_user.theme = theme
        db.session.commit()
        print('Theme saved successfully for user:', current_user.username)
        return jsonify({'success': True, 'theme': theme})
    except Exception as e:
        print('Error in theme update:', str(e))
        return jsonify({'error': str(e)}), 500

@main.route('/settings/disable-account', methods=['POST'])
@login_required
def disable_account():
    """Disable user account"""
    try:
        reason = request.form.get('reason', 'User requested account disable')
        current_user.disable_account(reason)
        logout_user()
        flash('Your account has been disabled. You can re-enable it by logging back in.', 'info')
        return redirect(url_for('main.index'))
    except Exception as e:
        flash('Error disabling account. Please try again.', 'error')
        return redirect(url_for('main.settings'))

@main.route('/settings/request-deletion', methods=['POST'])
@login_required
def request_account_deletion():
    """Request account deletion (20-day waiting period)"""
    try:
        reason = request.form.get('reason', 'User requested account deletion')
        current_user.request_deletion(reason)
        logout_user()
        flash('Your account deletion has been requested. You have 20 days to cancel by logging back in.', 'warning')
        return redirect(url_for('main.index'))
    except Exception as e:
        flash('Error requesting account deletion. Please try again.', 'error')
        return redirect(url_for('main.settings'))

@main.route('/settings/cancel-deletion', methods=['POST'])
@login_required
def cancel_account_deletion():
    """Cancel account deletion request"""
    try:
        current_user.cancel_deletion()
        flash('Your account deletion has been cancelled. Your account is now active.', 'success')
        return redirect(url_for('main.settings'))
    except Exception as e:
        flash('Error cancelling account deletion. Please try again.', 'error')
        return redirect(url_for('main.settings'))

@main.route('/admin/delete-expired-accounts', methods=['POST'])
@login_required
def delete_expired_accounts():
    """Admin route to delete accounts that have passed the 20-day waiting period"""
    if not current_user.is_authenticated or current_user.username != 'admin':  # Simple admin check
        abort(403)
    
    try:
        # Find accounts that have passed the 20-day waiting period
        cutoff_date = datetime.utcnow() - timedelta(days=20)
        expired_accounts = User.query.filter(
            User.deletion_requested_at.isnot(None),
            User.deletion_requested_at <= cutoff_date
        ).all()
        
        deleted_count = 0
        for user in expired_accounts:
            try:
                user.delete_account_permanently()
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting user {user.id}: {e}")
        
        flash(f'Successfully deleted {deleted_count} expired accounts.', 'success')
        return redirect(url_for('main.settings'))
    except Exception as e:
        flash('Error deleting expired accounts.', 'error')
        return redirect(url_for('main.settings'))

@main.route('/history/delete/<int:history_id>', methods=['POST'])
@login_required
def delete_history_item(history_id):
    # Try to find in story reading history first
    history = ReadingHistory.query.get(history_id)
    if history and history.user_id == current_user.id:
        db.session.delete(history)
        db.session.commit()
        flash('History item deleted.', 'success')
        return redirect(request.referrer or url_for('main.profile', username=current_user.username))
        
    # If not found in story history, try chapter reading history
    chapter_history = ChapterReadingHistory.query.get(history_id)
    if chapter_history and chapter_history.user_id == current_user.id:
        db.session.delete(chapter_history)
        db.session.commit()
        flash('History item deleted.', 'success')
        return redirect(request.referrer or url_for('main.profile', username=current_user.username))
    
    # If neither found, return 404
    abort(404)

# Webnovel creation routes
@main.route('/novel/new', methods=['GET', 'POST'])
@login_required
def new_novel():
    form = NovelForm()
    if form.validate_on_submit():
        # Normalize genres: lowercase, trim, remove empty
        genres = [g.strip().lower() for g in form.genre.data.split(',') if g.strip()]
        genre_str = ', '.join(genres)
        # Auto-create Tag objects for each genre if not exist
        tag_objs = []
        for genre in genres:
            tag = Tag.query.filter_by(name=genre).first()
            if not tag:
                tag = Tag(name=genre)
                db.session.add(tag)
                db.session.flush()  # Ensure tag.id is available
            tag_objs.append(tag)
        story = Story(
            title=form.title.data,
            content='',
            summary=form.summary.data,
            is_premium=form.is_premium.data,
            author=current_user,
            is_published=False,
            writing_type='webnovel'
        )
        story.tags = tag_objs  # Associate story with genre tags
        db.session.add(story)
        db.session.flush()  # Get story.id before commit
        novel = Novel(
            story_id=story.id,
            title=form.title.data,
            summary=form.summary.data,
            genre=genre_str,
            cover_image=None,
            is_premium=form.is_premium.data
        )
        file = form.cover_image.data
        if isinstance(file, FileStorage) and file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            novel.cover_image = filename
        db.session.add(novel)
        db.session.commit()
        flash('Novel created! Now add volumes and chapters.')
        return redirect(url_for('main.novel_detail_slug', novel_slug=novel.slug))
    # Set submit button text for creation
    form.submit.label.text = 'Create Novel'
    return render_template('writings/novel.html', form=form)

@main.route('/novel/<novel_slug>')
def novel_detail_slug(novel_slug):
    from datetime import datetime, timedelta
    novel = Novel.query.filter_by(slug=novel_slug).first_or_404()
    chapters = Chapter.query.filter_by(novel_id=novel.id).order_by(Chapter.order.asc()).all()
    volumes = Volume.query.filter_by(novel_id=novel.id).order_by(Volume.order.asc()).all()

    unlocked = False
    if current_user.is_authenticated and novel.is_premium and novel.story.author != current_user:
        unlocked = UnlockedContent.query.filter_by(user_id=current_user.id, novel_id=novel.id).first() is not None
    
    # Get first chapter
    first_chapter = Chapter.query.filter_by(novel_id=novel.id).order_by(Chapter.order.asc()).first()

    # Get last read chapter for this user and novel
    last_read_chapter = None
    if current_user.is_authenticated:
        from app.models import ChapterReadingHistory
        chapter_history = ChapterReadingHistory.query.filter_by(user_id=current_user.id, novel_id=novel.id).first()
        if chapter_history:
            last_read_chapter = Chapter.query.get(chapter_history.chapter_id)

    now = datetime.utcnow()
    return render_template(
        'writings/novel_detail.html',
        novel=novel,
        chapters=chapters,
        volumes=volumes,
        unlocked=unlocked,
        form=CommentForm(),
        Comment=Comment,
        first_chapter=first_chapter,
        last_read_chapter=last_read_chapter,
        now=now,
        timedelta=timedelta
    )

@main.route('/novel/<novel_slug>/volume/new', methods=['GET', 'POST'])
@login_required
def new_volume(novel_slug):
    novel = Novel.query.filter_by(slug=novel_slug).first_or_404()
    form = VolumeForm()
    if form.validate_on_submit():
        volume = Volume(
            novel_id=novel.id,
            title=form.title.data,
            summary=form.summary.data,
            order=int(form.order.data),
            is_premium=form.is_premium.data
        )
        db.session.add(volume)
        db.session.commit()
        flash('Volume added!')
        return redirect(url_for('main.novel_detail_slug', novel_slug=novel.slug))
    # Set submit button text for creation
    form.submit.label.text = 'Add Volume'
    return render_template('writings/volume.html', form=form, novel=novel)

@main.route('/novel/<novel_slug>/volume/<volume_slug>/chapter/new', methods=['GET', 'POST'])
@login_required
def new_chapter(novel_slug, volume_slug):
    novel = Novel.query.filter_by(slug=novel_slug).first_or_404()
    volume = Volume.query.filter_by(novel_id=novel.id, slug=volume_slug).first_or_404()
    form = ChapterForm()
    if form.validate_on_submit():
        chapter = Chapter(
            novel_id=novel.id,
            volume_id=volume.id,
            title=form.title.data,
            content=form.content.data,
            order=int(form.order.data),
            is_premium=form.is_premium.data,
            author_notes=form.author_notes.data,
            is_draft=form.is_draft.data
        )
        db.session.add(chapter)
        db.session.commit()
        flash('Chapter added!')
        return redirect(url_for('main.novel_detail_slug', novel_slug=novel.slug))
    # Set submit button text for creation
    form.submit.label.text = 'Add Chapter'
    return render_template('writings/chapter.html', form=form, novel=novel, volume=volume)

@main.route('/novel/<novel_slug>/edit', methods=['GET', 'POST'])
@login_required
def edit_novel(novel_slug):
    novel = Novel.query.filter_by(slug=novel_slug).first_or_404()
    story = novel.story
    if story.author != current_user:
        abort(403)
    form = NovelForm(obj=novel)
    if form.validate_on_submit():
        # Normalize genres: lowercase, trim, remove empty
        genres = [g.strip().lower() for g in form.genre.data.split(',') if g.strip()]
        genre_str = ', '.join(genres)
        # Auto-create Tag objects for each genre if not exist
        tag_objs = []
        for genre in genres:
            tag = Tag.query.filter_by(name=genre).first()
            if not tag:
                tag = Tag(name=genre)
                db.session.add(tag)
                db.session.flush()
            tag_objs.append(tag)
        story.tags = tag_objs  # Associate story with genre tags
        # Check if premium status is being removed
        was_premium = novel.is_premium
        new_premium_status = form.is_premium.data
        novel.title = form.title.data
        novel.summary = form.summary.data
        novel.genre = genre_str
        novel.status = form.status.data
        novel.is_mature = form.is_mature.data
        novel.is_premium = new_premium_status  # Update novel premium status
        # Update slug if title changed
        novel.update_slug()
        file = form.cover_image.data
        if isinstance(file, FileStorage) and file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            novel.cover_image = filename
            story.cover_image = filename
        # Sync Story fields with Novel
        story.title = form.title.data
        story.summary = form.summary.data
        story.is_premium = new_premium_status  # Update story premium status
        # If premium status was removed, delete all unlock records for this novel
        if was_premium and not new_premium_status:
            UnlockedContent.query.filter_by(novel_id=novel.id).delete()
        # Handle tags for forms with a tags field (for non-genre tags)
        if hasattr(form, 'tags') and form.tags.data:
            tag_names = [t.strip() for t in form.tags.data.split(',') if t.strip()]
            for tag_name in tag_names:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                if tag not in story.tags:
                    story.tags.append(tag)
        db.session.commit()
        flash('Novel updated!', 'success')
        return redirect(url_for('main.novel_detail_slug', novel_slug=novel.slug))
    elif request.method == 'GET':
        # Pre-populate form with current values
        form.title.data = novel.title
        form.summary.data = novel.summary
        form.genre.data = novel.genre
        form.status.data = novel.status
        form.is_mature.data = novel.is_mature
        form.is_premium.data = novel.is_premium
        if hasattr(form, 'tags'):
            form.tags.data = ', '.join([tag.name for tag in story.tags])
        # Set submit button text for editing
        form.submit.label.text = 'Update Novel'
    return render_template('writings/novel.html', form=form, novel=novel)

@main.route('/novel/<novel_slug>/delete', methods=['POST'])
@login_required
def delete_novel(novel_slug):
    novel = Novel.query.filter_by(slug=novel_slug).first_or_404()
    story = novel.story
    if story.author != current_user:
        abort(403)
    db.session.delete(novel)
    db.session.delete(story)
    db.session.commit()
    flash('Novel and all its volumes and chapters deleted.', 'success')
    return redirect(url_for('main.profile', username=current_user.username))

@main.route('/volume/<volume_slug>/edit', methods=['GET', 'POST'])
@login_required
def edit_volume(volume_slug):
    volume = Volume.query.filter_by(slug=volume_slug).first_or_404()
    novel = volume.novel
    story = novel.story
    if story.author != current_user:
        abort(403)
    form = VolumeForm(obj=volume)
    if form.validate_on_submit():
        # Check if premium status is being removed
        was_premium = volume.is_premium
        new_premium_status = form.is_premium.data
        
        volume.title = form.title.data
        volume.summary = form.summary.data
        volume.order = int(form.order.data)
        volume.is_premium = new_premium_status  # Update volume premium status
        
        # If premium status was removed, delete all unlock records for this volume
        if was_premium and not new_premium_status:
            UnlockedContent.query.filter_by(volume_id=volume.id).delete()
        
        # Update slug if title changed
        volume.slug = slugify(volume.title)
        db.session.commit()
        flash('Volume updated!', 'success')
        return redirect(url_for('main.novel_detail_slug', novel_slug=novel.slug))
    elif request.method == 'GET':
        # Pre-populate form with current values
        form.title.data = volume.title
        form.summary.data = volume.summary
        form.order.data = str(volume.order)
        form.is_premium.data = volume.is_premium
        # Set submit button text for editing
        form.submit.label.text = 'Update Volume'
    return render_template('writings/volume.html', form=form, novel=novel, volume=volume)

@main.route('/volume/<volume_slug>/delete', methods=['POST'])
@login_required
def delete_volume(volume_slug):
    volume = Volume.query.filter_by(slug=volume_slug).first_or_404()
    novel = volume.novel
    story = novel.story
    if story.author != current_user:
        abort(403)
    db.session.delete(volume)
    db.session.commit()
    flash('Volume and all its chapters deleted.', 'success')
    return redirect(url_for('main.novel_detail_slug', novel_slug=novel.slug))

@main.route('/chapter/<chapter_slug>/edit', methods=['GET', 'POST'])
@login_required
def edit_chapter(chapter_slug):
    chapter = Chapter.query.filter_by(slug=chapter_slug).first_or_404()
    novel = chapter.novel
    story = novel.story
    if story.author != current_user:
        abort(403)
    form = ChapterForm(obj=chapter)
    if form.validate_on_submit():
        # Check if premium status is being removed
        was_premium = chapter.is_premium
        new_premium_status = form.is_premium.data
        
        chapter.title = form.title.data
        chapter.content = form.content.data
        chapter.order = int(form.order.data)
        chapter.author_notes = form.author_notes.data
        chapter.is_draft = form.is_draft.data
        chapter.is_premium = new_premium_status  # Update chapter premium status
        
        # If premium status was removed, delete all unlock records for this chapter
        if was_premium and not new_premium_status:
            UnlockedContent.query.filter_by(chapter_id=chapter.id).delete()
        
        # Update slug if title changed
        chapter.slug = slugify(chapter.title)
        db.session.commit()
        flash('Chapter updated!', 'success')
        return redirect(url_for('main.novel_detail_slug', novel_slug=novel.slug))
    elif request.method == 'GET':
        # Pre-populate form with current values
        form.title.data = chapter.title
        form.content.data = chapter.content
        form.order.data = chapter.order
        form.author_notes.data = chapter.author_notes
        form.is_draft.data = chapter.is_draft
        form.is_premium.data = chapter.is_premium
        # Set submit button text for editing
        form.submit.label.text = 'Update Chapter'
    return render_template('writings/chapter.html', form=form, novel=novel, volume=chapter.volume, chapter=chapter)

@main.route('/chapter/<chapter_slug>/delete', methods=['POST'])
@login_required
def delete_chapter(chapter_slug):
    chapter = Chapter.query.filter_by(slug=chapter_slug).first_or_404()
    novel = chapter.novel
    story = novel.story
    if story.author != current_user:
        abort(403)
    db.session.delete(chapter)
    db.session.commit()
    flash('Chapter deleted.', 'success')
    return redirect(url_for('main.novel_detail_slug', novel_slug=novel.slug))

@main.route('/novel/<novel_slug>/<volume_slug>')
def volume_detail_slug(novel_slug, volume_slug):
    novel = Novel.query.filter_by(slug=novel_slug).first_or_404()
    volume = Volume.query.filter_by(slug=volume_slug, novel_id=novel.id).first_or_404()
    chapters = volume.chapters.order_by(Chapter.order).all()
    
    unlocked = False
    if current_user.is_authenticated and volume.is_premium and novel.story.author != current_user:
        unlocked = UnlockedContent.query.filter_by(user_id=current_user.id, volume_id=volume.id).first() is not None
    
    return render_template('writings/volume_detail.html', novel=novel, volume=volume, chapters=chapters, unlocked=unlocked)

@main.route('/novel/<novel_slug>/<volume_slug>/<chapter_slug>')
def chapter_view_slug(novel_slug, volume_slug, chapter_slug):
    novel = Novel.query.filter_by(slug=novel_slug).first_or_404()
    volume = Volume.query.filter_by(slug=volume_slug, novel_id=novel.id).first() # Volume can be null
    chapter = Chapter.query.filter_by(slug=chapter_slug, novel_id=novel.id).first_or_404()
    
    login_form = LoginForm() if not current_user.is_authenticated else None
    
    unlocked = False
    if current_user.is_authenticated and chapter.is_premium_content and novel.story.author != current_user:
        unlocked = UnlockedContent.query.filter_by(user_id=current_user.id, chapter_id=chapter.id).first() is not None

    # Track chapter reading history for authenticated users
    if current_user.is_authenticated:
        # Check if there's already an entry for this user and novel
        existing_history = ChapterReadingHistory.query.filter_by(
            user_id=current_user.id, 
            novel_id=novel.id
        ).first()
        
        if existing_history:
            # Update existing entry with new chapter and timestamp
            existing_history.chapter_id = chapter.id
            existing_history.timestamp = datetime.utcnow()
        else:
            # Create new entry
            new_history = ChapterReadingHistory(
                user_id=current_user.id,
                novel_id=novel.id,
                chapter_id=chapter.id
            )
            db.session.add(new_history)
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            # Don't fail the page load if history tracking fails

    # Get previous and next chapters for navigation
    prev_chapter = Chapter.query.filter(
        Chapter.novel_id == novel.id,
        Chapter.order < chapter.order
    ).order_by(Chapter.order.desc()).first()

    next_chapter = Chapter.query.filter(
        Chapter.novel_id == novel.id,
        Chapter.order > chapter.order
    ).order_by(Chapter.order.asc()).first()

    return render_template('writings/chapter_view.html',
                           novel=novel,
                           volume=volume,
                           chapter=chapter,
                           prev_chapter=prev_chapter,
                           next_chapter=next_chapter,
                           unlocked=unlocked,
                           login_form=login_form)

@main.route('/feed')
@login_required
def feed():
    # Get the IDs of users that the current user follows
    following_ids = [follow.followed_id for follow in current_user.following]
    # Get stories from followed users, ordered by creation date
    stories = Story.query.filter(
        Story.author_id.in_(following_ids),
        Story.is_published == True
    ).order_by(Story.created_at.desc()).all()
    # Annotate each story with unlocked_by_current_user for premium stories
    from app.models import UnlockedContent
    unlocked_story_ids = set(
        uc.story_id for uc in UnlockedContent.query.filter_by(user_id=current_user.id).all() if uc.story_id is not None
    )
    for story in stories:
        if story.is_premium:
            story.unlocked_by_current_user = (story.id in unlocked_story_ids)
        else:
            story.unlocked_by_current_user = True  # Non-premium stories are always unlocked
    return render_template('story/feed.html', stories=stories)

@main.route('/drafts')
@login_required
def drafts():
    drafts = Story.query.filter_by(author=current_user, is_published=False).order_by(Story.updated_at.desc()).all()
    return render_template('drafts.html', title='My Drafts', drafts=drafts)

@main.route('/statistics')
@login_required
def statistics():
    # Get overall statistics
    overall_stats = {
        'views': db.session.query(db.func.sum(Story.views)).filter(Story.author_id == current_user.id).scalar() or 0,
        'likes': db.session.query(db.func.sum(Story.likes)).filter(Story.author_id == current_user.id).scalar() or 0,
        'comments': db.session.query(db.func.count(Comment.id)).filter(Comment.story_id.in_(
            db.session.query(Story.id).filter(Story.author_id == current_user.id)
        )).scalar() or 0,
        'followers': current_user.followers.count()
    }

    # Get monthly statistics
    month_ago = datetime.utcnow() - timedelta(days=30)
    monthly_stats = {
        'views': db.session.query(db.func.sum(Story.views)).filter(
            Story.author_id == current_user.id,
            Story.created_at >= month_ago
        ).scalar() or 0,
        'likes': db.session.query(db.func.sum(Story.likes)).filter(
            Story.author_id == current_user.id,
            Story.created_at >= month_ago
        ).scalar() or 0,
        'comments': db.session.query(db.func.count(Comment.id)).filter(
            Comment.story_id.in_(
                db.session.query(Story.id).filter(Story.author_id == current_user.id)
            ),
            Comment.created_at >= month_ago
        ).scalar() or 0,
        'new_followers': db.session.query(db.func.count(Follow.id)).filter(
            Follow.followed_id == current_user.id,
            Follow.created_at >= month_ago
        ).scalar() or 0
    }

    # Get weekly statistics
    week_ago = datetime.utcnow() - timedelta(days=7)
    weekly_stats = {
        'views': db.session.query(db.func.sum(Story.views)).filter(
            Story.author_id == current_user.id,
            Story.created_at >= week_ago
        ).scalar() or 0,
        'likes': db.session.query(db.func.sum(Story.likes)).filter(
            Story.author_id == current_user.id,
            Story.created_at >= week_ago
        ).scalar() or 0,
        'comments': db.session.query(db.func.count(Comment.id)).filter(
            Comment.story_id.in_(
                db.session.query(Story.id).filter(Story.author_id == current_user.id)
            ),
            Comment.created_at >= week_ago
        ).scalar() or 0,
        'new_followers': db.session.query(db.func.count(Follow.id)).filter(
            Follow.followed_id == current_user.id,
            Follow.created_at >= week_ago
        ).scalar() or 0
    }

    # Calculate Pulse Score
    # MS = RoundTo10(0.05F + 0.02√V + 0.1L + 0.5C)
    # Where F = followers, V = views in last 20 days, L = likes, C = comments
    twenty_days_ago = datetime.utcnow() - timedelta(days=20)
    recent_views = db.session.query(db.func.sum(Story.views)).filter(
        Story.author_id == current_user.id,
        Story.created_at >= twenty_days_ago
    ).scalar() or 0

    pulse_score = 0.05 * overall_stats['followers'] + \
                 0.02 * math.sqrt(recent_views) + \
                 0.1 * overall_stats['likes'] + \
                 0.5 * overall_stats['comments']
    
    # Round to nearest multiple of 10
    pulse_score = round(pulse_score / 10) * 10

    # Determine tier and message
    if pulse_score >= 250:
        tier = "Nova"
        tier_emoji = "✨🟡"
        message = "You're shining brighter than ever. Keep inspiring, creating, and leading by example — you're setting the bar."
    elif pulse_score >= 200:
        tier = "Surge"
        tier_emoji = "🟤"
        message = "Your reach and influence are expanding. Your content is thriving — this is your creative zone."
    elif pulse_score >= 170:
        tier = "Pulse"
        tier_emoji = "🟣"
        message = "You're in sync with your audience! This is a strong, active phase. Lean into it and share your best work."
    elif pulse_score >= 140:
        tier = "Shine"
        tier_emoji = "🔵"
        message = "You're becoming a familiar name. Your effort shows — stay consistent and keep the energy high."
    elif pulse_score >= 110:
        tier = "Glow"
        tier_emoji = "🟢"
        message = "Your content is connecting! Now's the time to build your style, voice, and loyal readers."
    elif pulse_score >= 80:
        tier = "Flame"
        tier_emoji = "🟡"
        message = "You're heating up! People are noticing your work — keep up the momentum and stay active."
    elif pulse_score >= 50:
        tier = "Spark"
        tier_emoji = "🟠"
        message = "You're beginning to find your rhythm! Keep sharing and engaging to grow your presence."
    else:
        tier = "Seed"
        tier_emoji = "🔴"
        message = "You're just starting out. Post consistently, explore your voice, and connect with readers — small steps lead to big progress."

    return render_template('statistics.html',
                         title='Statistics',
                         overall_stats=overall_stats,
                         monthly_stats=monthly_stats,
                         weekly_stats=weekly_stats,
                         pulse_score=pulse_score,
                         tier=tier,
                         tier_emoji=tier_emoji,
                         tier_message=message)

@main.route('/story/<int:story_id>/share', methods=['POST'])
@login_required
def share_story(story_id):
    story = Story.query.get_or_404(story_id)
    try:
        if current_user.can_earn_share_points():
            current_user.add_points(5, 'share_story', f'Shared {story.title}')
            current_user.share_points_count += 1
            db.session.commit()
            flash('You earned 5 points for sharing!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error processing share. Please try again.', 'error')
    
    return redirect(url_for('main.story_by_slug', story_slug=story.slug))

@main.route('/story/<story_slug>/share', methods=['POST'])
@login_required
def share_story_by_slug(story_slug):
    story = Story.query.filter_by(slug=story_slug).first_or_404()
    try:
        if current_user.can_earn_share_points():
            current_user.add_points(5, 'share_story', f'Shared {story.title}')
            current_user.share_points_count += 1
            db.session.commit()
            flash('You earned 5 points for sharing!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error processing share. Please try again.', 'error')
    
    return redirect(url_for('main.story_by_slug', story_slug=story.slug))

@main.route('/story/<story_slug>/track-share', methods=['POST'])
@login_required
def track_story_share(story_slug):
    """Track any type of sharing action and award points for first 2 shares per day"""
    story = Story.query.filter_by(slug=story_slug).first_or_404()
    share_type = request.form.get('share_type', 'general')  # general, twitter, facebook, linkedin, copy
    
    try:
        if current_user.can_earn_share_points():
            current_user.add_points(5, 'share_story', f'Shared {story.title} via {share_type}')
            current_user.share_points_count += 1
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'You earned 5 points for sharing!',
                'points_earned': 5,
                'remaining_shares': 2 - current_user.share_points_count
            })
        else:
            return jsonify({
                'success': False,
                'message': 'You have already earned the maximum share points for today.',
                'points_earned': 0,
                'remaining_shares': 0
            })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Error processing share. Please try again.',
            'points_earned': 0,
            'remaining_shares': 0
        }), 500

@main.route('/redeem', methods=['GET', 'POST'])
@login_required
def redeem_points():
    if request.method == 'POST':
        try:
            action = request.form.get('action')
            item_id = request.form.get('item_id')
            
            redemption_costs = {
                'premium_post': 50,
                'premium_volume': 100,
                'premium_novel': 250,
                'feature_post': 150
            }
            
            if action not in redemption_costs:
                flash('Invalid redemption action', 'error')
                return redirect(url_for('main.redeem_points'))
            
            required_points = redemption_costs[action]
            
            if not current_user.has_enough_points(required_points):
                flash('Not enough points for this redemption', 'error')
                return redirect(url_for('main.redeem_points'))
            
            if action == 'premium_post':
                story = Story.query.get_or_404(item_id)
                if story.is_premium:
                    current_user.add_points(-required_points, 'redeem_premium_post', f'Unlocked {story.title}')
                    flash(f'Successfully unlocked {story.title}!', 'success')
            
            elif action == 'premium_volume':
                volume = Volume.query.get_or_404(item_id)
                if volume.is_premium:
                    current_user.add_points(-required_points, 'redeem_premium_volume', f'Unlocked {volume.title}')
                    flash(f'Successfully unlocked {volume.title}!', 'success')
            
            elif action == 'premium_novel':
                novel = Novel.query.get_or_404(item_id)
                if novel.is_premium:
                    current_user.add_points(-required_points, 'redeem_premium_novel', f'Unlocked {novel.title}')
                    flash(f'Successfully unlocked {novel.title}!', 'success')
            
            elif action == 'feature_post':
                story = Story.query.get_or_404(item_id)
                if not story.is_featured:
                    story.is_featured = True
                    story.featured_at = datetime.utcnow()  # Set the featuring timestamp
                    current_user.add_points(-required_points, 'feature_post', f'Featured {story.title}')
                    flash(f'Successfully featured {story.title}! It will be featured for 24 hours.', 'success')
            
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash('Error processing redemption. Please try again.', 'error')
        
        return redirect(url_for('main.redeem_points'))
    
    # Get user's point transactions
    transactions = PointsTransaction.query.filter_by(user_id=current_user.id).order_by(PointsTransaction.timestamp.desc()).all()
    
    # Get IDs of users the current user is following
    following_ids = [follow.followed_id for follow in current_user.following]

    # Get IDs of content already unlocked by the user
    unlocked_story_ids = [uc.story_id for uc in UnlockedContent.query.filter_by(user_id=current_user.id).filter(UnlockedContent.story_id.isnot(None)).all()]
    unlocked_novel_ids = [uc.novel_id for uc in UnlockedContent.query.filter_by(user_id=current_user.id).filter(UnlockedContent.novel_id.isnot(None)).all()]
    unlocked_volume_ids = [uc.volume_id for uc in UnlockedContent.query.filter_by(user_id=current_user.id).filter(UnlockedContent.volume_id.isnot(None)).all()]

    # Get available premium content from followed authors that is not yet unlocked
    premium_stories = []
    if following_ids:
        premium_stories = Story.query.filter(
            Story.is_premium == True,
            Story.author_id != current_user.id,
            Story.author_id.in_(following_ids),
            Story.id.notin_(unlocked_story_ids)
        ).all()

    premium_volumes = []
    if following_ids:
        premium_volumes = Volume.query.join(Novel).join(Story).filter(
            Volume.is_premium == True,
            Story.author_id != current_user.id,
            Story.author_id.in_(following_ids),
            Volume.id.notin_(unlocked_volume_ids)
        ).all()

    premium_novels = []
    if following_ids:
        premium_novels = Novel.query.join(Story).filter(
            Novel.is_premium == True,
            Story.author_id != current_user.id,
            Story.author_id.in_(following_ids),
            Novel.id.notin_(unlocked_novel_ids)
        ).all()

    # Get data for premium content unlocked by others from the current user's content
    unlocked_user_premium_content = []

    # Unlocked Stories
    user_premium_stories = Story.query.filter_by(author_id=current_user.id, is_premium=True).all()
    for story in user_premium_stories:
        unlocked = UnlockedContent.query.filter_by(story_id=story.id).all()
        for entry in unlocked:
            transaction = PointsTransaction.query.filter_by(
                user_id=entry.user_id,
                action='unlock_premium_story',
                details=f'Unlocked story: {story.title}'
            ).order_by(PointsTransaction.timestamp.desc()).first() # Get the most recent one if duplicates
            if transaction:
                unlocked_user_premium_content.append({
                    'unlocked_by': entry.user,
                    'content_type': 'Story',
                    'title': story.title,
                    'points_spent': -transaction.points, # Points are negative when spent
                    'timestamp': transaction.timestamp
                })

    # Unlocked Novels
    user_premium_novels = Novel.query.filter_by(story_id=Story.id, is_premium=True).join(Story).filter(Story.author_id==current_user.id).all()
    for novel in user_premium_novels:
        unlocked = UnlockedContent.query.filter_by(novel_id=novel.id).all()
        for entry in unlocked:
            transaction = PointsTransaction.query.filter_by(
                user_id=entry.user_id,
                action='unlock_premium_novel',
                details=f'Unlocked novel: {novel.title}'
            ).order_by(PointsTransaction.timestamp.desc()).first()
            if transaction:
                unlocked_user_premium_content.append({
                    'unlocked_by': entry.user,
                    'content_type': 'Novel',
                    'title': novel.title,
                    'points_spent': -transaction.points,
                    'timestamp': transaction.timestamp
                })

    # Unlocked Volumes
    user_premium_volumes = Volume.query.filter_by(novel_id=Novel.id, is_premium=True).join(Novel).join(Story).filter(Story.author_id==current_user.id).all()
    for volume in user_premium_volumes:
        unlocked = UnlockedContent.query.filter_by(volume_id=volume.id).all()
        for entry in unlocked:
            transaction = PointsTransaction.query.filter_by(
                user_id=entry.user_id,
                action='unlock_premium_volume',
                details=f'Unlocked volume: {volume.title}'
            ).order_by(PointsTransaction.timestamp.desc()).first()
            if transaction:
                unlocked_user_premium_content.append({
                    'unlocked_by': entry.user,
                    'content_type': 'Volume',
                    'title': volume.title,
                    'points_spent': -transaction.points,
                    'timestamp': transaction.timestamp
                })

    # Unlocked Chapters
    user_premium_chapters = Chapter.query.filter_by(novel_id=Novel.id, is_premium=True).join(Novel).join(Story).filter(Story.author_id==current_user.id).all()
    for chapter in user_premium_chapters:
        unlocked = UnlockedContent.query.filter_by(chapter_id=chapter.id).all()
        for entry in unlocked:
            transaction = PointsTransaction.query.filter_by(
                user_id=entry.user_id,
                action='unlock_premium_chapter',
                details=f'Unlocked chapter: {chapter.title}'
            ).order_by(PointsTransaction.timestamp.desc()).first()
            if transaction:
                unlocked_user_premium_content.append({
                    'unlocked_by': entry.user,
                    'content_type': 'Chapter',
                    'title': chapter.title,
                    'points_spent': -transaction.points,
                    'timestamp': transaction.timestamp
                })
    
    # Sort by timestamp
    unlocked_user_premium_content.sort(key=lambda x: x['timestamp'], reverse=True)

    # Get content unlocked by current user
    user_unlocked_content = []
    
    # Get unlocked stories
    unlocked_stories = UnlockedContent.query.filter(
        UnlockedContent.user_id == current_user.id,
        UnlockedContent.story_id.isnot(None)
    ).all()
    for entry in unlocked_stories:
        story = Story.query.get(entry.story_id)
        if story and story.is_premium:
            user_unlocked_content.append({
                'content_type': 'Story',
                'title': story.title,
                'author': story.author.username,
                'unlocked_at': entry.unlocked_at,
                'story_slug': story.slug
            })
    
    # Get unlocked novels
    unlocked_novels = UnlockedContent.query.filter(
        UnlockedContent.user_id == current_user.id,
        UnlockedContent.novel_id.isnot(None)
    ).all()
    for entry in unlocked_novels:
        novel = Novel.query.get(entry.novel_id)
        if novel and novel.is_premium:
            user_unlocked_content.append({
                'content_type': 'Novel',
                'title': novel.title,
                'author': novel.story.author.username,
                'unlocked_at': entry.unlocked_at,
                'novel_slug': novel.slug
            })
    
    # Get unlocked volumes
    unlocked_volumes = UnlockedContent.query.filter(
        UnlockedContent.user_id == current_user.id,
        UnlockedContent.volume_id.isnot(None)
    ).all()
    for entry in unlocked_volumes:
        volume = Volume.query.get(entry.volume_id)
        if volume and volume.is_premium:
            user_unlocked_content.append({
                'content_type': 'Volume',
                'title': volume.title,
                'author': volume.novel.story.author.username,
                'unlocked_at': entry.unlocked_at,
                'novel_slug': volume.novel.slug,
                'volume_slug': volume.slug
            })
    
    # Get unlocked chapters
    unlocked_chapters = UnlockedContent.query.filter(
        UnlockedContent.user_id == current_user.id,
        UnlockedContent.chapter_id.isnot(None)
    ).all()
    for entry in unlocked_chapters:
        chapter = Chapter.query.get(entry.chapter_id)
        if chapter and chapter.is_premium_content:
            user_unlocked_content.append({
                'content_type': 'Chapter',
                'title': chapter.title,
                'author': chapter.novel.story.author.username,
                'unlocked_at': entry.unlocked_at,
                'novel_slug': chapter.novel.slug,
                'volume_slug': chapter.volume.slug if chapter.volume else 'null',
                'chapter_slug': chapter.slug
            })
    
    # Sort by unlock date
    user_unlocked_content.sort(key=lambda x: x['unlocked_at'], reverse=True)

    return render_template('redeem.html',
                         title='Redeem Points',
                         transactions=transactions,
                         premium_stories=premium_stories,
                         premium_volumes=premium_volumes,
                         premium_novels=premium_novels,
                         unlocked_user_premium_content=unlocked_user_premium_content,
                         user_unlocked_content=user_unlocked_content)

@main.route('/story/<int:story_id>/unlock', methods=['POST'])
@login_required
def unlock_story(story_id):
    story = Story.query.get_or_404(story_id)
    required_points = 50  # Define points cost for story

    if story.author == current_user:
        flash('You own this story, no need to unlock!', 'info')
        return redirect(url_for('main.story_by_slug', story_slug=story.slug))
    
    already_unlocked = UnlockedContent.query.filter_by(user_id=current_user.id, story_id=story_id).first()
    if already_unlocked:
        flash('You have already unlocked this story.', 'info')
        return redirect(url_for('main.story_by_slug', story_slug=story.slug))

    if not current_user.has_enough_points(required_points):
        flash('Not enough points to unlock this story.', 'error')
        return redirect(url_for('main.story_by_slug', story_slug=story.slug))

    try:
        current_user.add_points(-required_points, 'unlock_premium_story', f'Unlocked story: {story.title}')
        unlock = UnlockedContent(user_id=current_user.id, story_id=story_id)
        db.session.add(unlock)
        db.session.commit()
        flash('Story unlocked successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error unlocking story. Please try again.', 'error')
    
    return redirect(url_for('main.story_by_slug', story_slug=story.slug))

@main.route('/novel/<int:novel_id>/unlock', methods=['POST'])
@login_required
def unlock_novel(novel_id):
    novel = Novel.query.get_or_404(novel_id)
    required_points = 250  # Define points cost for novel

    if novel.story.author == current_user:
        flash('You own this novel, no need to unlock!', 'info')
        return redirect(url_for('main.novel_detail_slug', novel_slug=novel.slug))

    already_unlocked = UnlockedContent.query.filter_by(user_id=current_user.id, novel_id=novel_id).first()
    if already_unlocked:
        flash('You have already unlocked this novel.', 'info')
        return redirect(url_for('main.novel_detail_slug', novel_slug=novel.slug))

    if not current_user.has_enough_points(required_points):
        flash('Not enough points to unlock this novel.', 'error')
        return redirect(url_for('main.novel_detail_slug', novel_slug=novel.slug))

    try:
        current_user.add_points(-required_points, 'unlock_premium_novel', f'Unlocked novel: {novel.title}')
        unlock = UnlockedContent(user_id=current_user.id, novel_id=novel_id)
        db.session.add(unlock)
        db.session.commit()
        flash('Novel unlocked successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error unlocking novel. Please try again.', 'error')
    
    return redirect(url_for('main.novel_detail_slug', novel_slug=novel.slug))

@main.route('/volume/<int:volume_id>/unlock', methods=['POST'])
@login_required
def unlock_volume(volume_id):
    volume = Volume.query.get_or_404(volume_id)
    required_points = 100  # Define points cost for volume

    if volume.novel.story.author == current_user:
        flash('You own this volume, no need to unlock!', 'info')
        return redirect(url_for('main.volume_detail_slug', novel_slug=volume.novel.slug, volume_slug=volume.slug))
    
    already_unlocked = UnlockedContent.query.filter_by(user_id=current_user.id, volume_id=volume_id).first()
    if already_unlocked:
        flash('You have already unlocked this volume.', 'info')
        return redirect(url_for('main.volume_detail_slug', novel_slug=volume.novel.slug, volume_slug=volume.slug))

    if not current_user.has_enough_points(required_points):
        flash('Not enough points to unlock this volume.', 'error')
        return redirect(url_for('main.volume_detail_slug', novel_slug=volume.novel.slug, volume_slug=volume.slug))

    try:
        current_user.add_points(-required_points, 'unlock_premium_volume', f'Unlocked volume: {volume.title}')
        unlock = UnlockedContent(user_id=current_user.id, volume_id=volume_id)
        db.session.add(unlock)
        db.session.commit()
        flash('Volume unlocked successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error unlocking volume. Please try again.', 'error')
    
    return redirect(url_for('main.volume_detail_slug', novel_slug=volume.novel.slug, volume_slug=volume.slug))

@main.route('/chapter/<int:chapter_id>/unlock', methods=['POST'])
@login_required
def unlock_chapter(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    required_points = 25  # Define points cost for chapter

    if chapter.novel.story.author == current_user:
        flash('You own this chapter, no need to unlock!', 'info')
        return redirect(url_for('main.chapter_view_slug', novel_slug=chapter.novel.slug, volume_slug=chapter.volume.slug if chapter.volume else 'null', chapter_slug=chapter.slug))

    already_unlocked = UnlockedContent.query.filter_by(user_id=current_user.id, chapter_id=chapter_id).first()
    if already_unlocked:
        flash('You have already unlocked this chapter.', 'info')
        return redirect(url_for('main.chapter_view_slug', novel_slug=chapter.novel.slug, volume_slug=chapter.volume.slug if chapter.volume else 'null', chapter_slug=chapter.slug))

    if not current_user.has_enough_points(required_points):
        flash('Not enough points to unlock this chapter.', 'error')
        return redirect(url_for('main.chapter_view_slug', novel_slug=chapter.novel.slug, volume_slug=chapter.volume.slug if chapter.volume else 'null', chapter_slug=chapter.slug))

    try:
        current_user.add_points(-required_points, 'unlock_premium_chapter', f'Unlocked chapter: {chapter.title}')
        unlock = UnlockedContent(user_id=current_user.id, chapter_id=chapter_id)
        db.session.add(unlock)
        db.session.commit()
        flash('Chapter unlocked successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error unlocking chapter. Please try again.', 'error')
    
    return redirect(url_for('main.chapter_view_slug', novel_slug=chapter.novel.slug, volume_slug=chapter.volume.slug if chapter.volume else 'null', chapter_slug=chapter.slug))

# API endpoint for incrementing views after 10s delay (non-quote only)
@main.route('/api/story/<int:story_id>/increment_view', methods=['POST'])
def increment_story_view(story_id):
    story = Story.query.get_or_404(story_id)
    if story.writing_type == 'quote':
        return jsonify({'success': False, 'error': 'Views not counted for quotes.'}), 400
    # Only increment if not author (or not logged in)
    if (not current_user.is_authenticated) or (current_user.is_authenticated and current_user.id != story.author_id):
        story.views = (story.views or 0) + 1
        db.session.commit()
        # Add to reading history (FIFO, max 20) only if logged in
        if current_user.is_authenticated:
            existing = ReadingHistory.query.filter_by(user_id=current_user.id, story_id=story.id).first()
            if existing:
                existing.timestamp = datetime.utcnow()
            else:
                db.session.add(ReadingHistory(user_id=current_user.id, story_id=story.id))
            db.session.commit()
            # Keep only 20 most recent
            history = ReadingHistory.query.filter_by(user_id=current_user.id).order_by(ReadingHistory.timestamp.desc()).all()
            if len(history) > 20:
                for h in history[20:]:
                    db.session.delete(h)
                db.session.commit()
        return jsonify({'success': True, 'views': story.views})
    return jsonify({'success': False, 'error': 'Not allowed.'}), 403

# Legal pages routes
@main.route('/privacy')
def privacy():
    """Privacy Policy page"""
    return render_template('privacy.html', title='Privacy Policy')

@main.route('/terms')
def terms():
    """Terms of Service page"""
    return render_template('terms.html', title='Terms of Service')

@main.route('/contact')
def contact():
    """Contact page"""
    return render_template('contact.html', title='Contact Us')

@main.route('/story/<story_slug>/unlock', methods=['POST'])
@login_required
def unlock_story_by_slug(story_slug):
    story = Story.query.filter_by(slug=story_slug).first_or_404()
    required_points = 50  # Define points cost for story

    if story.author == current_user:
        flash('You own this story, no need to unlock!', 'info')
        return redirect(url_for('main.story_by_slug', story_slug=story_slug))
    
    already_unlocked = UnlockedContent.query.filter_by(user_id=current_user.id, story_id=story.id).first()
    if already_unlocked:
        flash('You have already unlocked this story.', 'info')
        return redirect(url_for('main.story_by_slug', story_slug=story_slug))

    if not current_user.has_enough_points(required_points):
        flash('Not enough points to unlock this story.', 'error')
        return redirect(url_for('main.story_by_slug', story_slug=story_slug))

    try:
        current_user.add_points(-required_points, 'unlock_premium_story', f'Unlocked story: {story.title}')
        unlock = UnlockedContent(user_id=current_user.id, story_id=story.id)
        db.session.add(unlock)
        db.session.commit()
        flash('Story unlocked successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error unlocking story. Please try again.', 'error')
    
    return redirect(url_for('main.story_by_slug', story_slug=story_slug))

def remove_expired_features():
    """Remove stories that have been featured for more than 24 hours"""
    try:
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        expired_stories = Story.query.filter(
            Story.is_featured == True,
            Story.featured_at < twenty_four_hours_ago
        ).all()
        
        for story in expired_stories:
            story.is_featured = False
            story.featured_at = None
        
        if expired_stories:
            db.session.commit()
            print(f"Removed {len(expired_stories)} expired featured stories")
        
        return len(expired_stories)
    except Exception as e:
        db.session.rollback()
        print(f"Error removing expired features: {e}")
        return 0

@main.route('/admin/remove-expired-features', methods=['POST'])
@login_required
def admin_remove_expired_features():
    """Admin route to manually trigger expired feature removal"""
    if not current_user.username == 'admin':  # Simple admin check
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    removed_count = remove_expired_features()
    flash(f'Removed {removed_count} expired featured stories', 'success')
    return redirect(url_for('main.index'))

@main.route('/api/tour/progress', methods=['POST'])
@login_required
def update_tour_progress():
    """API endpoint to update user's tour progress"""
    try:
        data = request.get_json()
        progress = data.get('progress', {})
        completed = data.get('completed', False)
        
        current_user.tour_progress = progress
        current_user.tour_completed = completed
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@main.route('/test-tour')
@login_required
def test_tour():
    """Test page for the tour system"""
    return render_template('test_tour.html', title='Tour Test')

# Predefined interests list
PREDEFINED_INTERESTS = [
    'romance', 'mystery', 'sci-fi', 'fantasy', 'poetry', 'quotes',
    'motivational', 'life', 'thriller', 'short-stories', 'fanfiction'
]

@main.route('/api/interests/list')
@login_required
def get_interests_list():
    return jsonify({'interests': PREDEFINED_INTERESTS})

@main.route('/api/interests/save', methods=['POST'])
@login_required
def save_user_interests():
    data = request.get_json()
    interests = data.get('interests', [])
    if not isinstance(interests, list):
        return jsonify({'success': False, 'error': 'Invalid interests format'}), 400
    current_user.interests = ','.join([i.strip() for i in interests if i.strip()])
    current_user.has_set_interests = True
    db.session.commit()
    return jsonify({'success': True})

@main.route('/settings/interests', methods=['POST'])
@login_required
def save_interests():
    # Always normalize tags
    selected = [t.strip().lower() for t in current_user.interests.split(',') if t.strip()]
    # Remove interest if requested
    remove = request.form.get('remove_interest')
    if remove:
        remove = remove.strip().lower()
        selected = [t for t in selected if t != remove]
        current_user.interests = ','.join(selected) if selected else ''
        db.session.commit()
        return redirect(url_for('main.settings', interests_message='Interest removed.'))
    # Add new interests
    custom = request.form.get('custom_interests', '')
    custom_tags = [t.strip().lower().replace('#', '') for t in custom.split(',') if t.strip()]
    all_tags = list(dict.fromkeys([t for t in selected + custom_tags if t]))
    current_user.interests = ','.join(all_tags) if all_tags else ''
    current_user.has_set_interests = True
    db.session.commit()
    return redirect(url_for('main.settings', interests_message='Your interests have been updated!'))

@main.route('/novel/<novel_slug>/comment', methods=['POST'])
def novel_comment(novel_slug):
    novel = Novel.query.filter_by(slug=novel_slug).first_or_404()
    story = novel.story
    form = CommentForm()
    
    if not current_user.is_authenticated:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Please log in to comment.'}), 401
        flash('Please log in to comment.', 'info')
        return redirect(url_for('auth.login', next=url_for('main.novel_detail_slug', novel_slug=novel_slug)))
    
    if form.validate_on_submit():
        try:
            parent_id = request.form.get('parent_id')
            parent_comment = None
            if parent_id:
                parent_comment = Comment.query.get(parent_id)
                if not parent_comment or parent_comment.story_id != story.id:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'success': False, 'error': 'Invalid parent comment.'}), 400
                    flash('Invalid parent comment.', 'danger')
                    return redirect(url_for('main.novel_detail_slug', novel_slug=novel_slug))
            
            comment = Comment(
                content=form.content.data,
                author=current_user,
                story=story,
                parent=parent_comment
            )
            db.session.add(comment)
            
            # Award points logic
            points_earned = 0
            word_count = len(form.content.data.split())
            if word_count >= 20 and current_user.can_earn_comment_points():
                current_user.add_points(4, 'meaningful_comment', f'Comment on {story.title}')
                current_user.comment_points_count += 1
                points_earned = 4
            
            if word_count >= 10 and story.author.can_earn_comment_points():
                story.author.add_points(3, 'received_comment', f'Comment on {story.title}')
                story.author.comment_points_count += 1
            
            db.session.commit()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                response_data = {
                    'success': True,
                    'message': 'Comment posted successfully.'
                }
                if points_earned > 0:
                    response_data['points_earned'] = points_earned
                return jsonify(response_data)
            
            if points_earned > 0:
                flash(f'You earned {points_earned} points for your meaningful comment!', 'success')
            flash('Your comment has been added.', 'success')
            return redirect(url_for('main.novel_detail_slug', novel_slug=novel_slug))

        except Exception as e:
            db.session.rollback()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'An internal error occurred while posting the comment.'}), 500
            flash('Error processing comment.', 'error')
            return redirect(url_for('main.novel_detail_slug', novel_slug=novel_slug))
    
    # Handle form validation failure
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': False, 'error': 'Invalid data provided.', 'errors': form.errors}), 400
    
    flash('Could not post comment. Please check your input.', 'danger')
    return redirect(url_for('main.novel_detail_slug', novel_slug=novel_slug))

@main.route('/faq')
def faq():
    return render_template('faq.html', title='FAQ')

@main.route('/about')
def about():
    return render_template('about.html', title='About')
