import datetime

from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, FormParser
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from core.category.models import Category
from core.post.models import Post
from core.comment.models import Comment
from api.forumMana.serializers import ListPostSeri, NewPostSeri, NewCommentSeri, DetailPostSeri
from utils.django.models import get_or_none
from utils.rest.viewsets import CreateRetrieViewSet
from utils.rest.sendemail import send_email


class PostViewSet(CreateRetrieViewSet):
    queryset = Post.objects.all()
    serializer_class = NewPostSeri
    parser_classes = (JSONParser, FormParser,)

    def retrieve(self, request, pk=None):
        post = get_or_none(Post, id=pk)
        if post is None:
            return Response(status=404)
        serializer = DetailPostSeri(post)
        return Response(serializer.data, status=200)

    def create(self, request):
        self.permission_classes = (permissions.IsAuthenticated,)
        category_id = request.DATA.get('category_id', "''")
        if category_id == '':
            return Response({"details": "Some Field Is Missing"}, status=400)
        category = get_or_none(Category, pk=category_id)
        if category is None:
            return Response(status=404)
        ctype = ContentType.objects.get_for_model(category)
        data = {'user': request.user.id, 'content_type': ctype.id, 'object_id': category.id,
                'title': request.DATA['title'],
                'content': request.DATA['content']}
        new_post = NewPostSeri(data=data)

        if new_post.is_valid():
            new_post_post = new_post.save()
            html_content = str(
                request.user) + ' vừa đăng bài mới trên diễn đàn: https://golfconnect24.com/#/forum/post/' + str(
                new_post_post.id)
            html_content += ' Với nội dung :' + str(request.DATA['content'])
            # Send email
            send_email('Nội dung mới trên diễn đàn', html_content, ['support@golfconnect24.com'])
            return Response(new_post.data, status=200)
        return Response(new_post.errors, status=400)


class CommentViewSet(CreateRetrieViewSet):
    queryset = Post.objects.all()
    serializer_class = NewCommentSeri
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (permissions.IsAuthenticated,)

    def create(self, request):
        cmt_type = request.DATA.get('type', "''")
        obj_id = request.DATA.get('object_id', "''")
        cmt_content = request.DATA.get('content', "''")
        if cmt_type == '' or obj_id == '' or cmt_content == '':
            return Response({"details": "Missing Some Field"}, status=400)

        if cmt_type == "P":
            ctype = ContentType.objects.get_by_natural_key('post', 'post')
        else:
            ctype = ContentType.objects.get_by_natural_key('comment', 'comment')

        data = {'user': request.user.id, 'content_type': ctype.id, 'object_id': obj_id, 'content': cmt_content}
        new_post = NewCommentSeri(data=data)
        if not new_post.is_valid():
            return Response(new_post.errors, status=400)
        html_content = str(
            request.user) + ' vừa đăng bình luận mới trên diễn đàn: https://golfconnect24.com/#/forum/post/' + str(
            obj_id)
        html_content += ' Với nội dung :' + str(cmt_content)
        # Send email
        send_email('Nội dung mới trên diễn đàn', html_content, ['support@golfconnect24.com'])
        new_post.save()
        return Response(new_post.data, status=200)


class Forum(APIView):
    @staticmethod
    def get(request):
        category = Category.objects.filter(is_forum=True)
        if category.count() < 1:
            return Response({"details": "We don't have any category yet"}, status=404)
        category = list(sorted(category, key=lambda x: x.order))
        ctype = ContentType.objects.get_for_model(category[0])
        return_data = []
        for ite in category:
            query = Post.objects.filter(content_type=ctype.id, object_id=ite.id)
            query = list(sorted(query, key=lambda x: x.id, reverse=True))
            serializer = ListPostSeri(query, many=True)
            return_item = {'id': ite.id, 'name': ite.name, 'vi_name': ite.name_vi, 'post': serializer.data}
            return_data.append(return_item)
        return Response(return_data, status=200)


class Report(APIView):
    @staticmethod
    def get(request):
        # category = Category.objects.filter(is_forum=True)
        # if category.count() < 1:
        # return Response({"details": "We don't have any category yet"}, status=404)
        # ctype = ContentType.objects.get_for_model(category[0])
        # post_data = []
        # comment_data = []
        # comment_ctype = ContentType.objects.get_by_natural_key('comment', 'comment')
        # post_ctype = ContentType.objects.get_by_natural_key('post', 'post')
        # for ite in category:
        # post_query = Post.objects.filter(content_type=ctype.id, object_id=ite.id)

        #     for post_item in post_query:
        #         serializer = MiniPostSeri(post_item)
        #         post_data.append(serializer.data)

        #         comment_query = Comment.objects.filter(content_type=post_ctype.id, object_id=post_item.id)
        #         for cm_item in comment_query:
        #             serializer = MiniPostSeri(cm_item)
        #             comment_data.append(serializer.data)

        #             cmts = Comment.objects.filter(content_type=comment_ctype.id, object_id=cm_item.id)
        #             for cm_item2 in cmts:
        #                 serializer = MiniPostSeri(cm_item2)
        #                 comment_data.append(serializer.data)

        #                 cmts3 = Comment.objects.filter(content_type=comment_ctype.id, object_id=cm_item2.id)
        #                 for cm_item3 in cmts3:
        #                     serializer = MiniPostSeri(cm_item3)
        #                     comment_data.append(serializer.data)
        # comment_data_filter = list(filter(lambda x: x['user'] == 3, comment_data))
        # return Response(len(comment_data_filter), status=200)
        date = request.QUERY_PARAMS.get('date', '')
        to_date = request.QUERY_PARAMS.get('to_date', '')
        if date == '':
            date = '2014-12-31'
        if to_date == '':
            to_date = datetime.date.today()

        user_list = User.objects.filter(is_active=True)
        category = Category.objects.filter(is_forum=True)
        ctype = ContentType.objects.get_for_model(category[0])
        post_ctype = ContentType.objects.get_by_natural_key('post', 'post')
        comment_ctype = ContentType.objects.get_by_natural_key('comment', 'comment')
        return_data = []
        for iuser in user_list:
            user_post = 0
            user_comment = 0
            comment_query = Comment.objects.filter(content_type=comment_ctype.id,
                                                   user_id=iuser.id,
                                                   date_creation__gte=date,
                                                   date_creation__lte=to_date)
            user_comment += len(comment_query)
            for icate in category:
                post_query = Post.objects.filter(content_type=ctype.id,
                                                 object_id=icate.id,
                                                 user_id=iuser.id,
                                                 date_creation__gte=date,
                                                 date_creation__lte=to_date)
                user_post += len(post_query)
                all_post_query = Post.objects.filter(content_type=ctype.id,
                                                     object_id=icate.id,
                                                     date_creation__gte=date,
                                                     date_creation__lte=to_date)
                for icmt in all_post_query:
                    comment_query = Comment.objects.filter(content_type=post_ctype.id,
                                                           object_id=icmt.id,
                                                           user_id=iuser.id,
                                                           date_creation__gte=date,
                                                           date_creation__lte=to_date)
                    user_comment += len(comment_query)
            return_data.append({'id': iuser.id, 'user': iuser.username, 'post': user_post, 'comment': user_comment})
        return_data = sorted(return_data, key=lambda x: x['post'], reverse=True)
        return Response(return_data, status=200)