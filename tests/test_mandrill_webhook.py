import hashlib
import hmac
import pytest
import base64

from unittest.mock import patch

from django.test import RequestFactory

from pymess.enums import EmailMessageState
from pymess.models import EmailMessage
from pymess.webhooks.mandrill import MandrillWebhookView


@pytest.mark.django_db
class TestMandrillWebhookView:
    def setup_method(self):
        self.view = MandrillWebhookView()
        self.factory = RequestFactory()

    def _compute_signature(self, webhook_key, url, params):
        """
        Sample implementation from Mandrill.
        See https://mailchimp.com/developer/transactional/guides/track-respond-activity-webhooks/
        """
        signed_data = url

        for key, value in sorted(params.items()):
            signed_data += key
            signed_data += value

        return base64.b64encode(
            hmac.new(webhook_key, msg=signed_data.encode("utf-8"), digestmod=hashlib.sha1).digest()
        ).decode()

    def _create_email_message(self, **kwargs):
        defaults = dict(
            recipient='recipient@example.com',
            sender='sender@example.com',
            subject='Test Subject',
            content='Test Content',
            state=EmailMessageState.SENDING,
            external_id='test-external-id',
            extra_sender_data={},
        )
        defaults.update(kwargs)
        return EmailMessage.objects.create(**defaults)

    def test_verify_signature_should_return_true_when_no_key_configured(self):
        request = self.factory.post('/webhook/')

        with patch('pymess.webhooks.mandrill.settings') as mock_settings:
            mock_settings.MANDRILL_WEBHOOK_KEY = None
            assert self.view._verify_signature(request) is True

    def test_verify_signature_should_return_true_for_valid_signature(self):
        key = 'test-key'
        url = 'https://example.com/webhook/'
        post_data = {'mandrill_events': '[]'}
        signature = self._compute_signature(key.encode('utf-8'), url, post_data)
        request = self.factory.post('/webhook/', post_data, HTTP_X_MANDRILL_SIGNATURE=signature)

        with patch('pymess.webhooks.mandrill.settings') as mock_settings:
            mock_settings.MANDRILL_WEBHOOK_KEY = key
            mock_settings.MANDRILL_WEBHOOK_URL = url
            assert self.view._verify_signature(request) is True

    def test_verify_signature_should_return_false_for_invalid_signature(self):
        key = 'test-key'
        url = 'https://example.com/webhook/'
        post_data = {'mandrill_events': '[]'}
        request = self.factory.post('/webhook/', post_data, HTTP_X_MANDRILL_SIGNATURE='invalid-signature')

        with patch('pymess.webhooks.mandrill.settings') as mock_settings:
            mock_settings.MANDRILL_WEBHOOK_KEY = key
            mock_settings.MANDRILL_WEBHOOK_URL = url
            assert self.view._verify_signature(request) is False

    def test_verify_signature_should_use_request_absolute_uri_when_no_url_configured(self):
        key = 'test-key'
        post_data = {'mandrill_events': '[]'}
        request = self.factory.post('/webhook/', post_data)
        url = request.build_absolute_uri()
        signature = self._compute_signature(key.encode('utf-8'), url, post_data)
        request = self.factory.post('/webhook/', post_data, HTTP_X_MANDRILL_SIGNATURE=signature)

        with patch('pymess.webhooks.mandrill.settings') as mock_settings:
            mock_settings.MANDRILL_WEBHOOK_KEY = key
            mock_settings.MANDRILL_WEBHOOK_URL = None
            assert self.view._verify_signature(request) is True

    def test_process_event_should_do_nothing_for_unknown_external_id(self):
        message = self._create_email_message()
        self.view.process_event({'_id': 'unknown-id', 'msg': {'state': 'sent'}})
        message.refresh_from_db()
        assert message.state == EmailMessageState.SENDING

    @pytest.mark.parametrize('event_msg, expected_state', [
        ({'state': 'sent'}, EmailMessageState.SENT),
        ({'state': 'queued'}, EmailMessageState.SENDING),
        ({'state': 'scheduled'}, EmailMessageState.SENDING),
        ({'state': 'rejected'}, EmailMessageState.ERROR),
        ({'state': 'invalid'}, EmailMessageState.ERROR),
        ({'state': 'bounced'}, EmailMessageState.ERROR),
        ({'state': 'soft-bounced'}, EmailMessageState.ERROR),
        ({'state': 'sent', 'opens': [{}]}, EmailMessageState.OPENED),
        ({'state': 'unknown_state'}, EmailMessageState.SENDING),
        ({}, EmailMessageState.SENDING),
    ])
    def test_process_event_should_map_mandrill_state_to_email_message_state(self, event_msg, expected_state):
        message = self._create_email_message()
        self.view.process_event({'_id': 'test-external-id', 'msg': event_msg})
        message.refresh_from_db()
        assert message.state == expected_state

    def test_process_event_should_always_update_last_webhook_received_at(self):
        message = self._create_email_message()
        assert message.last_webhook_received_at is None
        self.view.process_event({'_id': 'test-external-id'})
        message.refresh_from_db()
        assert message.last_webhook_received_at is not None

    def test_process_event_should_set_info_changed_at_equal_to_last_webhook_received_at_when_state_changes(self):
        message = self._create_email_message()
        self.view.process_event({'_id': 'test-external-id', 'msg': {'state': 'sent'}})
        message.refresh_from_db()
        assert message.info_changed_at == message.last_webhook_received_at

    def test_process_event_should_not_change_info_changed_at_when_state_does_not_change(self):
        message = self._create_email_message(info_changed_at=None)
        self.view.process_event({'_id': 'test-external-id', 'msg': {'state': 'unknown_state'}})
        message.refresh_from_db()
        assert message.info_changed_at is None

    def test_process_event_should_store_msg_in_extra_sender_data_and_preserve_existing_data(self):
        message = self._create_email_message(extra_sender_data={'result': {'status': 'sent'}})
        msg = {'state': 'sent', 'subject': 'Hello'}
        self.view.process_event({'_id': 'test-external-id', 'msg': msg})
        message.refresh_from_db()
        assert message.extra_sender_data['latest_event'] == msg
        assert message.extra_sender_data['result'] == {'status': 'sent'}

    def test_process_event_should_keep_current_state_and_not_add_latest_event_when_no_msg_key(self):
        message = self._create_email_message()
        self.view.process_event({'_id': 'test-external-id'})
        message.refresh_from_db()
        assert message.state == EmailMessageState.SENDING
        assert 'latest_event' not in message.extra_sender_data
