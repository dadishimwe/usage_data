# config.py
import os

# Get the absolute path of the directory where this file is located
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """
    Configuration class for the Flask app.
    Sets up the database URI and other configurations.
    """
    # Define the database URI. It points to a file named app.db
    # in an 'instance' folder at the same level as your app.py.
    # Flask will automatically create the 'instance' folder.
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'instance', 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
