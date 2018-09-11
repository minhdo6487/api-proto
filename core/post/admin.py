from django.contrib import admin
import reversion

from core.post.models import Post


class PostAdmin(reversion.VersionAdmin):
    pass


admin.site.register(Post, PostAdmin)