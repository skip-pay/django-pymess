import pytest

from pymess.backend.emails.mandrill import MandrillEmailBackend
from pymess.enums import EmailMessageState


class TestMandrillEmailBackend:
    @pytest.mark.parametrize('mandrill_state, info, expected_state', [
        ('sent', {}, EmailMessageState.SENT),
        ('queued', {}, EmailMessageState.SENDING),
        ('scheduled', {}, EmailMessageState.SENDING),
        ('rejected', {}, EmailMessageState.ERROR),
        ('invalid', {}, EmailMessageState.ERROR),
        ('bounced', {}, EmailMessageState.ERROR),
        ('soft-bounced', {}, EmailMessageState.ERROR),
        ('sent', {'opens': 1}, EmailMessageState.OPENED),
        ('sent', {'opens': [{}]}, EmailMessageState.OPENED),
        ('unknown_state', {}, None),
        (None, {}, None),
        (42, {}, None),
    ])
    def test_get_email_message_state_should_return_correct_state(self, mandrill_state, info, expected_state):
        assert MandrillEmailBackend.get_email_message_state(mandrill_state, info) == expected_state

    @pytest.mark.parametrize('mandrill_state', [
        'sent', 'queued', 'scheduled', 'rejected', 'invalid', 'bounced', 'soft-bounced',
    ])
    def test_get_email_message_state_should_return_opened_when_opens_regardless_of_state(self, mandrill_state):
        assert MandrillEmailBackend.get_email_message_state(mandrill_state, {'opens': 1}) == EmailMessageState.OPENED

    def test_get_email_message_state_should_not_return_opened_when_info_is_not_a_dict(self):
        assert MandrillEmailBackend.get_email_message_state('sent', None) == EmailMessageState.SENT
