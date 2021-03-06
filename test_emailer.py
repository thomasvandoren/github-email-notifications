import hmac
import json
import mock
import os
import sha
import unittest
import uuid

import emailer


@mock.patch('logging.error', new=mock.Mock())
@mock.patch('logging.warn', new=mock.Mock())
@mock.patch('logging.info', new=mock.Mock())
class EmailerTests(unittest.TestCase):

    def setUp(self):
        """Setup flask app for testing."""
        super(EmailerTests, self).setUp()
        emailer.app.config['TESTING'] = True
        self.app = emailer.app.test_client()
        self.headers = {
            'x-github-event': 'push',
            'x-hub-signature': 'bogus-sig',
            'content-type': 'application/json',
        }
        self.msg_info = {
            'repo': 'TESTING/test',
            'branch': 'the/TEST/master',
            'revision': 'some-TEST-sha1',
            'message': 'A lovely TEST\n\nTEST commit message.',
            'changed_files': ('R a.out\n'
                              'R gen\n'
                              'M README.md\n'
                              'M README\n'
                              'M LICENSE'),
            'pusher': 'TESTING-the-tester',
            'pusher_email': 'TESTING-the-tester <TEST@example.com>',
            'compare_url': 'http://TEST.fake',
        }
        self.sender = 'noreply@fake.fake'
        self.recipient = 'recip@fake.fake'
        self.reply_to = 'reply-to-me@fake.fake'
        self.send_grid_header = json.dumps(
            {'filters': {'clicktrack': {'settings': {'enable': 0}}}})

    @mock.patch('flask.got_request_exception.connect')
    @mock.patch('rollbar.init')
    def test_rollbar_init__testing(self, mock_init, mock_exc):
        """Verify rollbar is not initalized in unittest environment."""
        self.app.get('/')
        self.assertEqual(0, mock_init.call_count)
        self.assertEqual(0, mock_exc.call_count)

    @mock.patch('flask.got_request_exception.connect')
    @mock.patch('rollbar.init')
    def test_rollbar_init(self, mock_init, mock_exc):
        """Verify rollbar init is called."""
        os.environ['ROLLBAR_ACCESS_TOKEN'] = 'fakefakefake'
        emailer.app.config['TESTING'] = False
        emailer.app.before_first_request_funcs[0]()

        mock_init.assert_called_once_with(
            'fakefakefake',
            'github-email-notifications',
            root=os.path.abspath(os.path.dirname(__file__)),
            allow_logging_basic_config=False
        )
        mock_exc.assert_called_once_with(mock.ANY, emailer.app)

    @mock.patch('flask.got_request_exception.connect')
    @mock.patch('rollbar.init')
    def test_rollbar_init__env_name(self, mock_init, mock_exc):
        """Verify rollbar init is called with rollbar env name from env var."""
        os.environ['ROLLBAR_ACCESS_TOKEN'] = 'fakefakefake'
        os.environ['GITHUB_COMMIT_EMAILER_ROLLBAR_ENV'] = 'my-TEST-env'
        emailer.app.config['TESTING'] = False
        emailer.app.before_first_request_funcs[0]()

        mock_init.assert_called_once_with(
            'fakefakefake',
            'my-TEST-env',
            root=os.path.abspath(os.path.dirname(__file__)),
            allow_logging_basic_config=False
        )
        mock_exc.assert_called_once_with(mock.ANY, emailer.app)

    def test_index_redirects(self):
        """Verify index page redirects to chapel-lang.org."""
        r = self.app.get('/')
        self.assertEqual(301, r.status_code)
        self.assertEqual('http://chapel-lang.org/', r.headers['location'])

    @mock.patch('emailer._send_email')
    def test_non_push_event(self, mock_send):
        """Verify non-push event is skipped."""
        r = self.app.post('/commit-email',
                          headers={'x-github-event': 'whatevs'})
        self.assertEqual(200, r.status_code)
        self.assertEqual(0, mock_send.call_count)

    @mock.patch('emailer._get_secret')
    @mock.patch('emailer._send_email')
    def test_push_invalid_signature(self, mock_send, mock_secret):
        """Verify push event with invalid sig is skipped."""
        mock_secret.return_value = 'asdf'
        headers = {'x-github-event': 'push',
                   'x-hub-signature': 'sha1=bogus'}
        r = self.app.post('/commit-email', headers=headers)
        self.assertEqual(200, r.status_code)
        self.assertEqual(0, mock_send.call_count)

    def test_no_secret_in_env(self):
        """Verify raises error when secret is not in environment."""
        if 'GITHUB_COMMIT_EMAILER_SECRET' in os.environ:
            del os.environ['GITHUB_COMMIT_EMAILER_SECRET']
        self.assertRaises(
            ValueError,
            self.app.post,
            '/commit-email',
            headers=self.headers
        )

    @mock.patch('emailer._valid_signature')
    @mock.patch('emailer._get_secret')
    @mock.patch('emailer._send_email')
    def test_deleted_branch(self, mock_send, mock_sec, mock_sig):
        """Verify deleted branch notification are skipped."""
        mock_sec.return_value = 'asdf'
        mock_sig.return_value = True
        r = self.app.post('/commit-email',
                          headers=self.headers,
                          data=json.dumps({'deleted': True}))
        self.assertEqual(200, r.status_code)
        self.assertEqual(0, mock_send.call_count)

    @mock.patch('emailer._valid_signature')
    @mock.patch('emailer._get_secret')
    @mock.patch('emailer._send_email')
    def test_test_send_mail(self, mock_send, mock_sec, mock_sig):
        """Verify correct message info is passed to _send_email."""
        mock_sec.return_value = 'adsf'
        mock_sig.return_value = True
        body = {
            'ref': 'the/master',
            'deleted': False,
            'compare': 'http://the-url.it',
            'repository': {'full_name': 'testing/test'},
            'pusher': {'name': 'the-tester', 'email': 'the@example.com'},
            'head_commit': {
                'id': 'some-sha1',
                'message': 'A lovely\n\ncommit message.',
                'added': [],
                'removed': ['a.out', 'gen'],
                'modified': ['README.md', 'README', 'LICENSE'],
            },
        }
        expected_msg_info = {
            'repo': 'testing/test',
            'branch': 'the/master',
            'revision': 'some-sha1'[:7],
            'message': 'A lovely\n\ncommit message.',
            'changed_files': ('R a.out\n'
                              'R gen\n'
                              'M README.md\n'
                              'M README\n'
                              'M LICENSE'),
            'pusher': 'the-tester',
            'pusher_email': 'the-tester <the@example.com>',
            'compare_url': 'http://the-url.it',
        }
        r = self.app.post('/commit-email',
                          headers=self.headers,
                          data=json.dumps(body))
        self.assertEqual(200, r.status_code)
        mock_send.assert_called_once_with(expected_msg_info)

    def test_send_email__no_sender(self):
        """Verify ValueError when sender is not configured."""
        if 'GITHUB_COMMIT_EMAILER_SENDER' in os.environ:
            del os.environ['GITHUB_COMMIT_EMAILER_SENDER']
        self.assertRaises(ValueError,
                          emailer._send_email, {'pusher_email': 'x'})

    def test_send_email__no_recipient(self):
        """Verify ValueError when recipient is not configured."""
        if 'GITHUB_COMMIT_EMAILER_RECIPIENT' in os.environ:
            del os.environ['GITHUB_COMMIT_EMAILER_RECIPIENT']
        self.assertRaises(ValueError,
                          emailer._send_email, {'pusher_email': 'x'})

    def test_send_email__missing_both(self):
        """Verify ValueError when recipient and sender are not configured."""
        if 'GITHUB_COMMIT_EMAILER_SENDER' in os.environ:
            del os.environ['GITHUB_COMMIT_EMAILER_SENDER']
        if 'GITHUB_COMMIT_EMAILER_RECIPIENT' in os.environ:
            del os.environ['GITHUB_COMMIT_EMAILER_RECIPIENT']
        self.assertRaises(ValueError,
                          emailer._send_email, {'pusher_email': 'x'})

    def prep_env(self):
        """Prepare os.environ for _send_email() tests."""
        os.environ['GITHUB_COMMIT_EMAILER_SENDER'] = self.sender
        os.environ['GITHUB_COMMIT_EMAILER_RECIPIENT'] = self.recipient

    def check_msg(self, actual_msg):
        """Verify recipient and sender on sent message."""
        self.assertEqual([self.recipient], actual_msg.to_addr)
        self.assertEqual(self.sender, actual_msg.from_addr)
        self.assertEqual(
            self.send_grid_header, actual_msg.headers.get('X-SMTPAPI'))
        self.assertEqual(
            '[TESTING/test] TEST commit message.', actual_msg._subject)

    @mock.patch('envelopes.connstack.get_current_connection')
    def test_send_email__no_reply_to(self, mock_send):
        """Verify email is sent as expected when reply-to is not configured."""
        self.prep_env()
        if 'GITHUB_COMMIT_EMAILER_REPLY_TO' in os.environ:
            del os.environ['GITHUB_COMMIT_EMAILER_REPLY_TO']
        emailer._send_email(self.msg_info)

        mock_send.return_value.send.assert_called_once_with(mock.ANY)
        actual_msg = mock_send.return_value.send.call_args[0][0]
        self.check_msg(actual_msg)
        self.assertEqual(None, actual_msg.headers.get('Reply-To'))

    @mock.patch('envelopes.connstack.get_current_connection')
    def test_send_email__reply_to(self, mock_send):
        """Verify email is sent as expected when reply-to is configured."""
        self.prep_env()
        os.environ['GITHUB_COMMIT_EMAILER_REPLY_TO'] = self.reply_to
        emailer._send_email(self.msg_info)

        mock_send.return_value.send.assert_called_once_with(mock.ANY)
        actual_msg = mock_send.return_value.send.call_args[0][0]
        self.check_msg(actual_msg)
        self.assertEqual(self.reply_to, actual_msg.headers.get('Reply-To'))

    @mock.patch('envelopes.connstack.get_current_connection')
    def test_send_email__approved(self, mock_send):
        """Verify approved header is added when config is set."""
        self.prep_env()
        os.environ['GITHUB_COMMIT_EMAILER_APPROVED_HEADER'] = 'my-super-secret'
        emailer._send_email(self.msg_info)

        mock_send.return_value.send.assert_called_once_with(mock.ANY)
        actual_msg = mock_send.return_value.send.call_args[0][0]
        self.check_msg(actual_msg)
        self.assertEqual('my-super-secret', actual_msg.headers.get('Approved'))

    @mock.patch('envelopes.connstack.get_current_connection')
    def test_send_email__no_approved(self, mock_send):
        """Verify approved header is not added when config is not set."""
        self.prep_env()
        if 'GITHUB_COMMIT_EMAILER_APPROVED_HEADER' in os.environ:
            del os.environ['GITHUB_COMMIT_EMAILER_APPROVED_HEADER']
        emailer._send_email(self.msg_info)

        mock_send.return_value.send.assert_called_once_with(mock.ANY)
        actual_msg = mock_send.return_value.send.call_args[0][0]
        self.check_msg(actual_msg)
        self.assertEqual(None, actual_msg.headers.get('Approved'))

    def test_get_sender__from_author(self):
        """Verify sent from author when appropriate config var set."""
        os.environ['GITHUB_COMMIT_EMAILER_SEND_FROM_AUTHOR'] = 'whatevs'
        actual = emailer._get_sender('my-address')
        self.assertEqual('my-address', actual)

    def test_get_sender__from_noreply(self):
        """Verify sent from config'd sender when appropriate config var
        not set.
        """
        if 'GITHUB_COMMIT_EMAILER_SEND_FROM_AUTHOR' in os.environ:
            del os.environ['GITHUB_COMMIT_EMAILER_SEND_FROM_AUTHOR']
        os.environ['GITHUB_COMMIT_EMAILER_SENDER'] = 'noreply-addr'
        actual = emailer._get_sender('my-address')
        self.assertEqual('noreply-addr', actual)

    def test_get_subject(self):
        """Verify get_subject returns first line of commit message and
        repo name.
        """
        expected = '[TEST/it] this is a message'
        actual = emailer._get_subject('TEST/it', 'this is a message')
        self.assertEqual(expected, actual)

    def test_get_subject__msg_greater_than_50(self):
        """Verify subject when commit message line has more than 50 chars."""
        repo = 'TEST/realllllllllllllllyyyyyyyyyyy-loooooooooooooong'
        msg = 'this is really long {0}'.format('.' * 100)
        assert len(msg) > 50
        expected = '[{0}] {1}'.format(repo, msg[:50])
        actual = emailer._get_subject(repo, msg)
        self.assertEqual(expected, actual)

    def test_get_subject__third_line(self):
        """Verify subject when commit message has three lines."""
        msg = ('merge pull request #blah\n\n'
               'my real message\n\n'
               'with lots of info\n')
        expected = '[TEST/it] my real message'
        actual = emailer._get_subject('TEST/it', msg)
        self.assertEqual(expected, actual)

    def test_valid_signature__true__str(self):
        """Verify _valid_signature returns true when signature matches."""
        body = '{"rock": "on"}'
        secret = str(uuid.uuid4())
        h = hmac.new(secret, body, sha)
        sig = 'sha1=' + h.hexdigest()
        gh_sig = sig
        self.assertTrue(emailer._valid_signature(gh_sig, body, secret))

    def test_valid_signature__true__unicode(self):
        """Verify _valid_signature returns true when signature matches, even if github
        signature is unicode."""
        body = '{"rock": "on"}'
        secret = str(uuid.uuid4())
        h = hmac.new(secret, body, sha)
        sig = 'sha1=' + h.hexdigest()
        gh_sig = unicode(sig)
        self.assertTrue(emailer._valid_signature(gh_sig, body, secret))

    def test_valid_signature__false(self):
        """Verify _valid_signature returns False when signature does
        not match."""
        self.assertFalse(
            emailer._valid_signature(str(unicode('adsf')), 'asdf', 'my-secret')
        )


if __name__ == '__main__':
    unittest.main()
