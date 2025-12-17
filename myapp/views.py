from collections import Counter
from urllib.parse import urlencode
import json

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Avg
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from .forms import (
    LoginForm,
    RegistrationForm,
    ProfileForm,
    PasswordUpdateForm,
)
from .models import Movie, UserAction


def _querystring_without_page(request):
    params = request.GET.copy()
    params.pop("page", None)
    qs = params.urlencode()
    return f"&{qs}" if qs else ""


def _split_tokens(value):
    if not value:
        return []
    tokens = value.replace("，", ",").replace("、", ",").replace("|", ",").replace("/", ",").split(",")
    return [t.strip() for t in tokens if t.strip()]


def _personalized_recommendations(user, limit=24):
    actions = (
        UserAction.objects.filter(user=user)
        .select_related("movie")
        .order_by("-updated_at")[:200]
    )
    if not actions:
        return None

    type_counter, actor_counter = Counter(), Counter()
    seen_movie_ids = set()
    for action in actions:
        m = action.movie
        seen_movie_ids.add(m.id)
        type_counter.update(_split_tokens(m.type))
        actor_counter.update(_split_tokens(m.actors))

    top_types = [t for t, _ in type_counter.most_common(5)]
    top_actors = [a for a, _ in actor_counter.most_common(5)]

    filters = Q()
    for t in top_types:
        filters |= Q(type__icontains=t)
    for a in top_actors:
        filters |= Q(actors__icontains=a)

    qs = Movie.objects.exclude(id__in=seen_movie_ids)
    if filters:
        qs = qs.filter(filters)
    qs = qs.order_by("-score", "-date")[:limit]
    return qs if qs else None


def _hot_recommendations(limit=24):
    return Movie.objects.order_by("-score", "-date")[:limit]


def home(request):
    top_rated = Movie.objects.order_by("-score")[:8]
    latest = Movie.objects.order_by("-date")[:8]
    recommend = top_rated if request.user.is_anonymous else Movie.objects.order_by("-score")[:6]
    return render(
        request,
        "home/index.html",
        {
            "top_rated": top_rated,
            "latest": latest,
            "recommend": recommend,
        },
    )


