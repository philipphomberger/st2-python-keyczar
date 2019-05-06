# -*- coding: utf-8 -*-
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import uuid
import base64
import tempfile
import socket

import six
import mock
import mailparser

from st2common.constants import action as action_constants

from st2tests.fixturesloader import FixturesLoader
from st2tests.base import RunnerTestCase
from st2tests.base import CleanDbTestCase
from st2tests.base import CleanFilesTestCase

from local_runner.local_shell_script_runner import LocalShellScriptRunner

__all__ = [
    'SendmailActionTestCase'
]

MOCK_EXECUTION = mock.Mock()
MOCK_EXECUTION.id = '598dbf0c0640fd54bffc688b'
HOSTNAME = socket.gethostname()


class SendmailActionTestCase(RunnerTestCase, CleanDbTestCase, CleanFilesTestCase):
    """
    NOTE: Those tests rely on stanley user being available on the system and having paswordless
    sudo access.
    """
    fixtures_loader = FixturesLoader()

    def test_sendmail_default_text_html_content_type(self):
        action_parameters = {
            'sendmail_binary': 'cat',

            'from': 'from.user@example.tld1',
            'to': 'to.user@example.tld2',
            'subject': 'this is subject 1',
            'send_empty_body': False,
            'content_type': 'text/html',
            'body': 'Hello there html.',
            'attachments': ''
        }

        expected_body = ('Hello there html.\n'
                         '<br><br>\n'
                         'This message was generated by StackStorm action '
                         'send_mail running on %s' % (HOSTNAME))

        status, _, email_data, message = self._run_action(action_parameters=action_parameters)
        self.assertEquals(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

        # Verify subject contains utf-8 charset and is base64 encoded
        self.assertTrue('SUBJECT: =?UTF-8?B?' in email_data)

        self.assertEqual(message.to[0][1], action_parameters['to'])
        self.assertEqual(message.from_[0][1], action_parameters['from'])
        self.assertEqual(message.subject, action_parameters['subject'])
        self.assertEqual(message.body, expected_body)
        self.assertEqual(message.content_type, 'text/html; charset=UTF-8')

    def test_sendmail_text_plain_content_type(self):
        action_parameters = {
            'sendmail_binary': 'cat',

            'from': 'from.user@example.tld1',
            'to': 'to.user@example.tld2',
            'subject': 'this is subject 2',
            'send_empty_body': False,
            'content_type': 'text/plain',
            'body': 'Hello there plain.',
            'attachments': ''
        }

        expected_body = ('Hello there plain.\n\n'
                         'This message was generated by StackStorm action '
                         'send_mail running on %s' % (HOSTNAME))

        status, _, email_data, message = self._run_action(action_parameters=action_parameters)
        self.assertEquals(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

        # Verify subject contains utf-8 charset and is base64 encoded
        self.assertTrue('SUBJECT: =?UTF-8?B?' in email_data)

        self.assertEqual(message.to[0][1], action_parameters['to'])
        self.assertEqual(message.from_[0][1], action_parameters['from'])
        self.assertEqual(message.subject, action_parameters['subject'])
        self.assertEqual(message.body, expected_body)
        self.assertEqual(message.content_type, 'text/plain; charset=UTF-8')

    def test_sendmail_utf8_subject_and_body(self):
        # 1. tex/html
        action_parameters = {
            'sendmail_binary': 'cat',

            'from': 'from.user@example.tld1',
            'to': 'to.user@example.tld2',
            'subject': u'Å unicode subject 😃😃',
            'send_empty_body': False,
            'content_type': 'text/html',
            'body': u'Hello there 😃😃.',
            'attachments': ''
        }

        if six.PY2:
            expected_body = (u'Hello there 😃😃.\n'
                             u'<br><br>\n'
                             u'This message was generated by StackStorm action '
                             u'send_mail running on %s' % (HOSTNAME))
        else:
            expected_body = (u'Hello there \\U0001f603\\U0001f603.\n'
                             u'<br><br>\n'
                             u'This message was generated by StackStorm action '
                             u'send_mail running on %s' % (HOSTNAME))

        status, _, email_data, message = self._run_action(action_parameters=action_parameters)
        self.assertEquals(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

        # Verify subject contains utf-8 charset and is base64 encoded
        self.assertTrue('SUBJECT: =?UTF-8?B?' in email_data)

        self.assertEqual(message.to[0][1], action_parameters['to'])
        self.assertEqual(message.from_[0][1], action_parameters['from'])
        self.assertEqual(message.subject, action_parameters['subject'])
        self.assertEqual(message.body, expected_body)
        self.assertEqual(message.content_type, 'text/html; charset=UTF-8')

        # 2. text/plain
        action_parameters = {
            'sendmail_binary': 'cat',

            'from': 'from.user@example.tld1',
            'to': 'to.user@example.tld2',
            'subject': u'Å unicode subject 😃😃',
            'send_empty_body': False,
            'content_type': 'text/plain',
            'body': u'Hello there 😃😃.',
            'attachments': ''
        }

        if six.PY2:
            expected_body = (u'Hello there 😃😃.\n\n'
                             u'This message was generated by StackStorm action '
                             u'send_mail running on %s' % (HOSTNAME))
        else:
            expected_body = (u'Hello there \\U0001f603\\U0001f603.\n\n'
                             u'This message was generated by StackStorm action '
                             u'send_mail running on %s' % (HOSTNAME))

        status, _, email_data, message = self._run_action(action_parameters=action_parameters)
        self.assertEquals(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

        self.assertEqual(message.to[0][1], action_parameters['to'])
        self.assertEqual(message.from_[0][1], action_parameters['from'])
        self.assertEqual(message.subject, action_parameters['subject'])
        self.assertEqual(message.body, expected_body)
        self.assertEqual(message.content_type, 'text/plain; charset=UTF-8')

    def test_sendmail_with_attachments(self):
        _, path_1 = tempfile.mkstemp()
        _, path_2 = tempfile.mkstemp()
        os.chmod(path_1, 0o755)
        os.chmod(path_2, 0o755)

        self.to_delete_files.append(path_1)
        self.to_delete_files.append(path_2)

        with open(path_1, 'w') as fp:
            fp.write('content 1')

        with open(path_2, 'w') as fp:
            fp.write('content 2')

        action_parameters = {
            'sendmail_binary': 'cat',

            'from': 'from.user@example.tld1',
            'to': 'to.user@example.tld2',
            'subject': 'this is email with attachments',
            'send_empty_body': False,
            'content_type': 'text/plain',
            'body': 'Hello there plain.',
            'attachments': '%s,%s' % (path_1, path_2)
        }

        expected_body = ('Hello there plain.\n\n'
                         'This message was generated by StackStorm action '
                         'send_mail running on %s' % (HOSTNAME))

        status, _, email_data, message = self._run_action(action_parameters=action_parameters)
        self.assertEquals(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

        # Verify subject contains utf-8 charset and is base64 encoded
        self.assertTrue('SUBJECT: =?UTF-8?B?' in email_data)

        self.assertEqual(message.to[0][1], action_parameters['to'])
        self.assertEqual(message.from_[0][1], action_parameters['from'])
        self.assertEqual(message.subject, action_parameters['subject'])
        self.assertEqual(message.body, expected_body)
        self.assertEqual(message.content_type,
                         'multipart/mixed; boundary="ZZ_/afg6432dfgkl.94531q"')

        # There should be 3 message parts - 2 for attachments, one for body
        self.assertEqual(email_data.count('--ZZ_/afg6432dfgkl.94531q'), 3)

        # There should be 2 attachments
        self.assertEqual(email_data.count('Content-Transfer-Encoding: base64'), 2)
        self.assertTrue(base64.b64encode(b'content 1').decode('utf-8') in email_data)
        self.assertTrue(base64.b64encode(b'content 2').decode('utf-8') in email_data)

    def _run_action(self, action_parameters):
        """
        Run action with the provided action parameters, return status output and
        parse the output email data.
        """
        models = self.fixtures_loader.load_models(
            fixtures_pack='packs/core', fixtures_dict={'actions': ['sendmail.yaml']})
        action_db = models['actions']['sendmail.yaml']
        entry_point = self.fixtures_loader.get_fixture_file_path_abs(
            'packs/core', 'actions', 'send_mail/send_mail')

        runner = self._get_runner(action_db, entry_point=entry_point)
        runner.pre_run()
        status, result, _ = runner.run(action_parameters)
        runner.post_run(status, result)

        # Remove footer added by the action which is not part of raw email data and parse
        # the message
        if 'stdout' in result:
            email_data = result['stdout']
            email_data = email_data.split('\n')[:-2]
            email_data = '\n'.join(email_data)

            if six.PY2 and isinstance(email_data, six.text_type):
                email_data = email_data.encode('utf-8')

            message = mailparser.parse_from_string(email_data)
        else:
            email_data = None
            message = None

        return (status, result, email_data, message)

    def _get_runner(self, action_db, entry_point):
        runner = LocalShellScriptRunner(uuid.uuid4().hex)
        runner.execution = MOCK_EXECUTION
        runner.action = action_db
        runner.action_name = action_db.name
        runner.liveaction_id = uuid.uuid4().hex
        runner.entry_point = entry_point
        runner.runner_parameters = {}
        runner.context = dict()
        runner.callback = dict()
        runner.libs_dir_path = None
        runner.auth_token = mock.Mock()
        runner.auth_token.token = 'mock-token'
        return runner
