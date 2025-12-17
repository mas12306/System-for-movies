from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import PermissionsMixin

# Create your models here.
class Movie(models.Model):
    title = models.CharField(max_length=255,verbose_name='电影标题')
    score = models.FloatField(null = True, blank = True, verbose_name='评分')
    date = models.DateField(null = True, blank = True,verbose_name='发布日期')
    poster = models.URLField(max_length=255, null = True, blank = True,verbose_name='海报链接')
    actors = models.CharField(max_length=255, null = True, blank = True,verbose_name='演员表')
    region = models.CharField(max_length=255, null = True, blank = True,verbose_name='地区')
    type = models.CharField(max_length=255, null = True, blank = True,verbose_name='类型')
    summary = models.TextField(null = True, blank = True,verbose_name='简介')

    class Meta:
        verbose_name = '电影'
        verbose_name_plural = '电影集'

    def __str__(self):
        return self.title


class UserAction(models.Model):
    """用户行为：评分、收藏与评论"""
    user = models.ForeignKey("UserInfo", on_delete=models.CASCADE, related_name="actions")
    movie = models.ForeignKey("Movie", on_delete=models.CASCADE, related_name="actions")
    rating = models.FloatField(null=True, blank=True, verbose_name="评分")
    comment = models.TextField(null=True, blank=True, verbose_name="评论")
    is_favorite = models.BooleanField(default=False, verbose_name="收藏")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "movie")

    def __str__(self):
        return f"{self.user.username}-{self.movie.title}"

class UserManager(BaseUserManager):
    def _create_user(self, username, email, password, **kwargs):
        if not username:
            raise ValueError('请输入用户名')
        if not email:
            raise ValueError('请输入邮箱')
        if not password:
            raise ValueError('请输入密码')
        user = self.model(username=username, email=email, **kwargs)
        user.set_password(password)
        user.save()
        return user

    def create_user(self, username, email, password, **kwargs):
        kwargs['is_superuser'] = False
        return self._create_user(username, email, password, **kwargs)

    def create_superuser(self, username, email, password, **kwargs):
        kwargs['is_superuser'] = True
        kwargs['is_staff'] = True  # 超级用户必须有staff权限才能访问admin
        return self._create_user(username, email, password, **kwargs)

class UserInfo(AbstractUser,PermissionsMixin):
    user_ID = models.CharField(max_length=32, null=False,verbose_name="用户ID")
    username = models.CharField(max_length=255, null=False, verbose_name="用户名", unique=True)
    password = models.CharField(max_length=255, null=False, verbose_name="用户密码")
    nickname = models.CharField(max_length=255, null=False, verbose_name="用户昵称")
    sex_choice = {
        (1, "男"),
        (2, "女")
    }
    sex = models.IntegerField(choices=sex_choice, null = False, verbose_name="性别", default=1)
    age = models.IntegerField(verbose_name="年龄", null = True)
    email = models.EmailField(null = False, verbose_name="邮箱", unique=False)
    registration = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", null=False)
    last_login = models.DateTimeField(auto_now_add=True, verbose_name="上次登录时间", null=False)
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']
    EMAIL_FIELD = 'email'
    objects = UserManager()

    def __str__(self):
        return self.username


