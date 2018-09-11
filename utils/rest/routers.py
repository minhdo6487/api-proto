from rest_framework.routers import Route, SimpleRouter, DefaultRouter

# Router for only get and update
# Without pk
# Used specially for current user (profile)


class GetAndUpdateRouter(SimpleRouter):
    """
        Router for get and update only
    """
    routes = [
        Route(url=r'^{prefix}{trailing_slash}$',
              mapping={
                  'get': 'retrieve',
                  'put': 'update',
                  'patch': 'partial_update',
              },
              name='{basename}-detail',
              initkwargs={'suffix': 'Detail'})
    ]
class CreateRouter(SimpleRouter):
    """
        Router for get and update only
    """
    routes = [
        Route(url=r'^{prefix}{trailing_slash}$',
              mapping={
                  'post': 'create',
              },
              name='{basename}-detail',
              initkwargs={'suffix': 'Detail'})
    ]

class FriendRequestRouter(SimpleRouter):
    """
        Router for friend request view
    """
    routes = [
        Route(
            url=r'^{prefix}{trailing_slash}$',
            mapping={
                'get': 'list',
            },
            name='{basename}-list',
            initkwargs={'suffix': 'Detail'}
        ),
        Route(
            url=r'^{prefix}/connect/{lookup}{trailing_slash}$',
            mapping={
                'post': 'connect',
            },
            name='{basename}-connect',
            initkwargs={}
        ),
        Route(
            url=r'^{prefix}/accept/{lookup}{trailing_slash}$',
            mapping={
                'post': 'accept',
            },
            name='{basename}-accept',
            initkwargs={}
        ),
        Route(
            url=r'^{prefix}/reject/{lookup}{trailing_slash}$',
            mapping={
                'post': 'reject',
            },
            name='{basename}-reject',
            initkwargs={}
        ),
        Route(
            url=r'^{prefix}/cancel/{lookup}{trailing_slash}$',
            mapping={
                'post': 'cancel',
            },
            name='{basename}-cancel',
            initkwargs={}
        ),
    ]


class FriendConnectRouter(SimpleRouter):
    """
        Router for friend connect view
    """
    routes = [
        Route(
            url=r'^{prefix}{trailing_slash}$',
            mapping={
                'get': 'list',
            },
            name='{basename}-list',
            initkwargs={'suffix': 'Detail'}
        ),
        Route(
            url=r'^{prefix}/unfriend/{lookup}{trailing_slash}$',
            mapping={
                'post': 'unfriend',
            },
            name='{basename}-unfriend',
            initkwargs={}
        ),
    ]
class GroupchatRouter(DefaultRouter):
    routes = [
        # List route.
        Route(
            url=r'^{prefix}{trailing_slash}$',
            mapping={
                'get': 'list',
                'post': 'create'
            },
            name='{basename}-list',
            initkwargs={'suffix': 'List'}
        ),
        # Detail route.
        Route(
            url=r'^{prefix}/{lookup}{trailing_slash}$',
            mapping={
                'get': 'retrieve',
                'post': 'update',
                'patch': 'partial_update',
                'delete': 'destroy'
            },
            name='{basename}-detail',
            initkwargs={'suffix': 'Instance'}
        ),
        # Dynamically generated routes.
        # Generated using @action or @link decorators on methods of the viewset.
        Route(
            url=r'^{prefix}/{lookup}/{methodname}{trailing_slash}$',
            mapping={
                '{httpmethod}': '{methodname}',
            },
            name='{basename}-{methodnamehyphen}',
            initkwargs={}
        ),
    ]