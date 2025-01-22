from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import yaml
import requests
import json
import os
import random
from werkzeug.utils import secure_filename
from models import db
from models.user import User
from models.favorite import Favorite
from models.watched import Watched
from models.watchlist import Watchlist
from models.rating import Rating

app = Flask(__name__, static_folder='frontend')
app.secret_key = "your_secret_key"
OMDB_API_KEY = "f91c77a2"
UPLOAD_FOLDER = 'frontend/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Load users from YAML file
def load_users():
    with open("users.yaml", "r") as file:
        data = yaml.safe_load(file)
        return data['users']

# Save users to YAML file
def save_users(users):
    with open("users.yaml", "w") as file:
        yaml.dump({"users": users}, file)

# Load profile images from YAML file
def load_profile_images():
    if not os.path.exists("profile_pics.yaml"):
        return {}
    with open("profile_pics.yaml", "r") as file:
        data = yaml.safe_load(file)
        return data.get('profile_pics', {})

# Save profile images to YAML file
def save_profile_images(profile_images):
    with open("profile_pics.yaml", "w") as file:
        yaml.dump({"profile_pics": profile_images}, file)

# Register a new user
def register_user(username, email, password):
    users = load_users()
    for user in users:
        if user['username'] == username or user['email'] == email:
            return False
    new_user = {"username": username, "email": email, "password": password}
    users.append(new_user)
    save_users(users)
    return True

# Login a user
def login_user(username, password):
    users = load_users()
    for user in users:
        if user['username'] == username and user['password'] == password:
            return True
    return False

# Update user information
def update_user_info(username, new_username=None, new_password=None, profile_image_path=None):
    users = load_users()
    for user in users:
        if user['username'] == username:
            if new_username:
                user['username'] = new_username
            if new_password:
                user['password'] = new_password
            if profile_image_path:
                user['profile_image'] = profile_image_path
            save_users(users)
            return True
    return False

