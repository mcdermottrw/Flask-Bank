from flask import Flask, session

from routes import main, poolBrowser
from database import db


def create_app():
    # Initialize Flask object
    app = Flask(__name__)

    # Register routing blueprint so that routes in other files (namely routes.py) can be recognized
    app.register_blueprint(main)

    # Configuration settings
    app.config["SECRET_KEY"] = "microlend2021"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite3"  # Sets the name and location of the sqlite3 database
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Turns off unnecessary warning message

    # Initializes the database and associates it with the Flask app
    db.init_app(app)
    with app.app_context():
        db.create_all()

    return app


# create_app() is used to make configurations for the Flask application
# app.run() starts the application itself
if __name__ == "__main__":
    app = create_app()
    app.run()
    session["logged_in"] = False
