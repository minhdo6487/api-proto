from haystack import indexes

from core.user.models import UserProfile


class NoteIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=False)
    username = indexes.EdgeNgramField(model_attr='user__username')
    email = indexes.CharField(model_attr='user__email')
    display_name = indexes.CharField(model_attr='display_name', null=True)
    pic = indexes.CharField(model_attr='profile_picture', null=True)
    mobile = indexes.CharField(model_attr='mobile', null=True)

    def get_model(self):
        return UserProfile

    def index_queryset(self, using=None):
        return self.get_model().objects.all()