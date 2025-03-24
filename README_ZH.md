# AI-RSS-Filter
[English](https://github.com/zuco1111/ai-rss-filter/blob/main/README.md)

## 描述
这个工具用来对RSS源的信息进行去重，通过LLM进行语义识别进行过滤，过滤后通过LLM生成摘要，便于用户快速了解文章简介

## 安装
```
git clone https://github.com/zuco1111/ai-rss-filter.git
cd ai-rss-filter
docker compose up -d
```
如果你是在 `arm64` 架构的设备上运行这个项目, 请编辑 `docker-compose.yml` 文件, 将文件中的 `amd64` 标签改成 `arm64`

## 配置
```
cd config
cp config.yaml.example config.yaml
```

## 配置项说明
```
global:
  # 数据想要存在哪个目录下
  data_dir: "/data"

  # 超过这个时间的数据将会被删除（单位：天）
  data_retention_days: 90

  cache:
    memory_enabled: true
    file_enabled: true
    db_enabled: true
    memory_ttl: 3600 # s
    file_ttl: 86400 # s
    db_ttl: 604800 # s

# 大语言模型配置
llm
  default_provider: "openai"
  # OpenAI
  openai:
    api_key: " "
    base_url: " "
    model: "gpt-4o-mini"
  # Gemini
  gemini:
    api_key: ""
    base_url: "https://generativelanguage.googleapis.com/v1"
    model: "gemini-pro"
  # Claude
  claude:
    api_key: ""
    base_url: "https://api.anthropic.com/v1"
    model: "claude-2"
  # Ollama
  ollama:
    base_url: "http://localhost:11434/api"
    model: "llama2"
  # Deepseek
  deepseek:
    api_key: ""
    base_url: "https://api.deepseek.com/v1"
    model: "deepseek-chat"
  # Azure
  azure:
    api_key: ""
    base_url: ""
    deployment_id: ""
    api_version: "2023-05-15"

# Web服务
web:
  host: "0.0.0.0"
  port: 8000

# RSS组
groups:
  # Example
  AI处理:
    # RSS URL
    urls:
      - "http://example.com/36kr"
      - "http://example.com/36kr"
    # 处理频率（单位：分钟）
    interval: 60
    # 去重（近3天内，标题相同的信息会被去重）
    deduplication:
      enabled: true
      days: 3
    # LLM 过滤
    filter:
      enabled: true
      prompt: "只保留与人工智能、大模型相关的文章"
    # 总结
    summary:
      enabled: true
      max_length: 150
```
## 使用
服务运行后，处理后的RSS订阅地址为： `127.0.0.1:8000/rss/组名` 

重置数据: `127.0.0.1:8000/rss/group_name?refresh=true`

清除缓存: `127.0.0.1:8000/rss/group_name?clear-cache`

手动更新:  `127.0.0.1:8000/rss/update/group_name`

## ⭐ Star History
[![Star History Chart](https://api.star-history.com/svg?repos=zuco1111/ai-rss-filter&type=Date)](https://star-history.com/#zuco1111/ai-rss-filter&Date)
