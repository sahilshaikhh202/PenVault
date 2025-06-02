# Writer's Platform

A modern web application for writers to share their stories, connect with readers, and build their audience. Built with Flask, this platform combines features from Instagram and Webnovel to create a unique writing and reading experience.

## Features

- **User Profiles**: Registration, login, and profile customization
- **Content Creation**: Rich text editor with formatting options and media support
- **Story Publishing**: Categories, tags, and privacy controls
- **Social Features**: Follow/unfollow, notifications, and direct messaging
- **Story Discovery**: Algorithm-driven feed and search functionality
- **Monetization**: Premium content and tip jar features
- **Reader Engagement**: Comments, polls, and reading lists
- **Analytics**: Track views, engagement, and reader demographics
- **Moderation**: Content reporting and user blocking
- **Mobile Responsive**: Fully functional on all devices

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment (recommended)
- PostgreSQL (for production)
- Redis (for caching and rate limiting)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/writers-platform.git
cd writers-platform
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
```
Edit `.env` with your configuration:
```
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:password@localhost/writers_platform
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

5. Initialize the database:
```bash
flask db upgrade
```

6. Create upload directories:
```bash
mkdir -p app/static/uploads
mkdir -p app/static/uploads/profiles
mkdir -p app/static/uploads/stories
```

## Running the Application

### Development
```bash
flask run
```

### Production
```bash
gunicorn -w 4 -b 0.0.0.0:8000 run:app
```

## Project Structure

```
writers-platform/
├── app/
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── uploads/
│   ├── templates/
│   │   ├── auth/
│   │   ├── story/
│   │   └── ...
│   ├── __init__.py
│   ├── models.py
│   ├── routes.py
│   └── forms.py
├── migrations/
├── tests/
├── config.py
├── requirements.txt
└── run.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Flask and its extensions
- Bootstrap for the frontend framework
- Quill.js for the rich text editor
- Font Awesome for icons 