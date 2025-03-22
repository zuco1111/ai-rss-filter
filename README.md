# AI-RSS-Filter

## Description
This is a tool used to filter and merge RSS information sources. It will deduplicate the content with the same title in the first and then use LLM to filter out the content you don't want to see. In the last, it will generate a summary for each piece of content.

## Installation
```
git clone https://github.com/zuco1111/ai-rss-filter.git
cd ai-rss-filter
docker compose up -d
```

## Configuration
```
cd config
cp config.yaml.example config.yaml
```

## Configuration documentation
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
  # Example
  36kr_hot:
    # RSS URL
    urls:
      - "http://example.com/36kr"
      - "http://example.com/36kr"
    # Processing frequency (minutes) 
    interval: 60
    # Deduplication
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
