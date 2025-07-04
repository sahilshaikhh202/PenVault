from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from slugify import slugify
from sqlalchemy.ext.hybrid import hybrid_property

# Define association table for Story and Tag relationship
story_tags = db.Table('story_tags',
    db.Column('story_id', db.Integer, db.ForeignKey('story.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

# Define association table for User's reading list
reading_list = db.Table('reading_list',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('story_id', db.Integer, db.ForeignKey('story.id'), primary_key=True)
)

# Add story_likes table
story_likes = db.Table('story_likes',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('story_id', db.Integer, db.ForeignKey('story.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class PointsTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    points = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.Column(db.String(200))  # Additional details about the transaction

    user = db.relationship('User', backref='point_transactions')

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(512))
    profile_picture = db.Column(db.String(128), default='default.jpg')
    bio = db.Column(db.Text)
    theme = db.Column(db.String(10), default='light')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_premium = db.Column(db.Boolean, default=False)
    hide_saved_list = db.Column(db.Boolean, default=False)
    hide_recent_reads = db.Column(db.Boolean, default=False)
    points = db.Column(db.Integer, default=0, nullable=False)  # Modified to ensure non-null
    last_daily_login = db.Column(db.Date)
    last_post_points = db.Column(db.Date)
    last_comment_points = db.Column(db.Date)
    last_share_points = db.Column(db.Date)  # Track when share points were last reset
    comment_points_count = db.Column(db.Integer, default=0)
    share_points_count = db.Column(db.Integer, default=0)
    referral_count = db.Column(db.Integer, default=0)
    highest_pulse_tier = db.Column(db.String(20))
    
    # Tour tracking
    tour_completed = db.Column(db.Boolean, default=False)
    tour_progress = db.Column(db.JSON, default=dict)  # Store tour step progress
    
    # Referral system fields
    referral_code = db.Column(db.String(20), unique=True)  # Format: username25
    referred_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    monthly_referral_count = db.Column(db.Integer, default=0)
    last_referral_reset = db.Column(db.Date)  # Track when monthly count was last reset
    
    # Account management fields
    is_disabled = db.Column(db.Boolean, default=False)
    deletion_requested_at = db.Column(db.DateTime, nullable=True)
    
    # Interests feature
    has_set_interests = db.Column(db.Boolean, default=False)
    interests = db.Column(db.String(512), default='')  # Comma-separated tags
    
    # Add relationships
    stories = db.relationship('Story', backref='author', lazy='dynamic')
    following = db.relationship('Follow', foreign_keys='Follow.follower_id', backref='follower', lazy='dynamic')
    followers = db.relationship('Follow', foreign_keys='Follow.followed_id', backref='followed', lazy='dynamic')
    reading_history = db.relationship('ReadingHistory', backref='user', lazy='dynamic')
    saved_stories = db.relationship('Story', secondary='reading_list', backref='saved_by', lazy='dynamic')
    
    # Referral relationships
    referrals = db.relationship('User', backref=db.backref('referrer', remote_side=[id]))
    
    # Account actions audit
    account_actions = db.relationship('AccountAction', backref='user', lazy='dynamic')

    chapter_reading_history = db.relationship('ChapterReadingHistory', backref='user', lazy='dynamic')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.points is None:
            self.points = 0
        if not self.referral_code:
            self.referral_code = f"{self.username}25" if self.username else None
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_account_active(self):
        """Check if account is active (not disabled and not scheduled for deletion)"""
        if self.is_disabled:
            return False
        if self.deletion_requested_at:
            # Check if 20 days have passed since deletion was requested
            days_since_deletion_request = (datetime.utcnow() - self.deletion_requested_at).days
            if days_since_deletion_request >= 20:
                return False
        return True
    
    def is_scheduled_for_deletion(self):
        """Check if account is scheduled for deletion but still within 20-day period"""
        return self.deletion_requested_at is not None and (datetime.utcnow() - self.deletion_requested_at).days < 20
    
    def days_until_deletion(self):
        """Get number of days until account is permanently deleted"""
        if not self.deletion_requested_at:
            return None
        days_since_request = (datetime.utcnow() - self.deletion_requested_at).days
        return max(0, 20 - days_since_request)
    
    def disable_account(self, reason="User requested"):
        """Disable the user account"""
        self.is_disabled = True
        action = AccountAction(
            user_id=self.id,
            action_type='disable',
            details=reason
        )
        db.session.add(action)
        db.session.commit()
    
    def enable_account(self):
        """Re-enable the user account"""
        self.is_disabled = False
        action = AccountAction(
            user_id=self.id,
            action_type='enable',
            details='Account re-enabled'
        )
        db.session.add(action)
        db.session.commit()
    
    def request_deletion(self, reason="User requested"):
        """Request account deletion (20-day waiting period)"""
        self.deletion_requested_at = datetime.utcnow()
        action = AccountAction(
            user_id=self.id,
            action_type='deletion_requested',
            details=reason
        )
        db.session.add(action)
        db.session.commit()
    
    def cancel_deletion(self):
        """Cancel account deletion request"""
        self.deletion_requested_at = None
        action = AccountAction(
            user_id=self.id,
            action_type='deletion_cancelled',
            details='User cancelled deletion request'
        )
        db.session.add(action)
        db.session.commit()
    
    def delete_account_permanently(self):
        """Permanently delete the account and all related data"""
        # This method should be called by a scheduled task after 20 days
        action = AccountAction(
            user_id=self.id,
            action_type='account_deleted',
            details='Account permanently deleted after 20-day waiting period'
        )
        db.session.add(action)
        
        # Delete all related data
        # Stories and comments will be deleted via cascade
        # Reading history, follows, etc. will be deleted via cascade
        db.session.delete(self)
        db.session.commit()
        
    def is_following(self, user):
        """Check if this user is following the given user"""
        if user.id is None:
            return False
        return self.following.filter_by(followed_id=user.id).first() is not None
        
    def follow(self, user):
        """Follow another user if not already following"""
        if not self.is_following(user) and self != user:
            follow = Follow(follower_id=self.id, followed_id=user.id)
            db.session.add(follow)
            
    def unfollow(self, user):
        """Unfollow a user"""
        follow = self.following.filter_by(followed_id=user.id).first()
        if follow:
            db.session.delete(follow)

    def add_points(self, points, action, details=None):
        """Add points to user and create transaction record"""
        if self.points is None:
            self.points = 0
        self.points += points
        transaction = PointsTransaction(
            user_id=self.id,
            action=action,
            points=points,
            details=details
        )
        db.session.add(transaction)
        db.session.commit()

    def can_earn_daily_login_points(self):
        """Check if user can earn daily login points"""
        today = datetime.utcnow().date()
        return not self.last_daily_login or self.last_daily_login < today

    def can_earn_post_points(self):
        """Check if user can earn post points"""
        today = datetime.utcnow().date()
        return not self.last_post_points or self.last_post_points < today

    def can_earn_comment_points(self):
        """Check if user can earn comment points"""
        today = datetime.utcnow().date()
        if not self.last_comment_points or self.last_comment_points < today:
            self.comment_points_count = 0
            self.last_comment_points = today
            return True
        return self.comment_points_count < 10

    def can_earn_share_points(self):
        """Check if user can earn share points"""
        today = datetime.utcnow().date()
        if not self.last_share_points or self.last_share_points < today:
            self.share_points_count = 0
            self.last_share_points = today
            return True
        return self.share_points_count < 2

    def can_earn_referral_points(self):
        """Check if user can earn referral points (max 3 per month)"""
        today = datetime.utcnow().date()
        # Reset monthly count if it's a new month
        if not self.last_referral_reset or self.last_referral_reset.month != today.month or self.last_referral_reset.year != today.year:
            self.monthly_referral_count = 0
            self.last_referral_reset = today
        return self.monthly_referral_count < 3

    def process_referral(self, referred_user):
        """Process a successful referral"""
        if self.can_earn_referral_points():
            self.add_points(25, 'referral', f'Referred {referred_user.username}')
            self.referral_count += 1
            self.monthly_referral_count += 1
            self.last_referral_reset = datetime.utcnow().date()
            return True
        return False

    def check_pulse_tier_bonus(self, current_tier):
        """Check and award pulse tier bonus points"""
        if not self.highest_pulse_tier or self.highest_pulse_tier < current_tier:
            bonus_points = {
                'spark': 25,
                'flame': 50,
                'glow': 75,
                'shine': 100,
                'pulse': 150,
                'surge': 200,
                'nova': 300
            }
            if current_tier in bonus_points:
                self.add_points(bonus_points[current_tier], 'pulse_tier_bonus', f'Reached {current_tier} tier')
                self.highest_pulse_tier = current_tier
                db.session.commit()

    def has_enough_points(self, required_points):
        """Check if user has enough points for redemption"""
        return self.points >= required_points

class Story(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text)
    cover_image = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_published = db.Column(db.Boolean, default=False)
    is_premium = db.Column(db.Boolean, default=False)
    views = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    writing_type = db.Column(db.String(50), nullable=False, server_default='story')
    is_featured = db.Column(db.Boolean, default=False, nullable=False)
    featured_at = db.Column(db.DateTime, nullable=True)  # Track when story was featured
    # Add likes relationship
    liked_by = db.relationship('User', secondary='story_likes',
                             backref=db.backref('liked_stories', lazy='dynamic'),
                             lazy='dynamic')
    
    # Poetry specific fields
    form_type = db.Column(db.String(50))  # e.g., haiku, sonnet, etc.
    notes = db.Column(db.Text)

    # Quote specific fields
    quote_author = db.Column(db.String(100))
    quote_source = db.Column(db.String(200))
    quote_category = db.Column(db.String(50))

    # Essay specific fields
    subtitle = db.Column(db.String(200))
    essay_category = db.Column(db.String(50))
    references = db.Column(db.Text)

    # Other writing type
    custom_type = db.Column(db.String(50))
    
    # Foreign Keys
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    comments = db.relationship('Comment', backref='story', lazy='dynamic', cascade="all, delete-orphan")
    tags = db.relationship('Tag', secondary='story_tags', backref='stories')
    # Webnovel relationship
    novel = db.relationship('Novel', backref='story', uselist=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.slug:
            self.slug = slugify(self.title)

    def update_slug(self):
        """Update the slug when the title changes"""
        self.slug = slugify(self.title)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Keys
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    story_id = db.Column(db.Integer, db.ForeignKey('story.id', ondelete="CASCADE"), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'))
    
    # Relationships
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')
    author = db.relationship('User', backref='comments')

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

class Follow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Webnovel Models
class Novel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey('story.id'), nullable=False, unique=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    summary = db.Column(db.Text)
    cover_image = db.Column(db.String(200))
    genre = db.Column(db.String(100))  # Add genre field
    status = db.Column(db.String(50), default='ongoing')  # Add status field
    is_mature = db.Column(db.Boolean, default=False)  # Add mature content flag
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_premium = db.Column(db.Boolean, default=False)  # If true, all volumes and chapters are premium
    # Relationships
    volumes = db.relationship('Volume', backref='novel', lazy='dynamic', cascade="all, delete-orphan")
    chapters = db.relationship('Chapter', backref='novel', lazy='dynamic', cascade="all, delete-orphan")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.slug:
            self.slug = slugify(self.title)

    def update_slug(self):
        """Update the slug when the title changes"""
        self.slug = slugify(self.title)
        # Update volume and chapter slugs if they contain the novel title
        for volume in self.volumes:
            if volume.title.startswith(self.title):
                volume.slug = slugify(volume.title)
        for chapter in self.chapters:
            if chapter.title.startswith(self.title):
                chapter.slug = slugify(chapter.title)

    @hybrid_property
    def avg_rating(self):
        if not self.ratings or len(self.ratings) == 0:
            return 0
        return sum(r.rating for r in self.ratings) / len(self.ratings)

class Volume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    novel_id = db.Column(db.Integer, db.ForeignKey('novel.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.Text)
    order = db.Column(db.Integer, default=1)
    is_premium = db.Column(db.Boolean, default=False)  # If true, all chapters in this volume are premium
    # Relationships
    chapters = db.relationship('Chapter', backref='volume', lazy='dynamic', cascade="all, delete-orphan")

    __table_args__ = (db.UniqueConstraint('novel_id', 'slug', name='uq_volume_novel_slug'),)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.slug:
            self.slug = slugify(self.title)

class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    novel_id = db.Column(db.Integer, db.ForeignKey('novel.id'), nullable=False)
    volume_id = db.Column(db.Integer, db.ForeignKey('volume.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    order = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_premium = db.Column(db.Boolean, default=False)  # Individual chapter premium status
    author_notes = db.Column(db.Text)
    is_draft = db.Column(db.Boolean, default=False)

    __table_args__ = (db.UniqueConstraint('volume_id', 'slug', name='uq_chapter_volume_slug'),)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.slug:
            self.slug = slugify(self.title)

    @property
    def is_premium_content(self):
        """Check if this chapter is premium based on novel, volume, or chapter settings"""
        if self.novel.is_premium:
            return True
        if self.volume and self.volume.is_premium:
            return True
        return self.is_premium

class ReadingHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    story_id = db.Column(db.Integer, db.ForeignKey('story.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    story = db.relationship('Story')

class ChapterReadingHistory(db.Model):
    """Track which chapters users have read for webnovels"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    novel_id = db.Column(db.Integer, db.ForeignKey('novel.id'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    novel = db.relationship('Novel')
    chapter = db.relationship('Chapter')
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'novel_id', name='uq_user_novel_reading'),
    )

class UnlockedContent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    story_id = db.Column(db.Integer, db.ForeignKey('story.id'), nullable=True)
    novel_id = db.Column(db.Integer, db.ForeignKey('novel.id'), nullable=True)
    volume_id = db.Column(db.Integer, db.ForeignKey('volume.id'), nullable=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=True)
    unlocked_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Add relationship to User
    user = db.relationship('User', backref='unlocked_content')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'story_id', name='uq_user_story_unlock'),
        db.UniqueConstraint('user_id', 'novel_id', name='uq_user_novel_unlock'),
        db.UniqueConstraint('user_id', 'volume_id', name='uq_user_volume_unlock'),
        db.UniqueConstraint('user_id', 'chapter_id', name='uq_user_chapter_unlock'),
    )

# --- NovelRating model for star ratings ---
class NovelRating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    novel_id = db.Column(db.Integer, db.ForeignKey('novel.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('novel_id', 'user_id', name='uq_novel_user_rating'),)

    user = db.relationship('User', backref='novel_ratings')
    novel = db.relationship('Novel', backref='ratings')

class AccountAction(db.Model):
    """Audit log for account management actions"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)  # disable, enable, deletion_requested, deletion_cancelled, account_deleted
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)