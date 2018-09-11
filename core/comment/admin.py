from django.contrib import admin
import reversion

from core.comment.models import Comment


class CommentAdmin(reversion.VersionAdmin):
    pass


admin.site.register(Comment, CommentAdmin)