from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from ..forms import PostForm
from ..models import Group, Post, Follow
from time import sleep
from django.core.cache import cache


User = get_user_model()


class GroupPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создаем запись группы в БД
        cls.user = User.objects.create_user(username='test_user')
        cls.user_author = User.objects.create_user(username='test_user_author')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.group_2 = Group.objects.create(
            title='Тестовый заголовок 2',
            slug='test-slug-2',
            description='Тестовое описание 2'
        )

        # Создаем записи постов в БД

        cls.COUNT_POST_FOR_TEST = 13
        for post_number in range(cls.COUNT_POST_FOR_TEST):
            sleep(0.01)
            cls.post = Post.objects.create(
                text=f'Test text пост номер {post_number + 1}',
                author=cls.user_author,
                group=cls.group,
            )


    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем пользователя
        self.user = User.objects.create_user(username='JohnDoe')
        # Создаем второй клиент
        self.authorized_client = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(self.user)
        # Создаем пользователя-автора
        self.authorized_client_author = Client()
        # Авторизуем пользователя-автора
        self.authorized_client_author.force_login(self.user_author)
        cache.clear()
        Follow.objects.create(
            user=self.user,
            author=self.user_author
        )

    # Проверяем используемые шаблоны
    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Собираем в словарь пары "reverse(name): имя_html_шаблона"
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
                'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': self.post.author.username}):
                'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post.id}):
                'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}):
                'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(template=template):
                response = self.authorized_client_author.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def control_context(self, response):
        object = response.context['page_obj'][0]
        self.assertEqual(object.author, self.user_author)
        self.assertEqual(object.text, 'Test text пост номер 13')
        self.assertEqual(object.group, self.group)
        self.assertEqual(object.pub_date, self.post.pub_date)

    def test_pages_accept_correct_context_index(self):
        """Проверка правильности передаваемого
        словаря context функции index."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.control_context(response)

    def test_pages_accept_correct_context_post_detail(self):
        response = self.authorized_client.get(
            reverse('posts:post_detail', args=(self.post.id,)))
        self.assertEqual(response.context.get('post'), self.post)

    def test_pages_accept_correct_context_group_post(self):
        """Проверка правильности передаваемого
        словаря context функции group_posts."""
        response = self.authorized_client.get(reverse(
            'posts:group_list', args=(self.group.slug,)))
        self.control_context(response)
        group_posts_context_group = response.context['group']
        self. assertEqual(group_posts_context_group, self.group)

    def test_pages_accept_correct_context_profile(self):
        """Проверка правильности передаваемого
        словаря context функции profile."""
        response = self.authorized_client.get(
            reverse('posts:profile', args=(self.user_author.username,)))
        self.control_context(response)
        context_author = response.context['author']
        context_posts_count = response.context['posts_count']
        self.assertEqual(context_author, self.post.author)
        self.assertEqual(context_posts_count, self.COUNT_POST_FOR_TEST)

    def test_pages_accept_correct_context_post_create(self):
        """Проверка правильности передаваемого
        словаря context функции post_create"""
        response = self.authorized_client_author.post(
            reverse('posts:post_create', None))
        form = response.context.get('form')
        self.assertIsNotNone(form)
        self.assertIsInstance(form, PostForm)

    def test_pages_accept_correct_context_post_edit(self):
        """Проверка правильности передаваемого
        словаря context функции post_edit"""
        response = self.authorized_client_author.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}))
        form = response.context.get('form')
        self.assertIsNotNone(form)
        self.assertIsInstance(form, PostForm)

    def test_paginator(self):
        pages_list = (
            (reverse('posts:index', None,)),
            (reverse('posts:group_list', args=(self.group.slug,))),
            (reverse('posts:profile', args=(self.post.author,))),
        )
        for page in pages_list:
            with self.subTest(page=page):
                response = self.authorized_client_author.get(page)
                self.assertEqual(len(response.context['page_obj']), (
                    10))
                response_2 = self.authorized_client.get(page + '?page=2')
                self.assertEqual(len(response_2.context['page_obj']), (
                    self.COUNT_POST_FOR_TEST - 10))

    def test_create_new_post(self):
        response_group = self.authorized_client_author.\
            get(reverse('posts:group_list',
                        kwargs={'slug': f'{self.group.slug}'}))
        object_post_group_list = response_group.context['page_obj'][0]
        response_group_2 = self.authorized_client_author.\
            get(reverse('posts:group_list',
                        kwargs={'slug': f'{self.group_2.slug}'}))
        self.assertEqual(object_post_group_list, self.post)
        self.assertNotIn(object_post_group_list,
                         response_group_2.context['page_obj'])

    def test_cache(self):
        test_post = Post.objects.create(author=self.user_author)
        response_1 = self.authorized_client.get(reverse('posts:index'))
        content_1 = response_1.content
        test_post.delete()
        response_2 = self.authorized_client.get(reverse('posts:index'))
        content_2 = response_2.content
        self.assertEqual(content_1, content_2)
        cache.clear()
        response_3 = self.authorized_client.get(reverse('posts:index'))
        content_3 = response_3.content
        self.assertNotEqual(content_1, content_3)

    def test_posts_feed(self):
        """Новая запись пользователя появляется в ленте тех,
        кто на него подписан и не появляется в ленте тех,
        кто не подписан."""
        response_before = self.authorized_client_author.get(
            reverse('posts:follow_index'))
        self.post_1 = Post.objects.create(
            text='text_for_follower_with_love',
            author=self.user_author,
            group=self.group, )
        response = self.authorized_client.get(
            reverse('posts:follow_index'))
        object = response.context['page_obj'][0]
        self.assertEqual(object.text, 'text_for_follower_with_love')
        response_after = self.authorized_client_author.get(
            reverse('posts:follow_index'))
        self.assertEqual(response_before.content, response_after.content)

    def test_follow(self):
        """Возможность подписываться на других
        пользователей и удалять их из подписок."""
        self.authorized_client.get(
            reverse('posts:profile_unfollow', args=(
                self.user_author.username,)))
        self.assertEqual(Follow.objects.count(), 0)
        self.authorized_client.get(
            reverse('posts:profile_follow', args=(
                self.user_author.username,)))
        self.assertEqual(Follow.objects.count(), 1)
