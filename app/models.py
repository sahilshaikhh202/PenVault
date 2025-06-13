from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from slugify import slugify

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

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    profile_picture = db.Column(db.String(128), default='default.jpg')
    bio = db.Column(db.Text)
    theme = db.Column(db.String(10), default='light')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_premium = db.Column(db.Boolean, default=False)
    hide_saved_list = db.Column(db.Boolean, default=False)
    hide_recent_reads = db.Column(db.Boolean, default=False)
    
    # Relationships
    stories = db.relationship('Story', backref='author', lazy='dynamic')
    followers = db.relationship('Follow', foreign_keys='Follow.followed_id', backref='followed', lazy='dynamic')
    following = db.relationship('Follow', foreign_keys='Follow.follower_id', backref='follower', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    saved_stories = db.relationship('Story', secondary='reading_list', backref=db.backref('saved_by', lazy='dynamic'))
    reading_history = db.relationship('ReadingHistory', backref='reader', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
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

class Story(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Relationships
    volumes = db.relationship('Volume', backref='novel', lazy='dynamic', cascade="all, delete-orphan")
    chapters = db.relationship('Chapter', backref='novel', lazy='dynamic', cascade="all, delete-orphan")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.slug:
            self.slug = slugify(self.title)

class Volume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    novel_id = db.Column(db.Integer, db.ForeignKey('novel.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.Text)
    order = db.Column(db.Integer, default=1)
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

    __table_args__ = (db.UniqueConstraint('volume_id', 'slug', name='uq_chapter_volume_slug'),)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.slug:
            self.slug = slugify(self.title)

class ReadingHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    story_id = db.Column(db.Integer, db.ForeignKey('story.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    story = db.relationship('Story')