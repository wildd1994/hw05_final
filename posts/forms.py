from django import forms

from .models import Comment, Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image', )

        required = {
            'group': False,
        }

        help_texts = {
            'text': 'Текст записи',
            'group': 'Выбор группы',
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
