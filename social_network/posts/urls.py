from django.urls import path
from . import views

urlpatterns = [
    path('posts/', views.PostListView.as_view(), name='post-list'),
    path('posts/<int:pk>/', views.PostDetailView.as_view(), name='post-detail'),
    path('posts/<int:post_id>/comments/', views.CommentCreateView.as_view(),
         name='comment-create'),
    path('posts/<int:post_id>/like/', views.toggle_like, name='toggle-like'),
    path('posts/<int:post_id>/stats/', views.post_stats, name='post-stats'),
]