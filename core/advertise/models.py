from django.db import models

LEFT1 = 'L1'
LEFT2 = 'L2'
LEFT3 = 'L3'
USER_FEED = 'UF'
POSITION_CHOICE = (
    (LEFT1, 'Left 1'),
    (LEFT2, 'Left 2'),
    (LEFT3, 'Left 3'),
    (USER_FEED, 'User Feed')
)


class Advertise(models.Model):
    from_date = models.DateTimeField()
    to_date = models.DateTimeField()
    notice_type = models.CharField(max_length=2, choices=POSITION_CHOICE, default=LEFT1)
    image = models.ImageField(upload_to='fixtures', max_length=140, blank=True, default='')
    link = models.TextField(max_length=200)