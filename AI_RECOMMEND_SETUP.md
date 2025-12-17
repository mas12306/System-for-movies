# AI推荐功能配置说明

## 功能概述

AI推荐功能使用通义千问大语言模型，基于用户的收藏和评分记录，生成个性化电影推荐。

## 配置步骤

### 1. 获取通义千问API Key

1. 访问 [阿里云DashScope控制台](https://dashscope.console.aliyun.com/)
2. 注册/登录账号
3. 创建API Key
4. 复制API Key（格式类似：`sk-xxxxxxxxxxxxx`）

### 2. 配置API Key

打开 `DjangoProject/settings.py` 文件，找到以下配置：

```python
# ==================== AI推荐配置 ====================
# 通义千问API配置
# 获取API Key: https://dashscope.console.aliyun.com/
QWEN_API_KEY = ''  # 请在此处填入你的通义千问API Key
QWEN_API_URL = 'https://dashscope.aliyun.com/api/v1/services/aigc/text-generation/generation'
```

将你的API Key填入 `QWEN_API_KEY`：

```python
QWEN_API_KEY = 'sk-你的API密钥'
```

### 3. 可选配置

如果需要使用不同的模型，可以修改 `_call_qwen_api` 函数中的 `model` 参数：

- `qwen-turbo`：快速响应，成本较低（默认）
- `qwen-plus`：平衡性能和成本
- `qwen-max`：最强性能，成本较高

## 使用方法

1. 确保用户已登录
2. 用户需要至少收藏或评分一些电影（建议至少5部）
3. 访问推荐页面（`/recommend/`）
4. 点击"生成推荐"按钮
5. 等待AI分析（通常需要5-15秒）
6. 查看AI推荐的电影和推荐理由

## 工作原理

1. **数据收集**：系统收集用户收藏的10部电影和评分最高的10部电影
2. **Prompt构建**：将这些信息整理成结构化的提示词
3. **AI分析**：调用通义千问API，让AI分析用户偏好
4. **结果解析**：解析AI返回的JSON，提取推荐电影和理由
5. **数据库匹配**：根据电影标题在数据库中查找匹配的电影
6. **结果展示**：在前端展示推荐结果

## 故障排查

### 问题1：提示"API Key未配置"
- 检查 `settings.py` 中的 `QWEN_API_KEY` 是否已填写
- 确保API Key格式正确

### 问题2：提示"API调用失败"
- 检查网络连接
- 确认API Key是否有效
- 检查API余额是否充足

### 问题3：提示"数据不足"
- 用户需要先收藏或评分至少几部电影
- 建议至少5部电影才能生成有效推荐

### 问题4：提示"未找到匹配电影"
- AI推荐的电影可能在数据库中不存在
- 可以重试，AI会推荐其他电影

## 成本说明

- 通义千问API按调用次数和token数量计费
- `qwen-turbo` 模型相对便宜
- 每次推荐大约消耗 500-1000 tokens
- 建议设置API调用频率限制，避免过度使用

## 安全建议

1. **不要将API Key提交到Git仓库**
   - 使用环境变量或配置文件（不提交到版本控制）
   - 或使用 `.env` 文件（添加到 `.gitignore`）

2. **限制API调用频率**
   - 可以在视图中添加频率限制
   - 使用Django的缓存机制

## 进阶优化

1. **缓存推荐结果**：相同用户的推荐结果可以缓存24小时
2. **异步处理**：使用Celery处理长时间API调用
3. **降级策略**：API失败时回退到传统推荐算法
4. **推荐理由优化**：根据实际效果调整prompt

