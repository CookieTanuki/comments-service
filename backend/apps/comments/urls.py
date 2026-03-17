from django.urls import path
from .views import CommentReplyView, CommentListView, CommentPreviewView

urlpatterns = [
    path('', CommentListView.as_view(), name='comments'),
    path('<int:pk>/reply/', CommentReplyView.as_view(), name='comment-reply'),
    path('preview/', CommentPreviewView.as_view(), name='comment-preview'),
]
