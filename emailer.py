import envelopes
import envelopes.connstack
from flask import Flask
import flask
import logging
import os

app = Flask(__name__)
heroku = Heroku(app)
conn = envelopes.SendGridSMTP(login=app.config['SENDGRID_USERNAME'], password=app.config['SENDGRID_PASSWORD'])

logging.basicConfig(level=logging.INFO)

@app.before_request
def app_before_request():
    envelopes.connstack.push_connection(conn)


@app.after_request
def app_after_request(response):
    envelopes.connstack.pop_connection()
    return response


@app.route('/')
def index():
    """Redirect to chapel homepage."""
    return flask.redirect('http://chapel-lang.org/', code=301)


@app.route('/commit-email', methods=['POST'])
def commit_email():
    """Receive web hook from github and generate email."""
    json_dict = flask.request.get_json()
    logging.info('json body: {0}'.format(json_dict))

    if json_dict['deleted']:
        logging.info('Branch was deleted, skipping email.')
        return 'nope'

    added = '\n'.join(map(lambda f: 'A {0}'.format(f),
                          json_dict['head_commit']['added']))
    removed = '\n'.join(map(lambda f: 'R {0}'.format(f),
                            json_dict['head_commit']['removed']))
    modified = '\n'.join(map(lambda f: 'M {0}'.format(f),
                             json_dict['head_commit']['modified']))
    changes = '\n'.join([added, removed, modified])

    msg_info = {
        'repo': json_dict['repository']['full_name'],
        'revision': json_dict['head_commit']['url'],
        'message': json_dict['head_commit']['message'],
        'changed_files': changes,
        'pusher': json_dict['pusher']['name'],
        'compare_url': json_dict['compare'],
    }

    sender = os.environ.get('CHAPEL_EMAILER_SENDER')
    recipient = os.environ.get('CHAPEL_EMAILER_RECIPIENT')

    subject = '[{0}] {1}'.format(
        msg_info['repo'],
        msg_info['message'].splitlines()[0])
    body = """Revision: {revision}
Author: {pusher}
Compare: {compare_url}
Log Message:
------------
{message}

Modified Files:
---------------
{changed_files}
""".format(**msg_info)

    msg = envelopes.Envelope(
        to_addr=recipient,
        from_addr=sender,
        subject=subject,
        text_body=body
    )
    smtp = envelopes.connstack.get_current_connection()
    logging.info('Sending email: {0}'.format(msg))
    smtp.send(msg)

    return 'yep'
