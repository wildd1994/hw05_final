import time

from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.shortcuts import get_object_or_404
from django.test import TestCase, Client
from django.urls import reverse
from django.utils.cache import get_cache_key

from posts.models import User, Post, Group, Comment, Follow


class TestPosts(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.unauth_client = Client()
        self.user = User.objects.create_user(
            username='TestUser',
            password='Test12345',
            email='test@test.com'
        )
        self.group = Group.objects.create(
            title='TestTitle',
            slug='TestSlug',
            description='TestDescription'
        )
        self.client.force_login(self.user)

    def test_create_profile(self):
        user = self.user
        response = self.client.get(reverse('profile', kwargs={'username': user.username}))
        self.assertEqual(response.status_code, 200)

    def test_posted_new_post(self):
        text = 'TextTest'
        response = self.client.post(reverse('new_post'), data={'text': text, 'group': self.group.id}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.count(), 1)
        post = get_object_or_404(Post, author__username=self.user.username)
        self.assertEqual(post.text, text)
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.group, self.group)

    def test_not_posted_new_post(self):
        text = 'TextTest'
        login_url = reverse('login')
        new_post_url = reverse('new_post')
        url = f'{login_url}?next={new_post_url}'
        response = self.unauth_client.post(new_post_url, data={'text': text}, follow=True)
        self.assertRedirects(response, url)
        self.assertEqual(Post.objects.count(), 0)

    def test_new_post_location(self):
        text = 'TextTest'
        post = Post.objects.create(text=text, author=self.user, group=self.group)
        urls = (
            reverse('index'),
            reverse('profile', kwargs={'username': self.user.username}),
            reverse('post', kwargs={'username': self.user.username, 'post_id': post.id})
        )
        for url in urls:
            self.check_content(url, self.user, self.group, text)

    def test_edit_post(self):
        text = 'TextTest'
        edit_text = 'TestText'
        post = Post.objects.create(text=text, author=self.user, group=self.group)
        new_group = Group.objects.create(
            title='NewTestTitle',
            slug='NewTestSlug',
            description='NewTestDescription'
        )
        urls = (
            reverse('index'),
            reverse('profile', kwargs={'username': self.user.username}),
            reverse('post', kwargs={'username': self.user.username, 'post_id': post.id}),
            reverse('group', kwargs={'slug': new_group.slug})
        )
        edit_post = self.client.post(reverse('post_edit', kwargs={'username': self.user.username, 'post_id': post.id}),
                                     data={'text': edit_text, 'group': new_group.id},
                                     follow=True)
        old_group = self.client.get(reverse('group', kwargs={'slug': self.group.slug}))
        self.assertEqual(len(old_group.context['page']), 0)
        for url in urls:
            self.check_content(url, self.user, new_group, edit_text)

    def check_content(self, url, user, group, text):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        if 'paginator' in response.context:
            post = response.context['page'][0]
        else:
            post = response.context['selected_post']
        self.assertEqual(post.text, text)
        self.assertEqual(post.author, user)
        self.assertEqual(post.group.id, group.id)

    def test_comment_post(self):
        text = 'TextTest'
        post = Post.objects.create(text=text, author=self.user)
        self.client.post(reverse('add_comment', kwargs={'username': self.user.username, 'post_id': post.id}), data={'post': post, 'text': text, 'author': self.user}, follow=True)
        response = self.client.get(reverse('post', kwargs={'username': self.user.username, 'post_id': post.id}))
        self.assertEqual(len(response.context['comments']), 1)
        self.client.logout()
        self.client.post(reverse('add_comment', kwargs={'username': self.user.username, 'post_id': post.id}), data={'post': post, 'text': text, 'author': self.user}, follow=True)
        response = self.client.get(reverse('post', kwargs={'username': self.user.username, 'post_id': post.id}))
        self.assertEqual(len(response.context['comments']), 1)


class TestImage(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username='TestUser',
            password='Test12345',
            email='test@test.com'
        )
        self.group = Group.objects.create(
            title='TestTitle',
            slug='TestSlug',
            description='TestDescription'
        )
        self.post = Post.objects.create(
            author=self.user,
            text='TestText',
            group=self.group
        )
        self.client.force_login(self.user)

    def test_image(self):
        with open('media/posts/cartman.jpg', 'rb') as img:
            response = self.client.post(reverse('post_edit', kwargs={'username': self.user.username, 'post_id': self.post.id}),
                                        {
                                            'text': 'post with image',
                                            'image': img,
                                            'group': self.group.id
                                        }
                                        )
        urls = (
            reverse('index'),
            reverse('post', kwargs={'username': self.user.username, 'post_id': self.post.id}),
            reverse('profile', kwargs={'username': self.user.username}),
            reverse('group', kwargs={'slug': self.group.slug})
        )
        for url in urls:
            response = self.client.get(url)
            self.assertContains(response, '<img'.encode())

    def test_not_image(self):
        with open('media/posts/test.txt', 'rb') as img:
            post = self.client.post(reverse('post_edit', kwargs={'username': self.user.username, 'post_id': self.post.id}),
                                        {
                                            'text': 'post with image',
                                            'image': img,
                                            'group': self.group.id
                                        }
                                        )
            response = self.client.get(reverse('index'))
            self.assertNotContains(response, '<img'.encode())


class TestCache(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username='TestUser',
            password='Test12345',
            email='test@test.com'
        )
        self.group = Group.objects.create(
            title='TestTitle',
            slug='TestSlug',
            description='TestDescription'
        )
        self.post = Post.objects.create(
            author=self.user,
            text='TestText',
            group=self.group
        )
        self.client.force_login(self.user)

    def test_cache(self):
        text = 'TestCache'
        response = self.client.get(reverse('index'))
        self.assertNotEqual(response.context, None)
        self.post = Post.objects.create(author=self.user, text=text)
        response = self.client.get(reverse('index'))
        self.assertEqual(response.context, None)
        cache.clear()
        response = self.client.get(reverse('index'))
        self.assertNotEqual(response.context, None)
        self.assertEqual(response.context['page'][0].text, text)


class TestFollow(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username='TestUser',
            password='Test12345',
            email='test@test.com'
        )
        self.second_user = User.objects.create_user(
            username='TestUser2',
            password='Test12345',
            email='test@test.com',
        )
        self.new_client = Client()
        self.new_client2 = Client()
        self.post = Post.objects.create(author=self.user, text='TestText')
        self.second_post = Post.objects.create(author=self.second_user, text='Text')
        self.myself_user = User.objects.create_user(
            username='MySelfUser',
            password='Test12345',
            email='test@test.com'
        )
        self.client.force_login(self.myself_user)

    def test_follow_and_unfollow(self):
        self.client.get(reverse('profile_follow', kwargs={'username': self.user.username}))
        self.assertEqual(Follow.objects.count(), 1)
        self.client.get(reverse('profile_unfollow', kwargs={'username': self.user.username}))
        self.assertEqual(Follow.objects.count(), 0)
    
    def test_follow_index(self):
        self.client.get(reverse('profile_follow', kwargs={'username': self.user.username}))
        response = self.client.get(reverse('follow_index'))
        self.assertEqual(response.context['post'], self.post)
        self.assertNotEqual(response.context['post'], self.second_post)
