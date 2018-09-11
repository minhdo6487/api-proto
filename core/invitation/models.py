import logging
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from core.realtime.models import UserSubcribe

ACCEPT = 'A'
CANCEL = 'C'
PENDING = 'P'
TYPE_CHOICES = (
    (ACCEPT, 'Accept'),
    (CANCEL, 'Cancel'),
    (PENDING, 'Pending')
)


# class Invitation(models.Model):
#     user = models.ForeignKey(User, null=True, blank=True)
#     date = models.DateField()
#     time = models.TimeField(null=True, blank=True)
#     description = models.TextField(null=True, blank=True)
#     golfcourse = models.TextField(max_length=1000, db_index=True)
#
#     is_publish = models.BooleanField(default=False)
#     is_show = models.BooleanField(default=True)
#     from_hdcp = models.PositiveIntegerField(blank=True, null=True)
#     to_hdcp = models.PositiveIntegerField(blank=True, null=True)
#
#     content_type = models.ForeignKey(ContentType, blank=True, null=True)
#     object_id = models.PositiveIntegerField(blank=True, null=True)
#     related_object = generic.GenericForeignKey('content_type', 'object_id')
#
#     def __str__(self):
#         return self.golfcourse
#
#     class Meta:
#         ordering = ('-date',)
#
#
# def push_owner_to_subcribe(sender, instance, created, **kwargs):
#     if created:
#         INVITE_CTYPE = ContentType.objects.get_for_model(Invitation)
#         UserSubcribe.objects.create(content_type=INVITE_CTYPE, object_id=instance.id,user=[instance.user_id])
#
# post_save.connect(push_owner_to_subcribe, sender=Invitation)
#
# class InvitedPeople(models.Model):
#     invitation = models.ForeignKey(Invitation, related_name='invited_people')
#     status = models.CharField(max_length=2, choices=TYPE_CHOICES, default=PENDING)
#     content_type = models.ForeignKey(ContentType, blank=True, null=True)
#     object_id = models.PositiveIntegerField(blank=True, null=True)
#     player = generic.GenericForeignKey('content_type', 'object_id')
#
# def push_invited_player_to_subcribe(sender, instance, created, **kwargs):
#     if created and isinstance(instance.player, User):
#         INVITE_CTYPE = ContentType.objects.get_for_model(Invitation)
#         user_subcribe = UserSubcribe.objects.get(content_type=INVITE_CTYPE, object_id=instance.invitation_id)
#         subcribe_list = eval(user_subcribe.user)
#         if instance.object_id not in subcribe_list:
#             subcribe_list.append(instance.object_id)
#             user_subcribe.user = subcribe_list
#             user_subcribe.save(update_fields=['user'])
#
# post_save.connect(push_invited_player_to_subcribe, sender=InvitedPeople)

    

