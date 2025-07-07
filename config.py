# config.py
import os

# Get the absolute path of the directory where this file is located
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """
    Configuration class for the Flask app.
    Uses environment variables for production settings.
    """
    # Use the DATABASE_URL from the environment if it's available (for Render).
    # Otherwise, fall back to the local SQLite database for development.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'app.db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
