import hmac
import sha
import unittest
import uuid

import emailer


class EmailerTests(unittest.TestCase):

    def test_valid_signature__true__str(self):
        body = '{"rock": "on"}'
        secret = str(uuid.uuid4())
        h = hmac.new(secret, body, sha)
        sig = 'sha1=' + h.hexdigest()
        gh_sig = sig
        self.assertTrue(emailer._valid_signature(gh_sig, body, secret))

    def test_valid_signature__true__unicode(self):
        body = '{"rock": "on"}'
        secret = str(uuid.uuid4())
        h = hmac.new(secret, body, sha)
        sig = 'sha1=' + h.hexdigest()
        gh_sig = unicode(sig)
        self.assertTrue(emailer._valid_signature(gh_sig, body, secret))

    def test_valid_signature__false(self):
        self.assertFalse(
            emailer._valid_signature(str(unicode('adsf')), 'asdf', 'my-secret')
        )


if __name__ == '__main__':
    unittest.main()
