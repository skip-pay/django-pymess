# -*- coding: utf-8 -*-
# Generated by Django 1.11.26 on 2020-03-09 18:50
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('pymess', '0016_migration'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dialermessage',
            name='state',
            field=models.IntegerField(
                choices=[(-1, 'waiting'), (0, 'not assigned'), (1, 'ready'), (2, 'rescheduled by dialer'),
                         (3, 'call in progress'), (4, 'hangup'), (5, 'done'), (6, 'rescheduled'),
                         (7, 'listened up complete message'), (8, 'listened up partial message'), (9, 'unreachable'),
                         (10, 'declined'), (11, 'unanswered'), (12, 'unanswered - hangup by dialer'),
                         (13, 'answered - hangup by customer'), (66, 'error message update'), (77, 'debug'),
                         (88, 'error message was not sent')], editable=False, verbose_name='state'),
        ),
        migrations.AlterField(
            model_name='emailmessage',
            name='state',
            field=models.IntegerField(
                choices=[(1, 'waiting'), (2, 'sending'), (3, 'sent'), (4, 'error message was not sent'), (5, 'debug')],
                editable=False, verbose_name='state'),
        ),
        migrations.AlterField(
            model_name='outputsmsmessage',
            name='state',
            field=models.IntegerField(
                choices=[(1, 'waiting'), (2, 'unknown'), (3, 'sending'), (4, 'sent'), (5, 'error message update'),
                         (6, 'debug'), (7, 'delivered'), (8, 'error message was not sent')], editable=False,
                verbose_name='state'),
        ),
        migrations.AlterField(
            model_name='pushnotificationmessage',
            name='state',
            field=models.PositiveIntegerField(
                choices=[(1, 'waiting'), (2, 'sent'), (3, 'error message was not sent'), (4, 'debug')], editable=False,
                verbose_name='state'),
        ),
    ]
