from django.urls import path
from .views import CommentReplyView, CommentListView

urlpatterns = [
    path('', CommentListView.as_view(), name='comments'),
    path('<int:pk>/reply/', CommentReplyView.as_view(), name='comment-reply'),

]
