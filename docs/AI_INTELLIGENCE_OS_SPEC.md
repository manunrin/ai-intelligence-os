# AI Intelligence OS

## Enterprise AI Intelligence Operating System

Version: 1.0

Date: 2026


# 1. Project Overview


## Product Name

AI Intelligence OS


## Vision


Build a personal and enterprise-level AI intelligence platform.

The system automatically collects global information, analyzes it with AI agents, creates knowledge, manages tasks, and delivers actionable intelligence.


The system combines:

- AI News Intelligence
- Knowledge Management
- Multi-Agent Automation
- Personal Learning System
- Project Management Automation


The final goal:

Create an AI operating system that connects:

Information → Knowledge → Action


---

# 2. Core Objectives


The system should automatically:


## Information Layer

Collect:

- AI news
- Technology updates
- Research papers
- GitHub projects
- Company announcements


Sources:

- Official blogs
- RSS
- Search engines
- APIs
- Web pages


---

## Intelligence Layer


AI agents analyze:


- Importance
- Technical impact
- Business impact
- Trend analysis
- Relationship mapping


---

## Language Layer


Support:


Chinese:

中文


Japanese:

日本語


English:

English


Japanese learning features:


- Kanji
- Hiragana reading
- Pronunciation
- Vocabulary extraction


Example:


人工知能

じんこうちのう

Jinkō chinō

Artificial Intelligence



---

# 3. System Architecture


High level:


User

↓

Frontend

↓

Backend API

↓

Agent Runtime

↓

AI Agents

↓

Knowledge Layer

↓

External Services



---

# 4. Technology Stack


## Frontend


Framework:

Next.js


Language:

TypeScript


UI:

TailwindCSS

shadcn/ui



---

## Backend


Framework:

FastAPI


Language:

Python 3.12+



Components:


- API
- Authentication
- Business Logic
- Agent Interface



---

# Agent Framework


Primary:


LangGraph


Purpose:


- Multi-agent workflow
- State management
- Agent communication
- Human approval



---

# LLM Layer


Use model abstraction.


Technology:


LiteLLM Gateway



Supported models:


Cloud:

- GPT
- Claude
- Gemini


Local:

- Qwen
- DeepSeek
- Ollama models



---

# Database Layer


## Main Database


PostgreSQL


Stores:


- Users
- Articles
- Tasks
- Projects
- Agent states



---

## Vector Database


Qdrant


Purpose:


- Semantic search
- RAG
- Knowledge retrieval



---

## Cache


Redis



---

## Object Storage


MinIO


Stores:


- Documents
- HTML
- Images
- Files



---

# 5. Agent Architecture



## Supervisor Agent


Role:


Main coordinator.


Responsibilities:


- Receive goals
- Manage workflows
- Call other agents
- Monitor execution



---


## Research Agent


Responsibilities:


- Search information
- Find sources
- Verify sources



---


## Crawler Agent


Responsibilities:


- Web crawling
- RSS parsing
- Content extraction



---


## Analyst Agent


Responsibilities:


Analyze:


- Importance
- Technology category
- Business impact
- Trend



---


## Translator Agent


Responsibilities:


Generate:


- Chinese
- Japanese
- English


translations.



---


## Pronunciation Agent


Responsibilities:


Japanese learning support:


- Kanji reading
- Hiragana
- Vocabulary



---


## Knowledge Agent


Responsibilities:


Manage:


- Notion pages
- Knowledge structure
- Tags
- Relations



---


## Project Manager Agent


Responsibilities:


Manage:


- Asana tasks
- Project milestones
- Progress tracking


Workflow:


Information

↓

Knowledge

↓

Action



---


## Notification Agent


Responsibilities:


Send:


- WeChat
- Telegram
- Email



---

# 6. External Integrations



## Notion


Purpose:


Knowledge Management


Automatically create:


- News pages
- Technology notes
- Learning materials



---


## Asana


Purpose:


Task Management


Automatically create:


- Development tasks
- Learning tasks
- Research tasks



Task description must include:


- Related Notion URL
- Background
- Completion criteria



---


# 7. MCP Architecture



Use Model Context Protocol.


MCP Servers:


- Notion MCP
- Asana MCP
- Browser MCP
- GitHub MCP



Purpose:


Allow different AI agents to share tools.



---

# 8. Automation Workflow



Daily workflow:



Scheduler


↓

Research Agent


↓

Crawler Agent


↓

Analyst Agent


↓

Translator Agent


↓

Knowledge Agent


↓

Project Manager Agent


↓

Notification Agent



---

# 9. Docker Architecture



Local environment:



Docker Compose



Services:


- frontend
- backend
- agent-worker
- postgres
- redis
- qdrant
- minio
- nginx



---

# 10. Development Principles



## Enterprise Standard


Follow:


- Modular architecture
- Clean code
- API first
- Environment separation
- Automated testing
- Documentation first



---

# 11. Development Method



Claude Code must:


Before coding:


1. Read this document

2. Understand architecture

3. Create implementation plan

4. Wait for confirmation


Do not generate the entire system at once.



---

# 12. Future Expansion



Possible modules:


- Price Intelligence Agent

- Investment Research Agent

- Market Analysis Agent

- Personal Learning Agent

- Competitor Monitoring Agent

- AI Coding Agent



All modules share:


- Agent Runtime
- MCP
- Knowledge Base
- Task System



---

# End
