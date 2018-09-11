# from haystack import indexes
#
# from core.user.models import UserProfile
#
#
# class UserIndex(indexes.SearchIndex, indexes.Indexable):
# text = indexes.CharField(document=True, use_template=False)
#     first_name = indexes.EdgeNgramField(model_attr='user__first_name')
#     last_name = indexes.EdgeNgramField(model_attr='user__last_name')
#     display_name = indexes.EdgeNgramField(model_attr='display_name', null=True)
#     gender = indexes.CharField(model_attr='gender')
#     handicap_36 = indexes.CharField(model_attr='handicap_36', null=True)
#     handicap_us = indexes.CharField(model_attr='handicap_us', null=True)
#     business_area = indexes.CharField(model_attr='business_area', null=True)
#     city = indexes.CharField(model_attr='city', null=True)
#     district = indexes.CharField(model_attr='district', null=True)
#     dob = indexes.DateField(model_attr='dob', null=True)
#
#     def get_model(self):
#         return UserProfile
#
#     def index_queryset(self, using=None):
#         return self.get_model().objects.all()
