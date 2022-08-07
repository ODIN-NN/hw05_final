from django.contrib.auth import get_user_model
from django.test import TestCase
from ..models import Group, Post


User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Это пост, необходимый для тестирования моделей.',
        )

    def test_models_have_correct_object_names(self):
        post = PostModelTest.post
        expected_object_name_post = self.post.text[:15]
        self.assertEqual(
            str(post),
            expected_object_name_post,
            '__str__ в модели "Post" работает неверно'
        )
        group = PostModelTest.group
        expected_object_name_group = self.group.title
        self.assertEqual(
            str(group),
            expected_object_name_group,
            '__str__ в модели "Group" работает неверно'
        )
