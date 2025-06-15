from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField, 
    PasswordField, 
    BooleanField, 
    SubmitField, 
    TextAreaField, 
    SelectField, 
    IntegerField,
    SearchField
)
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional
from app.models import User

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class ProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    bio = TextAreaField('Bio', validators=[Length(max=500)])
    profile_picture = FileField('Profile Picture')
    submit = SubmitField('Update Profile')

class StoryForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    summary = TextAreaField('Summary', validators=[Length(max=500)])
    content = TextAreaField('Content', validators=[DataRequired()])
    cover_image = FileField('Cover Image')
    is_premium = BooleanField('Premium Content')
    writing_type = SelectField('Writing Type', choices=[
        ('story', 'Story'),
        ('poetry', 'Poetry'),
        ('quote', 'Quote / One-liner'),
        ('essay', 'Essay / Article'),
        ('webnovel', 'Webnovel'),
        ('other', 'Other')
    ], default='story', validators=[DataRequired()])
    tags = StringField('Tags (comma-separated)', validators=[Optional()])
    submit = SubmitField('Publish')
    save_draft = SubmitField('Save as Draft')

class PoetryForm(StoryForm):
    title = StringField('Poem Title', validators=[DataRequired(), Length(max=200)])
    content = TextAreaField('Poem', validators=[
        DataRequired(),
        Length(max=5000, message="Poem must be 5000 characters or less")
    ])
    form_type = SelectField('Poetry Form', choices=[
        ('free_verse', 'Free Verse'),
        ('haiku', 'Haiku'),
        ('sonnet', 'Sonnet'),
        ('limerick', 'Limerick'),
        ('other', 'Other')
    ])
    notes = TextAreaField('Author Notes', validators=[Optional(), Length(max=500)])
    tags = StringField('Tags (comma separated)', validators=[Optional()])
    submit = SubmitField('Publish Poem')
    save_draft = SubmitField('Save as Draft')

    def validate_content(self, field):
        if field.data.count('\n') < 2:
            raise ValidationError('Poetry must contain at least 2 lines')

class QuoteForm(FlaskForm):
    title = StringField('Title (Optional)', validators=[Optional(), Length(max=200)])
    content = StringField('Quote', validators=[
        DataRequired(),
        Length(max=300, message="Quote must be 300 characters or less")
    ])
    author = StringField('Original Author', validators=[Optional(), Length(max=100)])
    source = StringField('Source/Context', validators=[Optional(), Length(max=200)])
    category = SelectField('Category', choices=[
        ('inspiration', 'Inspirational'),
        ('wisdom', 'Wisdom'),
        ('humor', 'Humor'),
        ('philosophy', 'Philosophy'),
        ('other', 'Other')
    ])
    tags = StringField('Tags (comma separated)', validators=[Optional()])
    submit = SubmitField('Publish Quote')
    save_draft = SubmitField('Save as Draft')

class EssayForm(StoryForm):
    title = StringField('Essay Title', validators=[DataRequired(), Length(max=200)])
    subtitle = StringField('Subtitle', validators=[Optional(), Length(max=200)])
    content = TextAreaField('Content', validators=[
        DataRequired(),
        Length(min=500, message="Essays should be at least 500 characters")
    ])
    category = SelectField('Category', choices=[
        ('academic', 'Academic'),
        ('opinion', 'Opinion'),
        ('review', 'Review'),
        ('analysis', 'Analysis'),
        ('other', 'Other')
    ])
    references = TextAreaField('References', validators=[Optional()])
    tags = StringField('Tags (comma separated)', validators=[Optional()])
    submit = SubmitField('Publish Essay')
    save_draft = SubmitField('Save as Draft')

class NovelForm(FlaskForm):
    title = StringField('Novel Title', validators=[DataRequired(), Length(max=200)])
    summary = TextAreaField('Summary', validators=[
        DataRequired(),
        Length(min=100, max=1000)
    ])
    genre = SelectField('Genre', choices=[
        ('fantasy', 'Fantasy'),
        ('scifi', 'Science Fiction'),
        ('romance', 'Romance'),
        ('mystery', 'Mystery'),
        ('other', 'Other')
    ])
    status = SelectField('Status', choices=[
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('hiatus', 'On Hiatus')
    ])
    is_mature = BooleanField('Mature Content')
    is_premium = BooleanField('Premium Content (All volumes and chapters will be premium)')
    cover_image = FileField('Cover Image', validators=[
        Optional(),
        FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')
    ])
    submit = SubmitField('Create Novel')

class VolumeForm(FlaskForm):
    title = StringField('Volume Title', validators=[DataRequired(), Length(max=200)])
    summary = TextAreaField('Summary', validators=[Length(max=1000)])
    order = StringField('Order', validators=[DataRequired()])
    is_premium = BooleanField('Premium Content (All chapters in this volume will be premium)')
    submit = SubmitField('Add Volume')

class ChapterForm(FlaskForm):
    title = StringField('Chapter Title', validators=[DataRequired(), Length(max=200)])
    content = TextAreaField('Content', validators=[
        DataRequired(),
        Length(min=500, message="Chapter should be at least 500 characters")
    ])
    order = IntegerField('Chapter Number', validators=[DataRequired()])
    author_notes = TextAreaField('Author Notes', validators=[Optional(), Length(max=500)])
    is_draft = BooleanField('Save as Draft')
    is_premium = BooleanField('Premium Content (Only this chapter will be premium)')
    submit = SubmitField('Add Chapter')

class OtherWritingForm(StoryForm):
    custom_type = StringField('Custom Type', validators=[DataRequired(), Length(max=50)])
    tags = StringField('Tags (comma separated)', validators=[Optional()])
    pass

class CommentForm(FlaskForm):
    content = TextAreaField('Comment', validators=[DataRequired(), Length(max=1000)])
    submit = SubmitField('Post Comment')

class EditCommentForm(FlaskForm):
    content = TextAreaField('Edit Comment', validators=[DataRequired(), Length(max=1000)])
    submit = SubmitField('Update Comment')

class SearchForm(FlaskForm):
    query = StringField('Search', validators=[DataRequired()])
    submit = SubmitField('Search')
