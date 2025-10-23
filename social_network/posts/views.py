from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from .models import Post, Like, Comment
from .serializers import (
    PostSerializer, PostCreateSerializer,
    LikeSerializer, CommentSerializer
)
from .utils import get_geolocation


class PostListView(generics.ListCreateAPIView):
    """
    API endpoint для получения списка постов и создания новых постов.

    GET:
    Возвращает пагинированный список всех постов в системе.
    Доступен без аутентификации.

    POST:
    Создает новый пост. Требуется аутентификация пользователя.
    Автоматически определяет геолокацию, если указано местоположение.

    Request Body (multipart/form-data):
    - text: string (required) - Текст поста
    - image: file (optional) - Основное изображение поста
    - images: array of files (optional) - Дополнительные изображения
    - location_name: string (optional) - Название местоположения для геокодинга

    Responses:
    - 200 OK: Успешное получение списка постов
    - 201 Created: Пост успешно создан
    - 400 Bad Request: Неверные данные запроса
    - 403 Forbidden: Пользователь не аутентифицирован

    Permissions:
    - IsAuthenticatedOrReadOnly: Чтение доступно всем,
    создание - только аутентифицированным
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        """Выбирает сериализатор в зависимости от метода запроса."""
        if self.request.method == 'POST':
            return PostCreateSerializer
        return PostSerializer

    def get_queryset(self):
        """Возвращает QuerySet постов с предзагрузкой связанных объектов."""
        return Post.objects.prefetch_related('images', 'comments', 'likes').all()

    def perform_create(self, serializer):
        """
        Сохраняет пост и обрабатывает геолокацию.

        Args:
            serializer: Сериализатор с валидированными данными поста
        """
        post = serializer.save(author=self.request.user)

        if post.location_name:
            try:
                geolocation_data = get_geolocation(post.location_name)
                if geolocation_data:
                    post.latitude = geolocation_data['latitude']
                    post.longitude = geolocation_data['longitude']
                    post.save()
            except Exception as e:
                print(f"Geocoding error: {e}")


class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint для получения, обновления и удаления конкретного поста.

    GET:
    Возвращает детальную информацию о посте, включая комментарии и статистику.

    PUT/PATCH:
    Обновляет пост. Доступно только автору поста.

    DELETE:
    Удаляет пост. Доступно только автору поста.

    Path Parameters:
    - pk: int (required) - ID поста

    Responses:
    - 200 OK: Успешное получение/обновление поста
    - 204 No Content: Пост успешно удален
    - 403 Forbidden: Пользователь - не автор поста
    - 404 Not Found: Пост не найден

    Permissions:
    - IsAuthenticatedOrReadOnly: Чтение доступно всем,
    изменение - только аутентифицированным
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    serializer_class = PostSerializer
    queryset = Post.objects.prefetch_related('images', 'comments', 'likes').all()

    def get_serializer_context(self):
        """Добавляет request в контекст сериализатора."""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_update(self, serializer):
        """
        Проверяет права доступа перед обновлением поста.

        Args:
            serializer: Сериализатор с валидированными данными

        Raises:
            PermissionDenied: Если пользователь не автор поста
        """
        instance = self.get_object()
        if instance.author != self.request.user:
            raise PermissionDenied("Вы можете редактировать только свои публикации")
        serializer.save()

    def perform_destroy(self, instance):
        """
        Проверяет права доступа перед удалением поста.

        Args:
            instance: Объект поста для удаления

        Raises:
            PermissionDenied: Если пользователь не автор поста
        """
        if instance.author != self.request.user:
            raise PermissionDenied("Вы можете удалять только свои публикации")
        instance.delete()


class CommentCreateView(generics.CreateAPIView):
    """
    API endpoint для создания комментариев к постам.

    POST:
    Создает новый комментарий к указанному посту.

    Path Parameters:
    - post_id: int (required) - ID поста для комментария

    Request Body (JSON):
    - text: string (required) - Текст комментария

    Responses:
    - 201 Created: Комментарий успешно создан
    - 400 Bad Request: Неверные данные комментария
    - 403 Forbidden: Пользователь не аутентифицирован
    - 404 Not Found: Пост не найден

    Permissions:
    - IsAuthenticated: Только аутентифицированные пользователи
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CommentSerializer

    def perform_create(self, serializer):
        """
        Сохраняет комментарий с привязкой к посту и пользователю.

        Args:
            serializer: Сериализатор с валидированными данными комментария
        """
        post = get_object_or_404(Post, id=self.kwargs['post_id'])
        serializer.save(author=self.request.user, post=post)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def toggle_like(request, post_id):
    """
    API endpoint для управления реакциями (лайки/дизлайки) на посты.

    POST:
    Добавляет, изменяет или удаляет реакцию пользователя на пост.

    Business Logic:
    - Если реакции нет - создается новая
    - Если реакция такая же - удаляется
    - Если реакция другая - изменяется

    Path Parameters:
    - post_id: int (required) - ID поста

    Request Body (JSON):
    - reaction: string (required) - Тип реакции: 'like' или 'dislike'

    Responses:
    - 200 OK: Реакция успешно обработана
    - 400 Bad Request: Неверный тип реакции
    - 403 Forbidden: Пользователь не аутентифицирован
    - 404 Not Found: Пост не найден
    """
    post = get_object_or_404(Post, id=post_id)
    reaction = request.data.get('reaction', Like.LIKE)

    if reaction not in [Like.LIKE, Like.DISLIKE]:
        return Response(
            {'error': 'Неверная реакция. Используйте "like" или "dislike".'},
            status=status.HTTP_400_BAD_REQUEST
        )

    like, created = Like.objects.get_or_create(
        user=request.user,
        post=post,
        defaults={'reaction': reaction}
    )

    if not created:
        if like.reaction == reaction:
            like.delete()
            return Response({'status': 'reaction removed'})
        else:
            like.reaction = reaction
            like.save()

    serializer = LikeSerializer(like)
    return Response(serializer.data)


@api_view(['GET'])
def post_stats(request, post_id):
    """
    API endpoint для получения статистики поста.

    GET:
    Возвращает количество лайков, дизлайков и комментариев к посту.

    Path Parameters:
    - post_id: int (required) - ID поста

    Responses:
    - 200 OK: Статистика успешно получена
    - 404 Not Found: Пост не найден

    Statistics:
    - likes_count: Количество лайков
    - dislikes_count: Количество дизлайков
    - comments_count: Количество комментариев
    - total_reactions: Общее количество реакций
    """
    post = get_object_or_404(Post, id=post_id)

    stats = {
        'likes_count': post.likes.filter(reaction=Like.LIKE).count(),
        'dislikes_count': post.likes.filter(reaction=Like.DISLIKE).count(),
        'comments_count': post.comments.count(),
        'total_reactions': post.likes.count()
    }

    return Response(stats)