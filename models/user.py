# This file has been moved to the models directory

from models import db

# Define the User model
class User(db.Model):
    # Define the columns for the User table
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    # Define the string representation of the User object
    def __repr__(self):
        return f'<User {self.username}>'
