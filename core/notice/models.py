from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.utils import timezone


from core.user.models import UserSetting
from utils.rest.sendemail import send_email


NOTIFICATION_TYPE_CHOICES = (
    ('I', 'Invitation'),
    ('B', 'Booking'),
    ('IA', 'Invite Accept'),
    ('IC', 'Invite Cancel'),
    ('IN', 'Inform')
)


class Notice(models.Model):
    from_user = models.ForeignKey(User, related_name='notifications_sent',
                                  blank=True, null=True)
    to_user = models.ForeignKey(User, related_name='notifications_received')
    notice_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPE_CHOICES, db_index=True)
    date_create = models.DateTimeField()
    date_modify = models.DateTimeField()
    date_read = models.DateTimeField(null=True, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    is_show = models.BooleanField(default=False, db_index=True)
    detail = models.CharField(max_length=1000, blank=True)
    detail_en = models.CharField(max_length=1000, blank=True, null=True)
    send_email = models.BooleanField(default=True)
    content_type = models.ForeignKey(ContentType, blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    related_object = generic.GenericForeignKey('content_type', 'object_id')

    def save(self, *args, **kwargs):
        """
        custom save method to send email and push notification
        """
        if not self.id:
            self.date_create = timezone.now()
        self.date_modify = timezone.now()
        return super(Notice, self).save(*args, **kwargs)

    class Meta:
        ordering = ('-id',)


def send_email_to_user(sender, instance, created, **kwargs):
    if not UserSetting.objects.filter(user=instance.to_user).exists():
        UserSetting.objects.create(user=instance.to_user)
    if created and instance.to_user.usersettings.receive_email_notification and instance.send_email:
        subject = 'Notification'
        detail_html = '<b>Hi,</b><br><br>'
        detail_html += instance.detail_en
        detail_html += '<br><br><br><b>Chào bạn,</b><br><br>'
        detail_html += instance.detail
        email = instance.to_user.email
        send_email(subject, detail_html, [email])


post_save.connect(send_email_to_user, sender=Notice)