# Get random movies from a list
def get_random_movies():
    try:
        with open("movies.txt", "r") as file:
            movie_titles = [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print("movies.txt file not found! Please create the file and add movie titles.")
        return []
    random_movies = random.sample(movie_titles, min(len(movie_titles), 30))
    recommended_movies = []
    for title in random_movies:
        response = requests.get(f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&t={title}")
        if response.status_code == 200:
            movie = response.json()
            if not movie.get("Title") or not movie.get("Poster"):
                continue
            recommended_movies.append({
                "title": movie["Title"],
                "poster": movie["Poster"]
            })
    while len(recommended_movies) < 30:
        for title in random_movies:
            response = requests.get(f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&t={title}")
            if response.status_code == 200:
                movie = response.json()
                if not movie.get("Title") or not movie.get("Poster"):
                    continue
                recommended_movies.append({
                    "title": movie["Title"],
                    "poster": movie["Poster"]
                })
            if len(recommended_movies) == 30:
                break
    return recommended_movies

# Check if the file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route to redirect to the login page
@app.route('/')
def home():
    return redirect(url_for('login'))

# Route to handle user login
@app.route('/login', methods=['GET', 'POST'])
def login():
    error_message = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if login_user(username, password):
            session['user'] = username
            return redirect(url_for('dashboard'))
        else:
            error_message = "Login failed! Incorrect username or password."
    return render_template("login.html", error_message=error_message)

# Route to handle user registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    error_message = None
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if register_user(username, email, password):
            return redirect(url_for('dashboard'))
        else:
            error_message = "Username or email already registered."
    return render_template("register.html", error_message=error_message)

# Route to display the dashboard
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('home'))
    recommended_movies = get_random_movies()
    return render_template("dashboard.html", recommended_movies=recommended_movies)

# Route to handle user logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# Route to display the user profile
@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect(url_for('home'))
    username = session['user']
    users = load_users()
    profile_images = load_profile_images()
    user_info = next((user for user in users if user['username'] == username), None)
    if user_info:
        return render_template(
            'profile.html',
            user_username=user_info['username'],
            user_email=user_info['email'],
            user_profile_image=profile_images.get(username, 'default_image.png')
        )
    return "User information not found!"

# Route to update user profile information
@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user' not in session:
        return redirect(url_for('home'))
    username = session['user']
    current_password = request.form['current-password']
    new_password = request.form['new-password']
    new_username = request.form['new-username']
    profile_image = request.files['profile-image']
    if profile_image and allowed_file(profile_image.filename):
        filename = secure_filename(profile_image.filename)
        profile_image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        profile_image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    else:
        profile_image_path = None
    if update_user_info(username, new_username=new_username, new_password=new_password, profile_image_path=profile_image_path):
        if new_username:
            session['user'] = new_username
        if profile_image_path:
            profile_images = load_profile_images()
            profile_images[new_username or username] = profile_image_path
            save_profile_images(profile_images)
        return redirect(url_for('profile'))
    else:
        return "User information could not be updated!"

# Route to update user profile image
@app.route('/update_profile_image', methods=['POST'])
def update_profile_image():
    if 'user' not in session:
        return redirect(url_for('home'))
    username = session['user']
    profile_image = request.files['profile-image']
    if profile_image and allowed_file(profile_image.filename):
        filename = secure_filename(profile_image.filename)
        profile_image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        profile_image.save(profile_image_path)
        profile_images = load_profile_images()
        profile_images[username] = profile_image_path
        save_profile_images(profile_images)
        return redirect(url_for('profile'))
    else:
        return "Invalid file format!"

# Route to search for movies and display results
@app.route('/movies', methods=['GET', 'POST'])
def movies():
    if 'user' not in session:
        return redirect(url_for('home'))
    if request.method == 'GET':
        imdb_id = request.args.get('imdb_id')
        if imdb_id:
            response = requests.get(f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&i={imdb_id}")
            if response.status_code == 200:
                return jsonify(response.json())
            else:
                return jsonify({"error": "Movie information could not be retrieved."}), 500
    movie_data = []
    error_message = None
    if request.method == 'POST':
        movie_name = request.form['movie_name']
        search_response = requests.get(f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&s={movie_name}")
        if search_response.status_code == 200:
            search_results = search_response.json()
            if search_results.get('Response') == 'True':
                for movie in search_results.get('Search', []):
                    imdb_id = movie.get('imdbID')
                    if imdb_id:
                        detail_response = requests.get(f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&i={imdb_id}")
                        if detail_response.status_code == 200:
                            movie_details = detail_response.json()
                            movie_data.append(movie_details)
            else:
                error_message = "No results found for the movie you searched for."
        else:
            error_message = "Movie data could not be retrieved. Please try again."
    return render_template('movies.html', movie_data=movie_data, error_message=error_message)

# Route to add a movie to the favorites list
@app.route('/add_to_favorites', methods=['POST'])
def add_to_favorites():
    if 'user' not in session:
        return jsonify(success=False, message="You need to log in."), 401
    username = session['user']
    movie_data = request.json.get('movie_data')
    print(f"Received movie_data: {movie_data}")
    try:
        movie_dict = json.loads(movie_data)
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {str(e)}")
        return jsonify(success=False, message=f"Invalid JSON data: {str(e)}"), 400
    existing_favorite = Favorite.query.filter_by(username=username, imdb_id=movie_dict['imdbID']).first()
    if not existing_favorite:
        new_favorite = Favorite(
            username=username,
            imdb_id=movie_dict['imdbID'],
            title=movie_dict['Title'],
            year=movie_dict['Year'],
            genre=movie_dict['Genre'],
            director=movie_dict['Director'],
            actors=movie_dict['Actors'],
            plot=movie_dict['Plot'],
            poster=movie_dict['Poster'],
            imdb_rating=movie_dict['imdbRating']
        )
        db.session.add(new_favorite)
        db.session.commit()
        return jsonify(success=True, message="Movie added to favorites.")
    else:
        return jsonify(success=False, message="Movie is already in your favorites.")

# Route to display the favorites list
@app.route('/favorites')
def favorites():
    if 'user' not in session:
        return redirect(url_for('home'))
    username = session['user']
    favorite_movies = Favorite.query.filter_by(username=username).all()
    return render_template('favorites.html', favorite_movies=favorite_movies)

# Route to change user password
@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user' not in session:
        return redirect(url_for('home'))
    username = session['user']
    current_password = request.form['current-password']
    new_password = request.form['new-password']
    users = load_users()
    user_info = next((user for user in users if user['username'] == username), None)
    if user_info and user_info['password'] == current_password:
        if update_user_info(username, new_password=new_password):
            return redirect(url_for('profile'))
        else:
            return "Password could not be updated!"
    else:
        return "Current password is incorrect!"

# Route to change user username
@app.route('/change_username', methods=['POST'])
def change_username():
    if 'user' not in session:
        return redirect(url_for('home'))
    username = session['user']
    new_username = request.form['new-username']
    if update_user_info(username, new_username=new_username):
        session['user'] = new_username
        return redirect(url_for('profile'))
    else:
        return "Username could not be updated!"

# Route to get movie details by title
@app.route('/movie_details')
def movie_details():
    title = request.args.get('title')
    response = requests.get(f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&t={title}")
    if response.status_code == 200:
        return jsonify(response.json())
    else:
        return jsonify({"error": "Movie information could not be retrieved."}), 500

# Route to remove a movie from the favorites list
@app.route('/remove_from_favorites', methods=['POST'])
def remove_from_favorites():
    data = request.get_json()
    title = data.get('title')
    if not title:
        return jsonify({'success': False, 'message': 'Movie title not specified.'}), 400
    try:
        remove_movie_from_favorites(title)
        return jsonify({'success': True, 'message': 'Movie removed from favorites.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Helper function to remove a movie from the favorites list
def remove_movie_from_favorites(title):
    username = session.get('user')
    if not username:
        raise Exception('User session not found.')
    favorite = Favorite.query.filter_by(username=username, title=title).first()
    if not favorite:
        raise Exception('Movie not found in favorites.')
    db.session.delete(favorite)
    db.session.commit()

# Route to add a movie to the watched list
@app.route('/add_to_watched', methods=['POST'])
def add_to_watched():
    if 'user' not in session:
        return jsonify(success=False, message="You need to log in."), 401
    username = session['user']
    movie_data = request.json.get('movie_data')
    print(f"Received movie_data: {movie_data}")
    try:
        movie_dict = json.loads(movie_data)
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {str(e)}")
        return jsonify(success=False, message=f"Invalid JSON data: {str(e)}"), 400
    existing_watched = Watched.query.filter_by(username=username, imdb_id=movie_dict['imdbID']).first()
    if not existing_watched:
        new_watched = Watched(
            username=username,
            imdb_id=movie_dict['imdbID'],
            title=movie_dict['Title'],
            year=movie_dict['Year'],
            genre=movie_dict['Genre'],
            director=movie_dict['Director'],
            actors=movie_dict['Actors'],
            plot=movie_dict['Plot'],
            poster=movie_dict['Poster'],
            imdb_rating=movie_dict['imdbRating']
        )
        db.session.add(new_watched)
        db.session.commit()
        return jsonify(success=True, message="Movie added to watched.")
    else:
        return jsonify(success=False, message="Movie is already in your watched list.")

# Route to display the watched list
@app.route('/watched')
def watched():
    if 'user' not in session:
        return redirect(url_for('home'))
    username = session['user']
    watched_movies = Watched.query.filter_by(username=username).all()
    return render_template('watched.html', watched_movies=watched_movies)

# Route to remove a movie from the watched list
@app.route('/remove_from_watched', methods=['POST'])
def remove_from_watched():
    data = request.get_json()
    title = data.get('title')
    if not title:
        return jsonify({'success': False, 'message': 'Movie title not specified.'}), 400
    try:
        remove_movie_from_watched(title)
        return jsonify({'success': True, 'message': 'Movie removed from watched.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Helper function to remove a movie from the watched list
def remove_movie_from_watched(title):
    username = session.get('user')
    if not username:
        raise Exception('User session not found.')
    watched = Watched.query.filter_by(username=username, title=title).first()
    if not watched:
        raise Exception('Movie not found in watched.')
    db.session.delete(watched)
    db.session.commit()

# Another helper function to remove a movie from the watched list (duplicate)
def remove_movie_watched(title):
    username = session.get('user')
    if not username:
        raise Exception('User session not found.')
    watched = Watched.query.filter_by(username=username, title=title).first()
    if not watched:
        raise Exception('Movie not found in watched.')
    db.session.delete(watched)
    db.session.commit()

# Route to add a movie to the watchlist
@app.route('/add_to_watchlist', methods=['POST'])
def add_to_watchlist():
    if 'user' not in session:
        return jsonify(success=False, message="You need to log in."), 401
    username = session['user']
    movie_data = request.json.get('movie_data')
    print(f"Received movie_data: {movie_data}")
    try:
        movie_dict = json.loads(movie_data)
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {str(e)}")
        return jsonify(success=False, message=f"Invalid JSON data: {str(e)}"), 400
    existing_watchlist = Watchlist.query.filter_by(username=username, imdb_id=movie_dict['imdbID']).first()
    if not existing_watchlist:
        new_watchlist = Watchlist(
            username=username,
            imdb_id=movie_dict['imdbID'],
            title=movie_dict['Title'],
            year=movie_dict['Year'],
            genre=movie_dict['Genre'],
            director=movie_dict['Director'],
            actors=movie_dict['Actors'],
            plot=movie_dict['Plot'],
            poster=movie_dict['Poster'],
            imdb_rating=movie_dict['imdbRating']
        )
        db.session.add(new_watchlist)
        db.session.commit()
        return jsonify(success=True, message="Movie added to watchlist.")
    else:
        return jsonify(success=False, message="Movie is already in your watchlist.")

# Route to display the watchlist
@app.route('/watchlist')
def watchlist():
    if 'user' not in session:
        return redirect(url_for('home'))
    username = session['user']
    watchlist_movies = Watchlist.query.filter_by(username=username).all()
    return render_template('watchlist.html', watchlist_movies=watchlist_movies)

# Route to remove a movie from the watchlist
@app.route('/remove_from_watchlist', methods=['POST'])
def remove_from_watchlist():
    data = request.get_json()
    title = data.get('title')
    if not title:
        return jsonify({'success': False, 'message': 'Movie title not specified.'}), 400
    try:
        remove_movie_from_watchlist(title)
        return jsonify({'success': True, 'message': 'Movie removed from watchlist.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Helper function to remove a movie from the watchlist
def remove_movie_from_watchlist(title):
    username = session.get('user')
    if not username:
        raise Exception('User session not found.')
    watchlist = Watchlist.query.filter_by(username=username, title=title).first()
    if not watchlist:
        raise Exception('Movie not found in watchlist.')
    db.session.delete(watchlist)
    db.session.commit()

# Another helper function to remove a movie from the watchlist (duplicate)
def remove_movie_watchlist(title):
    username = session.get('user')
    if not username:
        raise Exception('User session not found.')
    watchlist = Watchlist.query.filter_by(username=username, title=title).first()
    if not watchlist:
        raise Exception('Movie not found in watchlist.')
    db.session.delete(watchlist)
    db.session.commit()

# Route to add a movie to the rating list
@app.route('/add_to_rating', methods=['POST'])
def add_to_rating():
    if 'user' not in session:
        return jsonify(success=False, message="You need to log in."), 401
    username = session['user']
    movie_data = request.json.get('movie_data')
    print(f"Received movie_data: {movie_data}")
    try:
        movie_dict = json.loads(movie_data)
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {str(e)}")
        return jsonify(success=False, message=f"Invalid JSON data: {str(e)}"), 400
    existing_rating = Rating.query.filter_by(username=username, imdb_id=movie_dict['imdbID']).first()
    if not existing_rating:
        new_rating = Rating(
            username=username,
            imdb_id=movie_dict['imdbID'],
            title=movie_dict['Title'],
            year=movie_dict['Year'],
            genre=movie_dict['Genre'],
            director=movie_dict['Director'],
            actors=movie_dict['Actors'],
            plot=movie_dict['Plot'],
            poster=movie_dict['Poster'],
            imdb_rating=movie_dict['imdbRating']
        )
        db.session.add(new_rating)
        db.session.commit()
        return jsonify(success=True, message="Movie rated.")
    else:
        return jsonify(success=False, message="Movie already rated.")

# Route to display the rating list
@app.route('/rating')
def rating():
    if 'user' not in session:
        return redirect(url_for('home'))
    username = session['user']
    rating_movies = Rating.query.filter_by(username=username).all()
    return render_template('rating.html', rating_movies=rating_movies)

# Route to remove a movie from the rating list
@app.route('/remove_from_rating', methods=['POST'])
def remove_from_rating():
    data = request.get_json()
    title = data.get('title')
    if not title:
        return jsonify({'success': False, 'message': 'Movie title not specified.'}), 400
    try:
        remove_movie_from_rating(title)
        return jsonify({'success': True, 'message': 'Movie removed from rating list.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Helper function to remove a movie from the rating list
def remove_movie_from_rating(title):
    username = session.get('user')
    if not username:
        raise Exception('User session not found.')
    rating = Rating.query.filter_by(username=username, title=title).first()
    if not rating:
        raise Exception('Movie not found in rating list.')
    db.session.delete(rating)
    db.session.commit()

# Another helper function to remove a movie from the rating list (duplicate)
def remove_movie_rating(title):
    username = session.get('user')
    if not username:
        raise Exception('User session not found.')
    rating = Rating.query.filter_by(username=username, title=title).first()
    if not rating:
        raise Exception('Movie not found in rating list.')
    db.session.delete(rating)
    db.session.commit()

# Route to rate a movie
@app.route('/rate_movie', methods=['POST'])
def rate_movie():
    if 'user' not in session:
        return jsonify(success=False, message="You need to log in."), 401
    data = request.get_json()
    movie_data = data.get('movie_data')
    rating_value = data.get('rating')
    try:
        movie_dict = json.loads(movie_data)
    except json.JSONDecodeError as e:
        return jsonify(success=False, message=f"Invalid JSON data: {str(e)}"), 400
    existing_rating = Rating.query.filter_by(username=session['user'], imdb_id=movie_dict['imdbID']).first()
    if not existing_rating:
        new_rating = Rating(
            username=session['user'],
            imdb_id=movie_dict['imdbID'],
            title=movie_dict['Title'],
            year=movie_dict['Year'],
            genre=movie_dict['Genre'],
            director=movie_dict['Director'],
            actors=movie_dict['Actors'],
            plot=movie_dict['Plot'],
            poster=movie_dict['Poster'],
            imdb_rating=movie_dict['imdbRating']
        )
        db.session.add(new_rating)
        db.session.commit()
        return jsonify(success=True, message="Movie rated.")
    else:
        existing_rating.imdb_rating = rating_value
        db.session.commit()
        return jsonify(success=True, message="Movie rating updated.")

if __name__ == "__main__":
    app.run(debug=True)
