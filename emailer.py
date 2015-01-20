import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return 'Move along, nothing to see here.'
