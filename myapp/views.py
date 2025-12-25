from collections import Counter
from urllib.parse import urlencode
import json
import requests
import re

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Avg
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings

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
    # 轮播图：选择评分最高的5部电影
    carousel_movies = Movie.objects.filter(score__isnull=False).order_by("-score")[:5]
    top_rated = Movie.objects.order_by("-score")[:8]
    latest = Movie.objects.order_by("-date")[:8]
    recommend = _personalized_recommendations(request.user, limit=6) if request.user.is_authenticated else _hot_recommendations(limit=6)
    return render(
        request,
        "home/index.html",
        {
            "carousel_movies": carousel_movies,
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
        recs = _personalized_recommendations(request.user, limit=8)
        personalized = recs is not None and len(recs) > 0
    if not recs:
        recs = _hot_recommendations(limit=8)
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


# ==================== AI推荐相关函数 ====================

def _format_movie_info(movie, user_rating=None):
    """格式化电影信息用于AI分析"""
    return {
        "title": movie.title,
        "type": movie.type or "未知",
        "region": movie.region or "未知",
        "actors": movie.actors or "未知",
        "score": movie.score,
        "rating": user_rating,  # 用户评分
    }


def _get_user_preference_data(user, limit=10):
    """获取用户偏好数据用于AI分析"""
    # 收藏的10部电影
    favorites = (
        UserAction.objects.filter(user=user, is_favorite=True)
        .select_related("movie")
        .order_by("-updated_at")[:limit]
    )
    
    # 评分最高的10部电影（按用户评分排序）
    top_rated = (
        UserAction.objects.filter(user=user, rating__isnull=False)
        .select_related("movie")
        .order_by("-rating", "-updated_at")[:limit]
    )
    
    return {
        "favorites": [_format_movie_info(action.movie, action.rating) for action in favorites],
        "top_rated": [_format_movie_info(action.movie, action.rating) for action in top_rated],
    }


def _build_recommendation_prompt(user_data):
    """构建推荐请求的prompt"""
    favorites_text = ""
    if user_data['favorites']:
        favorites_text = "用户收藏的电影：\n" + "\n".join([
            f"- {m['title']}（类型：{m['type']}，地区：{m['region']}，豆瓣评分：{m['score']}）"
            for m in user_data['favorites']
        ])
    
    top_rated_text = ""
    if user_data['top_rated']:
        top_rated_text = "用户评分最高的电影：\n" + "\n".join([
            f"- {m['title']}（类型：{m['type']}，地区：{m['region']}，用户评分：{m['rating']}分，豆瓣评分：{m['score']}）"
            for m in user_data['top_rated']
        ])
    
    prompt = f"""你是一位专业的电影推荐专家。基于用户的观影偏好，请推荐5-8部电影。

{favorites_text}

{top_rated_text}

请分析用户的观影偏好（类型、地区、风格等），然后：
1. 推荐5-8部符合用户口味的电影
2. 为每部推荐电影提供简短的推荐理由（20-30字）
3. 推荐理由要说明为什么这部电影适合这个用户

请以JSON格式返回，格式如下：
{{
    "analysis": "对用户观影偏好的简短分析（50字以内）",
    "recommendations": [
        {{
            "title": "电影标题（准确的电影名称）",
            "type": "电影类型（如：剧情、喜剧、动作等）",
            "region": "电影地区（如：美国、中国、日本等）",
            "score": 8.5,
            "reason": "推荐理由（20-30字）"
        }}
    ]
}}

注意：
1. 只返回JSON，不要其他文字
2. 电影标题要准确
3. type和region字段尽量填写，如果不知道可以填"未知"
4. score字段填写豆瓣评分（0-10之间的数字），如果不知道可以填null
5. 推荐理由要具体说明为什么适合这个用户"""
    
    return prompt


def _call_qwen_api(prompt):
    """调用通义千问API"""
    api_key = getattr(settings, 'QWEN_API_KEY', '')
    api_url = getattr(settings, 'QWEN_API_URL', 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation')
    
    if not api_key:
        return None, None, "API Key未配置"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "qwen-turbo",  # 或 "qwen-plus", "qwen-max"
        "input": {
            "messages": [
                {
                    "role": "system",
                    "content": "你是一位专业的电影推荐专家，擅长分析用户观影偏好并推荐合适的电影。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        },
        "parameters": {
            "temperature": 0.7,
            "max_tokens": 2000
        }
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        # 解析通义千问的响应格式（支持多种格式）
        content = None
        raw_response = str(result)  # 保存原始响应用于调试
        
        # 格式1: output.text (新版本API)
        if 'output' in result and 'text' in result['output']:
            content = result['output']['text']
        # 格式2: output.choices[0].message.content (旧版本API)
        elif 'output' in result and 'choices' in result['output']:
            if len(result['output']['choices']) > 0:
                if 'message' in result['output']['choices'][0]:
                    content = result['output']['choices'][0]['message']['content']
                elif 'text' in result['output']['choices'][0]:
                    content = result['output']['choices'][0]['text']
        
        if content:
            return content, raw_response, None
        else:
            return None, raw_response, f"API响应格式错误，无法提取内容。响应: {result}"
    except requests.exceptions.RequestException as e:
        return None, None, f"API请求失败: {str(e)}"
    except Exception as e:
        return None, None, f"API调用异常: {str(e)}"


def _extract_json_from_response(text):
    """从AI响应中提取JSON"""
    # 尝试直接解析
    try:
        return json.loads(text)
    except:
        pass
    
    # 尝试提取JSON块
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except:
            pass
    
    # 尝试提取```json代码块
    json_block_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_block_match:
        try:
            return json.loads(json_block_match.group(1))
        except:
            pass
    
    # 尝试提取```代码块
    code_block_match = re.search(r'```\s*(\{.*?\})\s*```', text, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except:
            pass
    
    return None


@login_required
def ai_recommend_api(request):
    """AI推荐API"""
    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)
    
    user = request.user
    
    # 获取用户偏好数据
    user_data = _get_user_preference_data(user)
    
    # 检查是否有足够的数据
    if not user_data['favorites'] and not user_data['top_rated']:
        return JsonResponse({
            "success": False,
            "error": "数据不足",
            "message": "请先收藏或评分一些电影，以便AI分析你的观影偏好"
        }, status=400)
    
    # 构建prompt
    prompt = _build_recommendation_prompt(user_data)
    
    # 调用AI API
    ai_response, raw_response, error_msg = _call_qwen_api(prompt)
    
    if not ai_response:
        return JsonResponse({
            "success": False,
            "error": "API调用失败",
            "message": error_msg or "请稍后重试",
            "raw_response": raw_response if raw_response else None  # 返回原始响应用于调试
        }, status=500)
    
    # 解析AI返回的JSON
    try:
        ai_data = _extract_json_from_response(ai_response)
        
        if not ai_data:
            # 如果JSON解析失败，返回原始回答和错误信息
            return JsonResponse({
                "success": False,
                "error": "JSON解析失败",
                "message": "AI返回格式不正确，但已显示原始回答",
                "raw_ai_response": ai_response,  # 返回原始AI回答
                "raw_api_response": raw_response  # 返回完整API响应
            }, status=500)
        
        # 直接使用AI返回的电影信息，不查找数据库
        recommendations = []
        for rec in ai_data.get('recommendations', []):
            title = rec.get('title', '').strip()
            if not title:
                continue
            
            # 尝试在数据库中查找（可选，用于获取海报等额外信息）
            movie = Movie.objects.filter(title=title).first()
            if not movie:
                movie = Movie.objects.filter(title__icontains=title).first()
            
            # 使用AI返回的数据，如果数据库中有则补充海报等信息
            recommendation = {
                "id": movie.id if movie else None,
                "title": title,
                "poster": movie.poster if movie and movie.poster else "",
                "score": rec.get('score') or (movie.score if movie else None),
                "type": rec.get('type') or (movie.type if movie else "") or "未知",
                "region": rec.get('region') or (movie.region if movie else "") or "未知",
                "reason": rec.get('reason', '推荐给你')
            }
            recommendations.append(recommendation)
        
        # 构建返回数据，包含原始回答
        response_data = {
            "success": True,
            "analysis": ai_data.get('analysis', '基于你的观影偏好，为你推荐以下电影'),
            "recommendations": recommendations,
            "raw_ai_response": ai_response,  # 添加原始AI回答
        }
        
        if not recommendations:
            # 即使没有推荐，也返回原始回答
            response_data.update({
                "success": False,
                "error": "无推荐数据",
                "message": "AI未返回推荐电影，但已显示AI的原始回答",
            })
            return JsonResponse(response_data, status=404)
        
        return JsonResponse(response_data)
    except json.JSONDecodeError as e:
        # JSON解析失败时，返回原始回答
        return JsonResponse({
            "success": False,
            "error": "JSON解析失败",
            "message": f"解析错误: {str(e)}，但已显示原始回答",
            "raw_ai_response": ai_response,  # 返回原始AI回答
            "raw_api_response": raw_response  # 返回完整API响应
        }, status=500)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": "处理失败",
            "message": str(e),
            "raw_ai_response": ai_response if 'ai_response' in locals() else None,
            "raw_api_response": raw_response if 'raw_response' in locals() else None
        }, status=500)