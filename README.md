github-email-notifications
==========================

Better email notifications from github with clear, concise, and readable
messages.

[![Build Status](https://travis-ci.org/chapel-lang/github-email-notifications.svg?branch=master)](https://travis-ci.org/chapel-lang/github-email-notifications) [![Coverage Status](https://coveralls.io/repos/chapel-lang/github-email-notifications/badge.svg?branch=master)](https://coveralls.io/r/chapel-lang/github-email-notifications?branch=master)

Simple python web application for Heroku that accepts github webhooks for
["push" events][push_events] and generates a clear, concise, and readable email
message.

It is designed to meet the [Chapel][chapel] team's needs, as the email hook
provided by github is rather noisy and it looks unlikely to change. The Chapel
project uses the [feature branch workflow][fb_workflow], and always includes a
nice summary in the merge commit messages. So, the merge message (actually the
head commit in the push event) is the only one included in the email.

[chapel]: http://chapel-lang.org/
[fb_workflow]: https://www.atlassian.com/git/tutorials/comparing-workflows/feature-branch-workflow/
[push_events]: https://developer.github.com/v3/activity/events/types/#pushevent

Heroku Setup
------------

Create the app, enable papertrail to record logs, and set the configuration
variables.

```bash
heroku create [<app_name>]
heroku addons:add papertrail
heroku config:set GITHUB_COMMIT_EMAILER_SEND_FROM_AUTHOR=<true>
heroku config:set GITHUB_COMMIT_EMAILER_SENDER=<sender_email>
heroku config:set GITHUB_COMMIT_EMAILER_RECIPIENT=<recipient_email>
heroku config:set GITHUB_COMMIT_EMAILER_SECRET=<the_secret>
```

If `GITHUB_COMMIT_EMAILER_SEND_FROM_AUTHOR` is set (to any value), the pusher
name and email combination will be used as the "From" address instead of the
configured sender value. If a reply-to is configured, see below, that will be
added regardless of this setting.

Optionally, a reply-to address can be configured with the following config. If
not set, no reply-to header is set so the sender address will be used as reply
address.

```bash
heroku config:set GITHUB_COMMIT_EMAILER_REPLY_TO=<reply_to_email>
```

Optionally, an "Approved" header value can be configured. The Approved header
automatically approves the messages for a read-only or moderated mailing list.

```bash
heroku config:set GITHUB_COMMIT_EMAILER_APPROVED_HEADER=<approved_header>
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

Rollbar Setup
-------------

Rollbar provides error tracking, in case anything unexpected happens. Enable
the addon and optionally set the environment name.

```bash
heroku addons:add rollbar
```

Optionally, set the environment name for rollbar. This is probably only
necessary if you have multiple environment configured to use rollbar.

```bash
heroku config:set GITHUB_COMMIT_EMAILER_ROLLBAR_ENV=<env_name>
```

GitHub Setup
------------

Add webhook to repo to use this emailer. Be sure to set the secret to the value
of `GITHUB_COMMIT_EMAILER_SECRET`. The webhook URL is
`<heroku_url>/commit-email` and it must send "push" events. Show the heroku app
url with:

```bash
heroku domains
```

Development
-----------

To develop and test locally, install the [Heroku Toolbelt][0], python
dependencies, create a `.env` file, and use `foreman start` to run the app.

* Install python dependencies (assuming virtualenvwrapper is available):

```bash
mkvirtualenv github-email-notifications
pip install -r requirements.txt
```

* Create `.env` file with chapel config values:

```
GITHUB_COMMIT_EMAILER_SENDER=<email>
GITHUB_COMMIT_EMAILER_RECIPIENT=<email>
GITHUB_COMMIT_EMAILER_SECRET=<the_secret>
ROLLBAR_ACCESS_TOKEN=<rollbar_token>
SENDGRID_PASSWORD=<sendgrid_password>
SENDGRID_USERNAME=<sendgrid_user>
```

To use the same values configured in heroku:

```bash
heroku config --shell > .env
```

* Run the app, which opens at `http://localhost:5000`:

```bash
foreman start
```

* Send a test request:

```bash
curl -vs -X POST \
  'http://localhost:5000/commit-email' \
  -H 'x-github-event: push' \
  -H 'content-type: application/json' \
  -d '{"deleted": false,
    "ref": "refs/heads/master",
    "compare": "http://compare.me",
    "repository": {"full_name": "test/it"},
    "head_commit": {
      "id": "mysha1here",
      "message": "This is my message\nwith a break!",
      "added": ["index.html"],
      "removed": ["removed.it"],
      "modified": ["stuff", "was", "done"]},
    "pusher": {
      "name": "thomasvandoren",
      "email": "testing@github-email-notification.info"}}'
```

* Install test dependencies and run the unittests.

```bash
pip install -r test-requirements.txt
tox
tox -e flake8
tox -e coverage
```

[0]: https://toolbelt.heroku.com/
