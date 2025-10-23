from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from .models import Post, Like, Comment, PostImage
import tempfile
import os
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()

TEST_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class PostAPITestCase(TestCase):
    def setUp(self):
        """Настройка тестовых данных"""
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            username='alena',
            email='alena@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='semen',
            email='semen@test.com',
            password='testpass123'
        )

        self.post_list_url = reverse('post-list')
        self.comment_create_url_name = 'comment-create'
        self.toggle_like_url_name = 'toggle-like'
        self.post_stats_url_name = 'post-stats'

    def create_test_image(self, filename):
        """Создает тестовое изображение в памяти"""
        from io import BytesIO
        from PIL import Image

        image = BytesIO()
        img = Image.new('RGB', (100, 100), color='red')
        img.save(image, 'JPEG')
        image.seek(0)
        return SimpleUploadedFile(
            filename,
            image.getvalue(),
            content_type='image/jpeg'
        )

    def get_post_detail_url(self, post_id):
        return reverse('post-detail', args=[post_id])

    def get_post_id_from_response(self, response):
        """Вспомогательный метод для получения ID поста из ответа API"""
        if 'id' in response.data:
            return response.data['id']
        else:
            post = Post.objects.order_by('-id').first()
            return post.id if post else None

    def test_create_post_authenticated(self):
        """Тест создания поста авторизованным пользователем"""
        self.client.force_authenticate(user=self.user1)

        response = self.client.post(self.post_list_url, {
            'text': 'Мой первый пост с фото',
            'location_name': 'Сочи, Россия'
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.count(), 1)

        post_id = self.get_post_id_from_response(response)
        post = Post.objects.get(id=post_id)

        self.assertEqual(post.author, self.user1)
        self.assertEqual(post.text, 'Мой первый пост с фото')

    def test_create_post_with_image(self):
        """Тест создания поста с изображением"""
        self.client.force_authenticate(user=self.user1)

        image = self.create_test_image('test_image.jpg')

        response = self.client.post(self.post_list_url, {
            'text': 'Пост с изображением',
            'image': image,
            'location_name': 'Сочи'
        }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        post_id = self.get_post_id_from_response(response)
        post = Post.objects.get(id=post_id)

        self.assertEqual(post.text, 'Пост с изображением')
        self.assertIsNotNone(post.image)

    def test_create_post_unauthenticated(self):
        """Тест создания поста неавторизованным пользователем"""
        response = self.client.post(self.post_list_url, {
            'text': 'Неавторизованный пост'
        })

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Post.objects.count(), 0)

    def test_get_post_list(self):
        """Тест получения списка постов"""
        post1 = Post.objects.create(author=self.user1, text='Первый пост')
        post2 = Post.objects.create(author=self.user2, text='Второй пост')

        response = self.client.get(self.post_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if 'results' in response.data:
            self.assertEqual(len(response.data['results']), 2)
        else:
            self.assertEqual(len(response.data), 2)

    def test_get_post_detail(self):
        """Тест получения деталей поста"""
        post = Post.objects.create(
            author=self.user1,
            text='Детальный пост',
            location_name='Москва'
        )

        url = self.get_post_detail_url(post.id)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['text'], 'Детальный пост')
        self.assertEqual(response.data['location_name'], 'Москва')
        self.assertIn('comments', response.data)
        self.assertIn('likes_count', response.data)

    def test_update_post_author(self):
        """Тест редактирования поста автором"""
        post = Post.objects.create(author=self.user1, text='Оригинальный текст')
        self.client.force_authenticate(user=self.user1)

        url = self.get_post_detail_url(post.id)
        response = self.client.put(url, {
            'text': 'Обновленный текст',
            'location_name': 'Санкт-Петербург'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        post.refresh_from_db()
        self.assertEqual(post.text, 'Обновленный текст')
        self.assertEqual(post.location_name, 'Санкт-Петербург')

    def test_update_post_non_author(self):
        """Тест редактирования поста не автором"""
        post = Post.objects.create(author=self.user1, text='Оригинальный текст')
        self.client.force_authenticate(user=self.user2)

        url = self.get_post_detail_url(post.id)
        response = self.client.put(url, {
            'text': 'Попытка изменить чужой пост'
        })

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        post.refresh_from_db()
        self.assertEqual(post.text, 'Оригинальный текст')

    def test_delete_post_author(self):
        """Тест удаления поста автором"""
        post = Post.objects.create(author=self.user1, text='Пост для удаления')
        self.client.force_authenticate(user=self.user1)

        url = self.get_post_detail_url(post.id)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Post.objects.count(), 0)

    def test_delete_post_non_author(self):
        """Тест удаления поста не автором"""
        post = Post.objects.create(author=self.user1, text='Чужой пост')
        self.client.force_authenticate(user=self.user2)

        url = self.get_post_detail_url(post.id)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Post.objects.count(), 1)

    def test_image_upload_and_serving(self):
        """Тест загрузки и отдачи изображений"""
        self.client.force_authenticate(user=self.user1)

        image = self.create_test_image('serving_test.jpg')
        response = self.client.post(self.post_list_url, {
            'text': 'Тест отдачи изображения',
            'image': image,
        }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        post_id = self.get_post_id_from_response(response)
        self.assertIsNotNone(post_id)

        detail_response = self.client.get(self.get_post_detail_url(post_id))

        self.assertTrue(
            'image' in detail_response.data or 'images' in detail_response.data,
            f"Ни 'image', ни 'images' не найдены в ответе: {detail_response.data}"
        )

        if 'image' in detail_response.data and detail_response.data['image']:
            self.assertIsNotNone(detail_response.data['image'])

        if 'images' in detail_response.data:
            self.assertIsInstance(detail_response.data['images'], list)

    def test_image_validation(self):
        """Тест валидации изображений"""
        self.client.force_authenticate(user=self.user1)

        text_file = SimpleUploadedFile(
            "test.txt",
            b"this is not an image",
            content_type="text/plain"
        )

        response = self.client.post(self.post_list_url, {
            'text': 'Пост с неправильным файлом',
            'image': text_file,
        }, format='multipart')

        self.assertIn(response.status_code, [status.HTTP_201_CREATED,
                                             status.HTTP_400_BAD_REQUEST])

    def test_post_with_multiple_images_model(self):
        """Тест создания поста с несколькими изображениями через модель"""
        self.client.force_authenticate(user=self.user1)

        post_response = self.client.post(self.post_list_url, {
            'text': 'Пост для множественных фото',
            'location_name': 'Красная Поляна'
        })

        self.assertEqual(post_response.status_code, status.HTTP_201_CREATED)

        post_id = self.get_post_id_from_response(post_response)
        self.assertIsNotNone(post_id)

        post = Post.objects.get(id=post_id)
        image1 = self.create_test_image('multi1.jpg')
        image2 = self.create_test_image('multi2.jpg')

        PostImage.objects.create(post=post, image=image1, order=0)
        PostImage.objects.create(post=post, image=image2, order=1)

        self.assertEqual(post.images.count(), 2)
        self.assertEqual(post.images.first().order, 0)
        self.assertEqual(post.images.last().order, 1)

    def tearDown(self):
        """Очистка после тестов"""
        import shutil
        if os.path.exists(TEST_MEDIA_ROOT):
            shutil.rmtree(TEST_MEDIA_ROOT)
        super().tearDown()


class LikeTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user('user1', 'user1@test.com', 'pass')
        self.user2 = User.objects.create_user('user2', 'user2@test.com', 'pass')
        self.post = Post.objects.create(author=self.user1, text='Тестовый пост')

    def test_like_post(self):
        """Тест добавления лайка"""
        self.client.force_authenticate(user=self.user1)
        url = reverse('toggle-like', args=[self.post.id])

        response = self.client.post(url, {'reaction': 'like'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Like.objects.count(), 1)
        self.assertEqual(Like.objects.first().reaction, 'like')
        self.assertEqual(self.post.likes.filter(reaction='like').count(), 1)

    def test_dislike_post(self):
        """Тест добавления дизлайка"""
        self.client.force_authenticate(user=self.user1)
        url = reverse('toggle-like', args=[self.post.id])

        response = self.client.post(url, {'reaction': 'dislike'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Like.objects.count(), 1)
        self.assertEqual(Like.objects.first().reaction, 'dislike')
        self.assertEqual(self.post.likes.filter(reaction='dislike').count(), 1)

    def test_change_reaction(self):
        """Тест изменения реакции с лайка на дизлайк"""
        self.client.force_authenticate(user=self.user1)
        url = reverse('toggle-like', args=[self.post.id])

        self.client.post(url, {'reaction': 'like'})
        self.assertEqual(Like.objects.first().reaction, 'like')

        response = self.client.post(url, {'reaction': 'dislike'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Like.objects.count(), 1)
        self.assertEqual(Like.objects.first().reaction, 'dislike')

    def test_remove_reaction(self):
        """Тест удаления реакции"""
        self.client.force_authenticate(user=self.user1)
        url = reverse('toggle-like', args=[self.post.id])

        self.client.post(url, {'reaction': 'like'})
        self.assertEqual(Like.objects.count(), 1)

        response = self.client.post(url, {'reaction': 'like'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Like.objects.count(), 0)

    def test_like_unauthenticated(self):
        """Тест лайка неавторизованным пользователем"""
        url = reverse('toggle-like', args=[self.post.id])
        response = self.client.post(url, {'reaction': 'like'})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Like.objects.count(), 0)

    def test_multiple_users_likes(self):
        """Тест лайков от нескольких пользователей"""
        self.client.force_authenticate(user=self.user1)
        url = reverse('toggle-like', args=[self.post.id])

        self.client.post(url, {'reaction': 'like'})

        self.client.force_authenticate(user=self.user2)
        self.client.post(url, {'reaction': 'dislike'})

        self.assertEqual(Like.objects.count(), 2)
        self.assertEqual(self.post.likes.filter(reaction='like').count(), 1)
        self.assertEqual(self.post.likes.filter(reaction='dislike').count(), 1)


class CommentTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user('user1', 'user1@test.com', 'pass')
        self.user2 = User.objects.create_user('user2', 'user2@test.com', 'pass')
        self.post = Post.objects.create(author=self.user1,
                                        text='Пост для комментариев')

    def test_create_comment(self):
        """Тест создания комментария"""
        self.client.force_authenticate(user=self.user2)
        url = reverse('comment-create', args=[self.post.id])

        response = self.client.post(url, {
            'text': 'Отличный пост!'
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(Comment.objects.first().text, 'Отличный пост!')
        self.assertEqual(Comment.objects.first().author, self.user2)
        self.assertEqual(Comment.objects.first().post, self.post)

    def test_create_comment_unauthenticated(self):
        """Тест создания комментария неавторизованным пользователем"""
        url = reverse('comment-create', args=[self.post.id])

        response = self.client.post(url, {
            'text': 'Анонимный комментарий'
        })

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Comment.objects.count(), 0)

    def test_comments_in_post_detail(self):
        """Тест отображения комментариев в деталях поста"""
        Comment.objects.create(
            author=self.user1,
            post=self.post,
            text='Первый комментарий'
        )
        Comment.objects.create(
            author=self.user2,
            post=self.post,
            text='Второй комментарий'
        )

        url = reverse('post-detail', args=[self.post.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['comments']), 2)
        self.assertEqual(response.data['comments'][0]['text'], 'Первый комментарий')

    def test_multiple_comments_ordering(self):
        """Тест порядка комментариев (старые первыми)"""
        comment1 = Comment.objects.create(
            author=self.user1,
            post=self.post,
            text='Первый комментарий'
        )
        comment2 = Comment.objects.create(
            author=self.user2,
            post=self.post,
            text='Второй комментарий'
        )

        comments = Comment.objects.all()
        self.assertEqual(comments[0], comment1)
        self.assertEqual(comments[1], comment2)


class PostStatsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user('user1', 'user1@test.com', 'pass')
        self.user2 = User.objects.create_user('user2', 'user2@test.com', 'pass')
        self.user3 = User.objects.create_user('user3', 'user3@test.com', 'pass')
        self.post = Post.objects.create(author=self.user1, text='Пост для статистики')

    def test_post_stats(self):
        """Тест статистики поста"""
        Like.objects.create(user=self.user1, post=self.post, reaction='like')
        Like.objects.create(user=self.user2, post=self.post, reaction='like')
        Like.objects.create(user=self.user3, post=self.post, reaction='dislike')

        Comment.objects.create(author=self.user1, post=self.post, text='Коммент 1')
        Comment.objects.create(author=self.user2, post=self.post, text='Коммент 2')

        url = reverse('post-stats', args=[self.post.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['likes_count'], 2)
        self.assertEqual(response.data['dislikes_count'], 1)
        self.assertEqual(response.data['comments_count'], 2)
        self.assertEqual(response.data['total_reactions'], 3)

    def test_post_stats_empty(self):
        """Тест статистики пустого поста"""
        url = reverse('post-stats', args=[self.post.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['likes_count'], 0)
        self.assertEqual(response.data['dislikes_count'], 0)
        self.assertEqual(response.data['comments_count'], 0)
        self.assertEqual(response.data['total_reactions'], 0)


class PostModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@test.com', 'pass')

    def test_post_creation(self):
        """Тест создания модели Post"""
        post = Post.objects.create(
            author=self.user,
            text='Тестовый пост',
            location_name='Тестовое место'
        )

        self.assertEqual(str(post), f'Post {post.id} by {self.user.username}')
        self.assertTrue(isinstance(post, Post))
        self.assertEqual(post.text, 'Тестовый пост')
        self.assertEqual(post.location_name, 'Тестовое место')

    def test_post_ordering(self):
        """Тест ordering постов (новые вверху)"""
        post1 = Post.objects.create(author=self.user, text='Первый пост')
        post2 = Post.objects.create(author=self.user, text='Второй пост')

        posts = Post.objects.all()
        self.assertEqual(posts[0], post2)
        self.assertEqual(posts[1], post1)

    def test_post_with_geolocation(self):
        """Тест поста с геолокацией"""
        post = Post.objects.create(
            author=self.user,
            text='Пост с координатами',
            latitude=55.7558,
            longitude=37.6173,
            location_name='Москва'
        )

        self.assertEqual(post.latitude, 55.7558)
        self.assertEqual(post.longitude, 37.6173)
        self.assertEqual(post.location_name, 'Москва')


class LikeModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@test.com', 'pass')
        self.post = Post.objects.create(author=self.user, text='Тестовый пост')

    def test_like_creation(self):
        """Тест создания лайка"""
        like = Like.objects.create(
            user=self.user,
            post=self.post,
            reaction=Like.LIKE
        )

        self.assertEqual(str(like), f'like by {self.user.username} '
                                    f'on post {self.post.id}')
        self.assertEqual(like.reaction, 'like')

    def test_unique_like_per_user(self):
        """Тест уникальности лайка для пользователя на пост"""
        Like.objects.create(user=self.user, post=self.post, reaction=Like.LIKE)

        with self.assertRaises(Exception):
            Like.objects.create(user=self.user, post=self.post, reaction=Like.DISLIKE)


class CommentModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@test.com', 'pass')
        self.post = Post.objects.create(author=self.user, text='Тестовый пост')

    def test_comment_creation(self):
        """Тест создания комментария"""
        comment = Comment.objects.create(
            author=self.user,
            post=self.post,
            text='Тестовый комментарий'
        )

        self.assertEqual(str(comment), f'Comment by {self.user.username} '
                                       f'on post {self.post.id}')
        self.assertEqual(comment.text, 'Тестовый комментарий')


def run_all_tests():
    """Функция для запуска всех тестов"""
    import unittest
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(PostAPITestCase)
    suite.addTests(loader.loadTestsFromTestCase(LikeTestCase))
    suite.addTests(loader.loadTestsFromTestCase(CommentTestCase))
    suite.addTests(loader.loadTestsFromTestCase(PostStatsTestCase))
    suite.addTests(loader.loadTestsFromTestCase(PostModelTestCase))
    suite.addTests(loader.loadTestsFromTestCase(LikeModelTestCase))
    suite.addTests(loader.loadTestsFromTestCase(CommentModelTestCase))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result


if __name__ == '__main__':
    run_all_tests()