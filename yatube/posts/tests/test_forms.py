import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Group, Post, Comment

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_author = User.objects.create_user(username='Test_author_name')
        cls.group = Group.objects.create(
            title='Тестовая_группа',
            slug='test_slug',
            description='Тестовое_описание'
        )
        cls.group_2 = Group.objects.create(
            title='Тестовая_группа_2',
            slug='test_slug_2',
            description='Тестовое_описание_2',
        )
        cls.post = Post.objects.create(
            text='Test_text',
            author=cls.user_author,
            group=cls.group
        )
        cls.comment = Comment.objects.create(
            text='setUpClass comment',
            author=cls.user_author,
            post=cls.post,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(self.user_author)

    def test_create_post(self):
        """Форма создаёт запись в БД."""
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small_gif.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Test_text',
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_client_author.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response,
                             reverse('posts:profile',
                                     args=(self.user_author.username,)))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        first_object = Post.objects.first()
        self.assertEqual(first_object.text, form_data.get('text'))
        self.assertEqual(first_object.author, self.user_author)
        self.assertEqual(first_object.group, self.group)
        self.assertEqual(first_object.image, 'posts/small_gif.gif')

    def test_edit_post_author(self):
        """"Проверка редактирования поста."""
        posts_count = Post.objects.count()
        new_form_data = {
            'text': 'new_text',
            'group': self.group_2.id,
        }
        response = self.authorized_client_author.post(
            reverse('posts:post_edit', args=(self.post.id,)),
            data=new_form_data,
            follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Post.objects.count(), posts_count)
        first_object = Post.objects.first()
        self.assertEqual(first_object.text, 'new_text')
        self.assertEqual(first_object.author, self.user_author)
        self.assertEqual(first_object.group.id, self.group_2.id)
        self.assertRedirects(response, reverse(
            'posts:post_detail', args=(self.post.id,)))

    def test_create_comment(self):
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый комментарий.',
        }
        response = self.authorized_client_author.post(
            reverse('posts:add_comment', args=(self.post.id,)),
            data=form_data,
            follow=True
        )
        test_comment = Comment.objects.first()
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertEqual(test_comment.text, form_data['text'])
