import hashlib
import hmac
import json
import logging

from base64 import b64encode

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from django.utils.decorators import method_decorator
from django.utils.timezone import now

from is_core.auth.permissions import AllowAny

from pymess.config import settings
from pymess.models import EmailMessage
from pymess.backend.emails.mandrill import MandrillState, MandrillEmailBackend

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class MandrillWebhookView(View):
    permission = AllowAny()

    def _verify_signature(self, request):
        if not (key := settings.MANDRILL_WEBHOOK_KEY):
            return True

        url = settings.MANDRILL_WEBHOOK_URL or request.build_absolute_uri()
        params = sorted(request.POST.items())
        signed_data = url + ''.join(k + v for k, v in params)
        digest = hmac.new(key.encode('utf-8'), signed_data.encode('utf-8'), hashlib.sha1).digest()

        return hmac.compare_digest(b64encode(digest).decode('utf-8'), request.headers.get('X-Mandrill-Signature', ''))

    def head(self, *args, **kwargs):
        return HttpResponse()

    def post(self, request, *args, **kwargs):
        if not self._verify_signature(request):
            logger.warning('Received invalid signature for Mandrill webhook')
            return HttpResponse(status=403)

        try:
            data = json.loads(request.POST.get('mandrill_events'))
        except TypeError:
            return HttpResponse(status=400)

        for event in data:
            try:
                self.process_event(event)
            except Exception as ex:  # pylint: disable=W0703
                logger.exception(ex)

        return HttpResponse()

    def process_event(self, event):
        external_id = event.get('_id')

        if not external_id or not (message := EmailMessage.objects.filter(external_id=external_id).first()):
            return

        state = message.state
        info_changed_at = message.info_changed_at
        extra_sender_data = message.extra_sender_data
        last_webhook_received_at = now()

        if info := event.get('msg', {}):
            extra_sender_data |= {'latest_event': info}

        if email_state := MandrillEmailBackend.get_email_message_state(info.get('state'), info):
            state = email_state
            # Having these variables to be the same means that pymess.management.commands.pull_emails_info.Command
            # would not try to update the message data later on
            info_changed_at = last_webhook_received_at

        message.change_and_save(
            state=state,
            info_changed_at=info_changed_at,
            last_webhook_received_at=last_webhook_received_at,
            extra_sender_data=extra_sender_data,
        )
