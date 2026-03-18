from django.urls import path
from .views import CommentReplyView, CommentListView, CommentPreviewView, CommentDeleteView

app_name = 'comments'

urlpatterns = [
    path('', CommentListView.as_view(), name='list'),
    path('<int:pk>/reply/', CommentReplyView.as_view(), name='comment-reply'),
    path('preview/', CommentPreviewView.as_view(), name='comment-preview'),
    path('<int:pk>/delete/', CommentDeleteView.as_view(), name='comment-delete'),
]
