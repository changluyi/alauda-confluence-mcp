# Alauda Confluence MCP Server

一个用于 Confluence 集成的 Model Context Protocol (MCP) 服务器。

## 功能

- 搜索 Confluence 内容 (使用 CQL)
- 获取页面详情
- 列出所有空间
- 按标题获取页面
- 添加评论到页面
- 自动禁用代理设置（解决企业环境中的代理问题）

## 安装

### 方式一：使用 uvx (推荐)

```bash
# 添加到 Claude Code 配置
claude mcp add confluence -s user \
  -e CONFLUENCE_URL="https://your-confluence.example.com" \
  -e CONFLUENCE_USERNAME="your-username" \
  -e CONFLUENCE_PASSWORD="your-password" \
  -- uvx --from git+https://github.com/clyi/alauda-confluence-mcp.git alauda-confluence-mcp
```

### 方式二：使用本地安装

```bash
# 克隆仓库
git clone https://github.com/clyi/alauda-confluence-mcp.git
cd alauda-confluence-mcp

# 创建虚拟环境并安装依赖
python -m venv venv
source venv/bin/activate
pip install -e .

# 添加到 Claude Code 配置
claude mcp add confluence -s user \
  -e CONFLUENCE_URL="https://your-confluence.example.com" \
  -e CONFLUENCE_USERNAME="your-username" \
  -e CONFLUENCE_PASSWORD="your-password" \
  -- ./venv/bin/python ./src/alauda_confluence_mcp/server.py
```

## 配置

设置以下环境变量：

| 变量 | 描述 | 必需 |
|------|------|------|
| `CONFLUENCE_URL` | Confluence 服务器地址 | 是 |
| `CONFLUENCE_USERNAME` | Confluence 用户名 | 是 |
| `CONFLUENCE_PASSWORD` | Confluence 密码或 API Token | 是 |

## 工具列表

| 工具名称 | 描述 |
|---------|------|
| `search_content` | 使用文本搜索 Confluence 内容 |
| `get_page` | 获取指定页面的详细信息 |
| `get_page_by_title` | 按标题获取页面（需要空间 key） |
| `list_spaces` | 列出所有可用的 Confluence 空间 |
| `add_comment` | 添加评论到页面 |

## 使用示例

在 Claude Code 中，您可以直接调用以下工具：

### 搜索内容
```
搜索包含 "API 文档" 的 Confluence 页面
```

### 获取页面详情
```
获取页面 ID 为 12345 的详细信息
```

### 列出空间
```
列出所有 Confluence 空间
```

## 特性

- **自动禁用代理**: 解决企业环境中常见的代理连接问题
- **重试机制**: 自动重试失败的请求
- **简洁输出**: 格式化的 JSON 输出，便于阅读

## 许可证

MIT

## 作者

Changlu Yi (clyi)
