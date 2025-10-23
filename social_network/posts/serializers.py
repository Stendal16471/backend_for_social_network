from rest_framework import serializers
from .models import Post, PostImage, Like, Comment
from django.contrib.auth import get_user_model

User = get_user_model()


class CommentAuthorSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отображения информации об авторе комментария.

    Fields:
    - id: ID пользователя
    - username: Имя пользователя
    - first_name: Имя
    - last_name: Фамилия
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']


class CommentSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Comment.

    Includes:
    - author: Вложенная информация об авторе
    - text: Текст комментария
    - created_at: Дата создания

    Fields:
    - id: ID комментария
    - author: Информация об авторе (read-only)
    - text: Текст комментария
    - created_at: Дата создания (read-only)
    """
    author = CommentAuthorSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'author', 'text', 'created_at']
        read_only_fields = ['id', 'author', 'created_at']


class PostImageSerializer(serializers.ModelSerializer):
    """
    Сериализатор для дополнительных изображений поста.

    Fields:
    - id: ID изображения
    - image: URL изображения
    - order: Порядок отображения
    """
    class Meta:
        model = PostImage
        fields = ['id', 'image', 'order']


class LikeSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Like.

    Fields:
    - id: ID реакции
    - user: Имя пользователя (read-only)
    - post: ID поста
    - reaction: Тип реакции
    - created_at: Дата создания (read-only)
    """
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Like
        fields = ['id', 'user', 'post', 'reaction', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class PostSerializer(serializers.ModelSerializer):
    """
    Основной сериализатор для модели Post.

    Includes:
    - author: Имя автора поста
    - comments: Список комментариев с авторами
    - images: Список дополнительных изображений
    - likes_count: Количество лайков (вычисляемое поле)
    - dislikes_count: Количество дизлайков (вычисляемое поле)
    - user_reaction: Реакция текущего пользователя (вычисляемое поле)

    Computed Fields:
    - likes_count: Количество лайков к посту
    - dislikes_count: Количество дизлайков к посту
    - user_reaction: Реакция текущего пользователя (like/dislike/null)
    """
    author = serializers.StringRelatedField(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    images = PostImageSerializer(many=True, read_only=True)
    likes_count = serializers.SerializerMethodField()
    dislikes_count = serializers.SerializerMethodField()
    user_reaction = serializers.SerializerMethodField()

    image = serializers.ImageField(read_only=True)

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'text', 'image', 'images', 'created_at',
            'comments', 'likes_count', 'dislikes_count', 'user_reaction',
            'latitude', 'longitude', 'location_name'
        ]
        read_only_fields = ['id', 'author', 'created_at']

    def get_likes_count(self, obj):
        """Возвращает количество лайков для поста."""
        return obj.likes.filter(reaction=Like.LIKE).count()

    def get_dislikes_count(self, obj):
        """Возвращает количество дизлайков для поста."""
        return obj.likes.filter(reaction=Like.DISLIKE).count()

    def get_user_reaction(self, obj):
        """
        Возвращает реакцию текущего пользователя на пост.

        Args:
            obj: Объект поста

        Returns:
            str|null: 'like', 'dislike' или None, если реакции нет
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                like = obj.likes.get(user=request.user)
                return like.reaction
            except Like.DoesNotExist:
                return None
        return None


class PostCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания постов с поддержкой загрузки изображений.

    Supports:
    - Основное изображение (image)
    - Множественные дополнительные изображения (images)
    - Текст поста
    - Геолокация

    Fields:
    - text: Текст поста
    - image: Основное изображение (optional)
    - images: Список дополнительных изображений (optional)
    - location_name: Название местоположения (optional)

    Validation:
    - images: Максимум 10 изображений
    - image: Поддерживаются форматы jpg, jpeg, png
    """
    images = serializers.ListField(
        child=serializers.ImageField(max_length=100000,
                                     allow_empty_file=False,
                                     use_url=False),
        write_only=True,
        required=False,
        max_length=10
    )
    image = serializers.ImageField(required=False)

    class Meta:
        model = Post
        fields = ['text', 'image', 'images', 'location_name']

    def create(self, validated_data):
        """
        Создает пост и связанные изображения.

        Args:
            validated_data: Валидированные данные поста

        Returns:
            Post: Созданный объект поста
        """
        images_data = validated_data.pop('images', [])
        main_image = validated_data.pop('image', None)

        post = Post.objects.create(**validated_data)

        if main_image:
            post.image = main_image
            post.save()

        for i, image_data in enumerate(images_data):
            PostImage.objects.create(post=post, image=image_data, order=i)

        return post