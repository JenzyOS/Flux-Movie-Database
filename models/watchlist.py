from models import db

# Define the Watchlist model
class Watchlist(db.Model):
    # Define the columns for the Watchlist table
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    imdb_id = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    year = db.Column(db.String(10), nullable=True)
    genre = db.Column(db.String(100), nullable=True)
    director = db.Column(db.String(100), nullable=True)
    actors = db.Column(db.String(500), nullable=True)
    plot = db.Column(db.Text, nullable=True)
    poster = db.Column(db.String(300), nullable=True)
    imdb_rating = db.Column(db.String(10), nullable=True)

    # Define the string representation of the Watchlist object
    def __repr__(self):
        return f'<Watchlist {self.title}>'
