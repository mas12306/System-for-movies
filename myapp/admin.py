from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import Movie, UserInfo, UserAction


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    """电影管理"""
    list_display = ['id', 'title', 'score', 'date', 'region', 'type', 'poster_preview']
    list_filter = ['region', 'type', 'date']
    search_fields = ['title', 'actors', 'summary']
    list_editable = ['score']
    list_per_page = 20
    ordering = ['-id']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'score', 'date', 'poster')
        }),
        ('详细信息', {
            'fields': ('actors', 'region', 'type', 'summary')
        }),
    )
    
    def poster_preview(self, obj):
        """海报预览"""
        if obj.poster:
            return format_html('<img src="{}" style="max-width: 60px; max-height: 90px; object-fit: cover;" />', obj.poster)
        return '-'
    poster_preview.short_description = '海报'


@admin.register(UserInfo)
class UserInfoAdmin(BaseUserAdmin):
    """用户管理"""
    list_display = ['id', 'username', 'nickname', 'email', 'sex', 'age', 'is_active', 'is_staff', 'is_superuser', 'registration', 'last_login']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'sex', 'registration']
    search_fields = ['username', 'nickname', 'email', 'user_ID']
    list_editable = ['is_active']
    list_per_page = 20
    ordering = ['-registration']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('username', 'nickname', 'email', 'password')
        }),
        ('个人信息', {
            'fields': ('sex', 'age', 'user_ID')
        }),
        ('权限', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('时间信息', {
            'fields': ('registration', 'last_login', 'date_joined')
        }),
    )
    
    add_fieldsets = (
        ('创建用户', {
            'classes': ('wide',),
            'fields': ('username', 'nickname', 'email', 'password1', 'password2', 'sex', 'age'),
        }),
    )
    
    readonly_fields = ['registration', 'last_login', 'date_joined', 'user_ID']


@admin.register(UserAction)
class UserActionAdmin(admin.ModelAdmin):
    """用户行为管理（评分、收藏、评论）"""
    list_display = ['id', 'user', 'movie', 'rating', 'is_favorite', 'comment_preview', 'created_at', 'updated_at']
    list_filter = ['is_favorite', 'rating', 'created_at']
    search_fields = ['user__username', 'user__nickname', 'movie__title', 'comment']
    list_per_page = 20
    ordering = ['-updated_at']
    
    fieldsets = (
        ('关联信息', {
            'fields': ('user', 'movie')
        }),
        ('行为信息', {
            'fields': ('rating', 'is_favorite', 'comment')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def comment_preview(self, obj):
        """评论预览"""
        if obj.comment:
            preview = obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
            return format_html('<span title="{}">{}</span>', obj.comment, preview)
        return '-'
    comment_preview.short_description = '评论'
