# AI-RSS-Filter
[中文](https://github.com/zuco1111/ai-rss-filter/blob/main/README_ZH.md)

## Description
This is a tool used to filter and merge RSS information sources. It will deduplicate the content with the same title in the first and then use LLM to filter out the content you don't want to see. In the last, it will generate a summary for each piece of content.

## Installation
```
git clone https://github.com/zuco1111/ai-rss-filter.git
cd ai-rss-filter
docker compose up -d
```
If you are running this porject in ARM64 architecture device, please edit `docker-compose.yml` file, replace `amd64` tag with `arm64`

## Configuration
```
cd config
cp config.yaml.example config.yaml
```

## Configuration Documentation
```
global:
  # Which path do you want to store the data in
  data_dir: "/data"

  # The data will be deleted after this time (day)
  data_retention_days: 90

  cache:
    memory_enabled: true
    file_enabled: true
    db_enabled: true
    memory_ttl: 3600 # s
    file_ttl: 86400 # s
    db_ttl: 604800 # s

# LLM Configuration
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

# Web Sever
web:
  host: "0.0.0.0"
  port: 8000

# RSS Group
groups:
  # Group1，`36kr_hot` is the group name
  36kr_hot:
    # RSS URL
    urls:
      - "http://example.com/36kr"
      - "http://example.com/36kr"
    # Processing frequency (minutes) 
    interval: 60
    # Deduplication (Content with the same title in the past three days will be deduplicated)
    deduplication:
      enabled: true
      days: 3
    # LLM Filter
    filter:
      enabled: true
      prompt: "只保留与人工智能、大模型相关的文章"
    # Summary
    summary:
      enabled: true
      max_length: 150
```
## Usage
Once upon you start docker server, the procceed RSS subscription link is `127.0.0.1:8000/rss/group_name`

Refresh Data: `127.0.0.1:8000/rss/group_name?refresh=true`

Clear Cache: `127.0.0.1:8000/rss/group_name?clear-cache`

Manual Update:  `127.0.0.1:8000/rss/update/group_name`

## ⭐ Star History
[![Star History Chart](https://api.star-history.com/svg?repos=zuco1111/ai-rss-filter&type=Date)](https://star-history.com/#zuco1111/ai-rss-filter&Date)

