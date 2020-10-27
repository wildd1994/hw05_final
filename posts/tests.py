from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.urls import reverse

from posts.models import User, Post, Group, Comment, Follow


class TestPosts(TestCase):
    def setUp(self) -> None:
        self.client = Client()
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
        cache.clear()

    def test_create_profile(self):
        user = self.user
        response = self.client.get(reverse('profile',
                                           kwargs={'username': user.username})
                                   )
        self.assertEqual(response.status_code, 200)

    def test_posted_new_post(self):
        text = 'TextTest'
        response = self.client.post(reverse('new_post'),
                                    data={'text': text, 'group': self.group.id},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.count(), 1)
        post = Post.objects.first()
        self.assertEqual(post.text, text)
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.group, self.group)

    def test_not_posted_new_post(self):
        self.un_auth_client = Client()
        text = 'TextTest'
        login_url = reverse('login')
        new_post_url = reverse('new_post')
        url = f'{login_url}?next={new_post_url}'
        response = self.un_auth_client.post(new_post_url,
                                            data={'text': text},
                                            follow=True)
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
        self.client.post(reverse('post_edit',
                                 kwargs={'username': self.user.username, 'post_id': post.id}),
                         data={'text': edit_text, 'group': new_group.id},
                         follow=True)
        old_group = self.client.get(reverse('group', kwargs={'slug': self.group.slug}))
        self.assertEqual(old_group.context['paginator'].count, 0)
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

    def test_comment_post_auth(self):
        text = 'TextTest'
        post = Post.objects.create(text=text,
                                   author=self.user)
        self.client.post(reverse('add_comment',
                                 kwargs={'username': self.user.username,
                                         'post_id': post.id}),
                         data={'post': post,
                               'text': text,
                               'author': self.user},
                         follow=True
                         )
        comment = Comment.objects.first()
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(comment.text, text)
        self.assertEqual(comment.author, self.user)

    def test_comment_post_not_auth(self):
        un_auth_client = Client()
        text = 'TextTest'
        post = Post.objects.create(text=text, author=self.user)
        response = un_auth_client.post(reverse('add_comment',
                                               kwargs={'username': self.user,
                                                       'post_id': post.id}),
                                       data={'post': post,
                                             'text': text,
                                             'author': self.user},
                                       follow=True)
        login_url = reverse('login')
        comment_post_url = reverse('add_comment',
                                   kwargs={'username': self.user, 'post_id': post.id})
        url = f'{login_url}?next={comment_post_url}'
        self.assertRedirects(response, url)
        self.assertFalse(Comment.objects.exists())


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
        self.client.force_login(self.user)

    def test_image(self):
        cache.clear()
        content_image = (b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21'
                         b'\xf9\x04\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00'
                         b'\x01\x00\x00\x02\x02\x4c\x01\x00\x3b')
        image = SimpleUploadedFile(name='test_image.jpg',
                                   content=content_image,
                                   content_type='image/jpg')
        post = Post.objects.create(author=self.user,
                                   text='TestText',
                                   group=self.group,
                                   image=image)
        urls = (
            reverse('index'),
            reverse('post', kwargs={'username': self.user.username, 'post_id': post.id}),
            reverse('profile', kwargs={'username': self.user.username}),
            reverse('group', kwargs={'slug': self.group.slug})
        )
        for url in urls:
            response = self.client.get(url)
            self.assertContains(response, '<img')

    def test_not_image(self):
        file = SimpleUploadedFile('file.txt', b'Hello', 'text/plain')
        response = self.client.post(reverse('new_post'),
                                    data={
                                        'author': self.user,
                                        'text': 'post with image',
                                        'image': file,
                                        'group': self.group.id
                                    },
                                    follow=True)
        self.assertFormError(response, 'form', 'image',
                             'Upload a valid image. The file you uploaded was either'
                             ' not an image or a corrupted image.'
                             )


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
        self.client.force_login(self.user)

    def test_cache(self):
        text = 'TestCache'
        self.client.get(reverse('index'))
        Post.objects.create(author=self.user, text=text, group=self.group)
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
        self.group = Group.objects.create(
            title='TestTitle',
            slug='TestSlug',
            description='TestDescription'
        )
        self.client = Client()
        self.myself_user = User.objects.create_user(
            username='MySelfUser',
            password='Test12345',
            email='test@test.com'
        )
        self.client.force_login(self.myself_user)

    def test_follow(self):
        self.client.get(reverse('profile_follow', kwargs={'username': self.user.username}))
        follow = Follow.objects.first()
        self.assertEqual(Follow.objects.count(), 1)
        self.assertEqual(follow.author, self.user)
        self.assertEqual(follow.user, self.myself_user)

    def test_unfollow(self):
        self.client.get(reverse('profile_follow', kwargs={'username': self.user.username}))
        self.client.get(reverse('profile_unfollow', kwargs={'username': self.user.username}))
        self.assertFalse(Follow.objects.exists())

    def test_follow_index(self):
        Post.objects.create(author=self.user, text='TestText', group=self.group)
        self.client.get(reverse('profile_follow', kwargs={'username': self.user.username}))
        response = self.client.get(reverse('follow_index'))
        post = response.context['post']
        self.assertEqual(post.text, 'TestText')
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.group.id, self.group.id)

    def test_unfollow_index(self):
        Post.objects.create(author=self.user, text='TestText', group=self.group)
        response = self.client.get(reverse('follow_index'))
        self.assertEqual(response.context['paginator'].count, 0)
