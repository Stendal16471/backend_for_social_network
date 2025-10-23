from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator


User = get_user_model()


class Post(models.Model):
    """
    Модель для хранения постов пользователей в социальной сети.

    Attributes:
        author (User): Автор поста (связь с пользователем)
        text (str): Текст поста, максимальная длина 2000 символов
        image (ImageField): Основное изображение поста
        created_at (datetime): Дата и время создания поста (автоматически)
        latitude (float): Географическая широта местоположения
        longitude (float): Географическая долгота местоположения
        location_name (str): Название местоположения для геокодинга

    Methods:
        __str__: Возвращает строковое представление поста

    Meta:
        ordering: Посты сортируются от новых к старым
    """
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posts'
    )
    text = models.TextField(max_length=2000, blank=True)
    image = models.ImageField(
        upload_to='posts/images/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    location_name = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Post {self.id} by {self.author.username}'


class PostImage(models.Model):
    """
    Модель для хранения дополнительных изображений поста.

    Позволяет прикреплять несколько изображений к одному посту.

    Attributes:
        post (Post): Связанный пост
        image (ImageField): Дополнительное изображение
        order (int): Порядок отображения изображений

    Meta:
        ordering: Изображения сортируются по порядку
    """
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(
        upload_to='posts/images/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'Image {self.id} for post {self.post.id}'


class Like(models.Model):
    """
    Модель для хранения реакций пользователей на посты.

    Поддерживает два типа реакций: лайк (like) и дизлайк (dislike).
    Один пользователь может иметь только одну реакцию на пост.

    Attributes:
        user (User): Пользователь, поставивший реакцию
        post (Post): Пост, на который поставлена реакция
        reaction (str): Тип реакции - 'like' или 'dislike'
        created_at (datetime): Дата и время создания реакции

    Class Attributes:
        LIKE: Константа для лайка
        DISLIKE: Константа для дизлайка
        REACTION_CHOICES: Доступные варианты реакций

    Meta:
        unique_together: Гарантирует уникальность реакции пользователя на пост
    """
    LIKE = 'like'
    DISLIKE = 'dislike'
    REACTION_CHOICES = [
        (LIKE, 'Like'),
        (DISLIKE, 'Dislike'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='likes'
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='likes'
    )
    reaction = models.CharField(
        max_length=7,
        choices=REACTION_CHOICES
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'post']

    def __str__(self):
        return f'{self.reaction} by {self.user.username} on post {self.post.id}'


class Comment(models.Model):
    """
    Модель для хранения комментариев к постам.

    Attributes:
        author (User): Автор комментария
        post (Post): Пост, к которому относится комментарий
        text (str): Текст комментария, максимальная длина 1000 символов
        created_at (datetime): Дата и время создания комментария

    Meta:
        ordering: Комментарии сортируются от старых к новым
    """
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    text = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.author.username} on post {self.post.id}'