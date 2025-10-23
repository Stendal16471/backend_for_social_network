from django.contrib import admin
from .models import Post, PostImage, Like, Comment


class PostImageInline(admin.TabularInline):
    model = PostImage
    extra = 1


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['id', 'author', 'created_at', 'location_name']
    list_filter = ['created_at', 'author']
    search_fields = ['text', 'author__username']
    inlines = [PostImageInline, CommentInline]


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'post', 'reaction', 'created_at']
    list_filter = ['reaction', 'created_at']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'author', 'post', 'created_at']
    list_filter = ['created_at']
    search_fields = ['text', 'author__username']
