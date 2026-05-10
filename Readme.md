# AI Process Bottleneck

An AI-powered backend system for intelligent workflow automation, semantic processing, local LLM inference, and scalable AI integration.

This project is designed as a production-style AI infrastructure backend that combines:

* Semantic embeddings
* Local LLM inference using Ollama
* FastAPI backend architecture
* Vector-ready processing pipeline
* Modular AI service structure
* Offline-first AI capabilities

---

# Overview

AI Process Bottleneck is built to simulate a real-world AI infrastructure system that can:

* Process and embed text data
* Run local AI models offline
* Provide scalable API-based AI services
* Support future vector search and RAG systems
* Serve as a foundation for intelligent workflow automation

The project focuses heavily on:

* Clean architecture
* Production-ready backend structure
* Modular AI pipelines
* Local-first AI deployment
* Performance optimization

---

# Core Features

## Semantic Embeddings

Uses Sentence Transformers for high-quality semantic embeddings.

Current embedding model:

* `sentence-transformers/all-MiniLM-L6-v2`

Capabilities:

* Semantic similarity
* Text understanding
* Embedding generation
* Vector database compatibility
* RAG-ready architecture

---

## Local LLM Inference with Ollama

Integrated local AI inference using Ollama.

Current recommended model:

* `phi3:mini`

Low-RAM fallback:

* `tinyllama`

Benefits:

* Fully offline AI inference
* No API cost
* Local data privacy
* Fast local responses
* Production-ready architecture

---

## FastAPI Backend

Modern asynchronous backend architecture using FastAPI.

Features:

* Async endpoints
* Scalable structure
* High performance
* Easy API testing
* Swagger documentation
* Production deployment ready

---

## Modular AI Architecture

The project follows a clean modular structure:

```text
src/
 ├── genai/
 │    ├── embeddings/
 │    ├── offline/
 │    ├── config/
 │    ├── shared/
 │    └── model_loader.py
 │
 ├── routes/
 ├── services/
 ├── database/
 └── utils/
```

This structure allows:

* Easy scaling
* Better maintainability
* Team collaboration
* Separation of concerns
* Production-level organization

---

# Tech Stack

## Backend

* Python
* FastAPI
* Uvicorn

## AI / ML

* Sentence Transformers
* Hugging Face Transformers
* Ollama
* Local LLMs

## Database

* PostgreSQL
* SQLAlchemy

## Async & Networking

* aiohttp
* Async Python

---

# System Architecture

```text
User Request
     ↓
FastAPI Backend
     ↓
AI Processing Layer
     ├── Embedding Engine
     ├── Ollama LLM Engine
     └── Semantic Processing
     ↓
Response Generation
     ↓
API Response
```

---

# Installation

## 1. Clone Repository

```bash
git clone <your-repository-url>
cd ai-process-bottleneck
```

---

## 2. Create Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / Mac

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install Requirements

```bash
pip install -r requirements.txt
```

---

# Ollama Setup

## Install Ollama

Official Website:

* [https://ollama.com](https://ollama.com)

---

## Run Recommended Model

```bash
ollama run phi3:mini
```

If your system has low RAM:

```bash
ollama run tinyllama
```

---

# Environment Configuration

Create a `.env` file:

```env
# ============================================================
# DATABASE
# ============================================================

POSTGRES_DB=your_db_name
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
POSTGRES_PORT=5432

# ============================================================
# MODEL PROVIDER
# ============================================================

DEFAULT_PROVIDER=ollama

# ============================================================
# OLLAMA
# ============================================================

OLLAMA_MODEL=phi3:mini
OLLAMA_BASE_URL=http://localhost:11434

# ============================================================
# OPENAI (OPTIONAL)
# ============================================================

OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
```

---

# Running the Backend

Start the FastAPI server:

```bash
python -m uvicorn main:app --reload
```

Backend will run at:

```text
http://127.0.0.1:8000
```

Swagger API docs:

```text
http://127.0.0.1:8000/docs
```

---

# Example Startup Logs

```text
✅ Embedding model loaded
✅ Ollama connected
🚀 Backend ready
```

---

# Current Capabilities

The backend currently supports:

* Embedding generation
* Local AI inference
* Async API handling
* Modular AI services
* Offline-first architecture
* Fast semantic processing

---

# Planned Features

Upcoming roadmap includes:

## Retrieval-Augmented Generation (RAG)

* Vector database integration
* Semantic document retrieval
* Context-aware AI responses

## Workflow Intelligence

* AI workflow optimization
* Bottleneck detection
* Automated recommendations

## AI Agent System

* Multi-agent orchestration
* Tool calling
* Autonomous task execution

## Vector Search

* pgvector integration
* Similarity search
* Semantic indexing

## Monitoring & Analytics

* AI performance tracking
* Request analytics
* Usage metrics

---

# Why This Project?

This project was built to explore and implement:

* Real-world AI backend engineering
* Production-grade AI system architecture
* Local AI deployment
* Scalable semantic systems
* AI infrastructure design

It is designed as both:

* A learning-focused AI infrastructure project
* A scalable foundation for future AI products

---

# Performance Focus

Key optimization areas:

* Model preloading
* Async processing
* Modular architecture
* Reduced API latency
* Offline AI execution
* Scalable backend structure

---

# Security & Privacy

Benefits of local AI execution:

* No external API dependency
* Data remains local
* Reduced operational cost
* Offline processing capability
* Better privacy control

---

# Requirements

Recommended system:

* Python 3.10+
* 8GB+ RAM recommended
* Ollama installed
* PostgreSQL installed

Minimum system:

* Python 3.10+
* 4GB RAM
* tinyllama model

---

# API Testing

You can test APIs using:

* FastAPI Swagger Docs
* Postman
* cURL
* Frontend integration

---

# Future Vision

The long-term vision for this project is to evolve into:

* AI workflow intelligence platform
* Enterprise AI orchestration system
* Autonomous AI processing engine
* Scalable AI infrastructure layer

---

# Contributing

Contributions, improvements, and feature suggestions are welcome.

Potential contribution areas:

* RAG pipelines
* Vector databases
* Agent systems
* AI orchestration
* Performance optimization
* Frontend dashboards

---

# License

This project is open-source and available under the MIT License.

---

# Author

Built with a focus on:

* AI engineering
* Backend architecture
* Local AI systems
* Scalable infrastructure
* Production-ready development

---

# Final Notes

This project demonstrates:

* Real AI backend engineering
* Local LLM integration
* Semantic AI pipelines
* Modern async Python architecture
* Production-oriented AI infrastructure

It serves as a strong foundation for building advanced AI systems, RAG applications, and autonomous AI workflows.
