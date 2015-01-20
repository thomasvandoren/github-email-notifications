import os
from flask import Flask
import flask
from flask.ext.heroku import Heroku

app = Flask(__name__)
heroku = Heroku(app)

@app.route('/')
def index():
    """Redirect to chapel homepage."""
    return flask.redirect('http://chapel-lang.org/', code=301)

@app.route('/commit-email', methods=['POST'])
def commit_email():
    """Receive web hook from github and generate email."""
    return 'blah'
