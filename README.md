chapel-commit-emailer
=====================

Better email notifications from github. Geared towards Chapel workflow.

[![Build Status](https://travis-ci.org/thomasvandoren/chapel-commit-emailer.svg?branch=master)](https://travis-ci.org/thomasvandoren/chapel-commit-emailer) [![Coverage Status](https://coveralls.io/repos/thomasvandoren/chapel-commit-emailer/badge.svg?branch=master)](https://coveralls.io/r/thomasvandoren/chapel-commit-emailer?branch=master)

Heroku Setup
------------

Create the app, enable papertrail to record logs, and set the configuration
variables.

```bash
heroku create [<app_name>]
heroku addons:add papertrail
heroku config:set CHAPEL_EMAILER_SENDER=<sender_email>
heroku config:set CHAPEL_EMAILER_RECIPIENT=<recipient_email>
heroku config:set CHAPEL_EMAILER_SECRET=<the_secret>
```

SendGrid Setup
--------------

Enable addon, and disable the plain text to html conversion:

```bash
heroku addons:add sendgrid
heroku addons:open sendgrid
```

* Go to "Global Settings".
* Check the "Don't convert plain text emails to HTML" box and "Update".

GitHub Setup
------------

Add webhook to repo to use this emailer. Be sure to set the secret to the value
of `CHAPEL_EMAILER_SECRET`. The webhook URL is `<heroku_url>/commit-email` and
it must send "push" events. Show the heroku app url with:

```bash
heroku domains
```

Development
-----------

To develop and test locally, install the [Heroku Toolbelt][0], python
dependencies, create a `.env` file, and use `foreman start` to run the app.

* Install python dependencies (assuming virtualenvwrapper is available):

```bash
mkvirtualenv chapel-commit-emailer
pip install -r requirements.txt
```

* Create `.env` file with chapel config values:

```
CHAPEL_EMAILER_SENDER=<email>
CHAPEL_EMAILER_RECIPIENT=<email>
CHAPEL_EMAILER_SECRET=<the_secret>
SENDGRID_PASSWORD=<sendgrid_password>
SENDGRID_USERNAME=<sendgrid_user>
```

Use `heroku config` to get the sendgrid values.

* Run the app, which opens at `http://localhost:5000`:

```bash
foreman start
```

* Send a test request:

```bash
curl -vs -X POST \
  'http://localhost:5000/commit-email' \
  -H 'x-github-event: push'
  -H 'content-type: application/json' \
  -d '{"deleted": false,
    "compare": "http://compare.me",
    "repository": {"full_name": "bite/me"},
    "head_commit": {
      "id": "mysha1here",
      "message": "This is my message\nwith a break!",
      "added": ["index.html"],
      "removed": ["removed.it"],
      "modified": ["stuff", "was", "done"]},
    "pusher": {"name": "thomasvandoren"}}'
```

* Install test dependencies and run the unittests.

```bash
pip install -r test-requirements.txt
tox
tox -e flake8
tox -e coverage
```

[0]: https://toolbelt.heroku.com/
