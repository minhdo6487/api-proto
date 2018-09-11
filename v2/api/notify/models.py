from django.db import models

GENDER_CHOICES = (
    ('M', 'Male'),
    ('F', 'Female'),
    ('A', 'Another'),
    ('-', 'ALL'),
)


class Camp(models.Model):
    title = models.CharField(max_length=150)
    body = models.CharField(max_length=320)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='-')
    age_min = models.IntegerField(default=18)
    age_max = models.IntegerField(default=70)
    city_ids = models.CharField(max_length=320, default='')  # store list city id "1,2,3", parse it to array for query
    sent_at = models.DateTimeField(blank=True, null=True, default=None) # mark last sent time
    user_id = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '#{0} {1}'.format(self.id, self.title)


class Schedule(models.Model):
    camp = models.ForeignKey(Camp, related_name='camp_time')
    timed_at = models.DateTimeField()
    sent_at = models.DateTimeField(blank=True, null=True, default=None)


class CampLog(models.Model):
    schedule_id = models.PositiveIntegerField()
    user_id = models.PositiveIntegerField()
    sent_at = models.DateTimeField(auto_now_add=True, blank=True)
    title = models.CharField(max_length=150)
    body = models.CharField(max_length=320, default='')