def login_user(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data["user"]
            login(request, user)
            messages.success(request, "登录成功")
            return redirect("/")
    else:
        form = LoginForm()
    return render(request, "auth/login.html", {"form": form})


def register_user(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "注册成功，已自动登录")
            return redirect("/")
    else:
        form = RegistrationForm()
    return render(request, "auth/register.html", {"form": form})


def logout_user(request):
    logout(request)
    messages.info(request, "已退出登录")
    return redirect("/")


def top_list(request):
    region = request.GET.get("region")
    mtype = request.GET.get("type")
    qs = Movie.objects.all()
    if region:
        qs = qs.filter(region__icontains=region)
    if mtype:
        qs = qs.filter(type__icontains=mtype)
    qs = qs.order_by("-score")

    paginator = Paginator(qs, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "movies/top.html",
        {
            "page_obj": page_obj,
            "regions": Movie.objects.exclude(region__isnull=True).exclude(region="").values_list("region", flat=True).distinct()[:30],
            "types": Movie.objects.exclude(type__isnull=True).exclude(type="").values_list("type", flat=True).distinct()[:30],
            "querystring": _querystring_without_page(request),
        },
    )


def movie_list(request):
    keyword = request.GET.get("q")
    region = request.GET.get("region")
    mtype = request.GET.get("type")
    sort = request.GET.get("sort", "-date")

    qs = Movie.objects.all()
    if keyword:
        qs = qs.filter(Q(title__icontains=keyword) | Q(actors__icontains=keyword) | Q(summary__icontains=keyword))
    if region:
        qs = qs.filter(region__icontains=region)
    if mtype:
        qs = qs.filter(type__icontains=mtype)
    if sort not in ["-date", "-score", "date", "score"]:
        sort = "-date"
    qs = qs.order_by(sort)

    paginator = Paginator(qs, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "movies/list.html",
        {
            "page_obj": page_obj,
            "regions": Movie.objects.exclude(region__isnull=True).exclude(region="").values_list("region", flat=True).distinct()[:30],
            "types": Movie.objects.exclude(type__isnull=True).exclude(type="").values_list("type", flat=True).distinct()[:30],
            "querystring": _querystring_without_page(request),
            "sort": sort,
            "keyword": keyword or "",
            "region": region or "",
            "mtype": mtype or "",
        },
    )


def movie_detail(request, pk):
    movie = get_object_or_404(Movie, pk=pk)
    related = Movie.objects.filter(type=movie.type).exclude(pk=pk).order_by("-score")[:6]
    action = None
    if request.user.is_authenticated:
        action = UserAction.objects.filter(user=request.user, movie=movie).first()
    # 获取所有评论（有评分或评论的）
    from django.db.models import Q
    comments = UserAction.objects.filter(
        movie=movie
    ).filter(
        Q(rating__isnull=False) | Q(comment__isnull=False, comment__gt="")
    ).select_related("user").order_by("-updated_at")
    return render(
        request,
        "movies/detail.html",
        {
            "movie": movie,
            "related": related,
            "action": action,
            "comments": comments,
        },
    )


def recommend_view(request):
    personalized = False
    recs = None
    if request.user.is_authenticated:
        recs = _personalized_recommendations(request.user, limit=18)
        personalized = recs is not None and len(recs) > 0
    if not recs:
        recs = _hot_recommendations(limit=18)
    return render(
        request,
        "recommend/index.html",
        {
            "recs": recs,
            "personalized": personalized,
        },
    )


def profile(request):
    if request.user.is_anonymous:
        messages.info(request, "请先登录")
        return redirect("login")
    favorites = (
        UserAction.objects.filter(user=request.user, is_favorite=True)
        .select_related("movie")
        .order_by("-updated_at")
    )
    rated = (
        UserAction.objects.filter(user=request.user, rating__isnull=False)
        .select_related("movie")
        .order_by("-updated_at")
    )
    return render(
        request,
        "account/profile.html",
        {
            "user_obj": request.user,
            "favorites": favorites,
            "rated": rated,
        },
    )


@login_required
def user_stats(request):
    """用户统计数据页面"""
    user = request.user
    
    # 收藏统计
    favorites = UserAction.objects.filter(user=user, is_favorite=True).select_related("movie")
    favorite_count = favorites.count()
    
    # 评分统计
    rated = UserAction.objects.filter(user=user, rating__isnull=False).select_related("movie")
    rated_count = rated.count()
    avg_rating = rated.aggregate(avg=Avg("rating"))["avg"] or 0
    
    # 评分分布（0-2, 2-4, 4-6, 6-8, 8-10）
    rating_dist = {"range_0_2": 0, "range_2_4": 0, "range_4_6": 0, "range_6_8": 0, "range_8_10": 0}
    for action in rated:
        r = action.rating
        if r < 2:
            rating_dist["range_0_2"] += 1
        elif r < 4:
            rating_dist["range_2_4"] += 1
        elif r < 6:
            rating_dist["range_4_6"] += 1
        elif r < 8:
            rating_dist["range_6_8"] += 1
        else:
            rating_dist["range_8_10"] += 1
    
    # 收藏影片的类型统计
    favorite_types = Counter()
    for action in favorites:
        if action.movie.type:
            types = _split_tokens(action.movie.type)
            favorite_types.update(types)
    top_types = dict(favorite_types.most_common(10))
    
    # 收藏影片的地区统计
    favorite_regions = Counter()
    for action in favorites:
        if action.movie.region:
            regions = _split_tokens(action.movie.region)
            favorite_regions.update(regions)
    top_regions = dict(favorite_regions.most_common(10))
    
    # 评分影片的类型统计
    rated_types = Counter()
    for action in rated:
        if action.movie.type:
            types = _split_tokens(action.movie.type)
            rated_types.update(types)
    top_rated_types = dict(rated_types.most_common(10))
    
    # 评分影片的地区统计
    rated_regions = Counter()
    for action in rated:
        if action.movie.region:
            regions = _split_tokens(action.movie.region)
            rated_regions.update(regions)
    top_rated_regions = dict(rated_regions.most_common(10))
    
    # 月度收藏趋势（简化：按创建时间）
    from django.utils import timezone
    from datetime import timedelta
    monthly_favorites = {}
    for action in favorites:
        month_key = action.created_at.strftime("%Y-%m")
        monthly_favorites[month_key] = monthly_favorites.get(month_key, 0) + 1
    
    # 月度评分趋势
    monthly_ratings = {}
    for action in rated:
        month_key = action.created_at.strftime("%Y-%m")
        if month_key not in monthly_ratings:
            monthly_ratings[month_key] = []
        monthly_ratings[month_key].append(action.rating)
    monthly_avg_ratings = {k: sum(v) / len(v) for k, v in monthly_ratings.items()}
    
    return render(
        request,
        "account/stats.html",
        {
            "user_obj": user,
            "favorite_count": favorite_count,
            "rated_count": rated_count,
            "avg_rating": round(avg_rating, 2),
            "rating_dist": rating_dist,
            "top_types": json.dumps(top_types, ensure_ascii=False),
            "top_regions": json.dumps(top_regions, ensure_ascii=False),
            "top_rated_types": json.dumps(top_rated_types, ensure_ascii=False),
            "top_rated_regions": json.dumps(top_rated_regions, ensure_ascii=False),
            "monthly_favorites": json.dumps(monthly_favorites, ensure_ascii=False),
            "monthly_avg_ratings": json.dumps({k: round(v, 2) for k, v in monthly_avg_ratings.items()}, ensure_ascii=False),
        },
    )


@login_required
def profile_edit(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "资料已更新")
            return redirect("profile")
    return render(request, "account/edit.html", {"form": form})


@login_required
def profile_password(request):
    form = PasswordUpdateForm(user=request.user, data=request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "密码已更新")
            return redirect("profile")
    return render(request, "account/password.html", {"form": form})


@login_required
def toggle_favorite(request, pk):
    movie = get_object_or_404(Movie, pk=pk)
    action, _ = UserAction.objects.get_or_create(user=request.user, movie=movie)
    action.is_favorite = not action.is_favorite
    action.save()
    messages.success(request, "已收藏" if action.is_favorite else "已取消收藏")
    return redirect("movie_detail", pk=pk)


@login_required
def rate_movie(request, pk):
    movie = get_object_or_404(Movie, pk=pk)
    try:
        rating = float(request.POST.get("rating"))
    except (TypeError, ValueError):
        messages.error(request, "评分格式不正确")
        return redirect("movie_detail", pk=pk)
    action, _ = UserAction.objects.get_or_create(user=request.user, movie=movie)
    action.rating = max(0, min(10, rating))
    action.save()
    messages.success(request, f"已评分 {action.rating}")
    return redirect("movie_detail", pk=pk)


@login_required
def toggle_favorite_api(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)
    movie = get_object_or_404(Movie, pk=pk)
    action, _ = UserAction.objects.get_or_create(user=request.user, movie=movie)
    action.is_favorite = not action.is_favorite
    action.save()
    return JsonResponse({"is_favorite": action.is_favorite})


@login_required
def rate_movie_api(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)
    movie = get_object_or_404(Movie, pk=pk)
    try:
        rating = float(request.POST.get("rating"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "invalid rating"}, status=400)
    rating = max(0, min(10, rating))
    action, _ = UserAction.objects.get_or_create(user=request.user, movie=movie)
    action.rating = rating
    action.save()
    return JsonResponse({"rating": action.rating})


@login_required
def submit_comment(request, pk):
    """提交评论（可同时评分和评论）"""
    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)
    movie = get_object_or_404(Movie, pk=pk)
    action, _ = UserAction.objects.get_or_create(user=request.user, movie=movie)
    
    # 处理评分
    rating = request.POST.get("rating")
    if rating:
        try:
            rating = float(rating)
            rating = max(0, min(10, rating))
            action.rating = rating
        except (TypeError, ValueError):
            pass
    
    # 处理评论
    comment = request.POST.get("comment", "").strip()
    if comment:
        action.comment = comment
    
    action.save()
    
    return JsonResponse({
        "success": True,
        "rating": action.rating,
        "comment": action.comment,
        "user": request.user.nickname or request.user.username,
        "updated_at": action.updated_at.strftime("%Y-%m-%d %H:%M:%S")
    })


def recommend_api(request):
    personalized = False
    recs = None
    if request.user.is_authenticated:
        recs = _personalized_recommendations(request.user, limit=30)
        personalized = recs is not None and len(recs) > 0
    if not recs:
        recs = _hot_recommendations(limit=30)
    data = [
        {
            "id": m.id,
            "title": m.title,
            "score": m.score,
            "poster": m.poster,
            "type": m.type,
            "region": m.region,
            "date": m.date,
        }
        for m in recs
    ]
    return JsonResponse({"personalized": personalized, "items": data})