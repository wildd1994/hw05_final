from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page

from .forms import PostForm, CommentForm
from .models import Group, Post, User, Comment, Follow


@cache_page(20, key_prefix='index_page')
def index(request):
    post_list = Post.objects.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        'index.html',
        {
            'page': page,
            'paginator': paginator
        }
    )


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        'group.html',
        {
            'group': group,
            'page': page,
            'paginator': paginator
        }
    )


@login_required
def new_post(request):
    form = PostForm(request.POST or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('index')
    return render(
        request,
        'posts/new_post.html',
        {
            'form': form
        }
    )


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = author.posts.all()
    paginator = Paginator(posts, 6)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    following = request.user.is_authenticated and (
            Follow.objects.filter(user=request.user, author=author).exists())
    return render(
        request,
        'posts/profile.html',
        {
            'author': author,
            'page': page,
            'paginator': paginator,
            'following': following,
            'profile': True,
        }
        )


def post_view(request, username, post_id):
    selected_post = get_object_or_404(Post, pk=post_id, author__username=username)
    author = selected_post.author
    form = CommentForm()
    return render(
        request,
        'posts/post.html',
        {
            'author': author,
            'selected_post': selected_post,
            'form': form,
         }
    )


def post_edit(request, username, post_id):
    get_post = get_object_or_404(Post, pk=post_id, author__username=username)
    if request.user != get_post.author:
        return redirect('post_view', username=username, post_id=post_id)
    form = PostForm(request.POST or None, files=request.FILES or None, instance=get_post)
    if form.is_valid():
        form.save()
        return redirect('post', username=username, post_id=post_id)
    return render(
        request,
        'posts/new_post.html',
        {
            'get_post': get_post,
            'form': form,
            'update': True,
        }
    )


@login_required
def add_comment(request, username, post_id):
    get_post = get_object_or_404(Post, pk=post_id, author__username=username)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = get_post
        comment.save()
        return redirect('post', username=username, post_id=post_id)
    return render(
        request,
        'included_snippet/comments.html',
        {
            'get_post': get_post,
            'form': form,
        }
    )


@login_required
def follow_index(request):
    post_list = Post.objects.filter(author__following__user=request.user)
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        'follow.html',
        {
            'page': page,
            'paginator': paginator
        }
    )


@login_required
def profile_follow(request, username):
    follower = request.user
    following = get_object_or_404(User, username=username)
    follow = Follow.objects.filter(user=follower, author=following).exists()
    if not follow and follower != following:
        Follow.objects.create(user=follower, author=following)
    return redirect('profile', username=username)


@login_required
def profile_unfollow(request, username):
    follower = request.user
    following = get_object_or_404(User, username=username)
    follow = Follow.objects.filter(user=follower, author=following)
    if follow.exists() and follower != following:
        follow.delete()
    return redirect('profile', username=username)


def page_not_found(request, exception):
    return render(
        request,
        "misc/404.html",
        {"path": request.path},
        status=404
    )


def server_error(request):
    return render(request, "misc/500.html", status=500)
