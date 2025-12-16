from collections import Counter
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
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
    return render(
        request,
        "movies/detail.html",
        {
            "movie": movie,
            "related": related,
            "action": action,
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