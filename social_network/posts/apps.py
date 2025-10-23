from django.apps import AppConfig


class PostsConfig(AppConfig):
    """
    Конфигурация приложения Posts.

    Attributes:
        default_auto_field: Тип поля для автоматических primary keys
        name: Имя приложения
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'posts'
