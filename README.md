# KashY_elk_docker

![Elastic Stack](https://img.shields.io/badge/Elastic_Stack-8.13.4-005571?style=for-the-badge&logo=elasticstack&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

> A lightweight, single-node **ELK stack** (Elasticsearch + Kibana) running in Docker — pre-configured with X-Pack security and automatic credential bootstrapping.

---

## Overview

**Skadi ELK** brings up a fully secured Elasticsearch + Kibana environment with a single command. A one-shot `setup` container handles credential initialization automatically so the stack is ready to use out of the box.

```
┌─────────────┐     bootstraps     ┌──────────────┐
│ skadi-setup │ ─────────────────► │  skadi-es    │  :9200
└─────────────┘                    │ Elasticsearch│
                                   └──────┬───────┘
                                          │
                                   ┌──────▼───────┐
                                   │ skadi-kibana │  :5601
                                   │    Kibana    │
                                   └──────────────┘
```

---

## Features

- **One-command startup** — `docker-compose up -d` and you're done
- **X-Pack security** — basic auth enforced out of the box
- **Persistent storage** — data volume survives container restarts
- **Memory-locked JVM** — prevents Elasticsearch heap from swapping
- **Health-gated dependencies** — Kibana only starts after setup succeeds
- **Fully configurable** — all settings in a single `.env` file

---

## Requirements

| | Minimum |
|---|---|
| Docker Engine | 20.10+ |
| Docker Compose | v2.x or v1.x |
| RAM | 4 GB (2 GB reserved for ES heap) |
| Disk | 10 GB free |
| OS | Linux · macOS · Windows (WSL2 / Docker Desktop) |

> **Linux only** — raise the virtual memory limit before starting:
> ```bash
> sudo sysctl -w vm.max_map_count=262144
> ```
> To persist across reboots, add `vm.max_map_count=262144` to `/etc/sysctl.conf`.

---

## Configuration

All settings are in [`skadi.env`](skadi.env):

| Variable | Default | Description |
|---|---|---|
| `ELASTIC_VERSION` | `8.13.4` | Elastic stack version |
| `ELASTIC_PASSWORD` | `Y2K_passwd` | Password for the `elastic` superuser |
| `KIBANA_PASSWORD` | `Y2K_passwd` | Password for the `kibana_system` internal user |
| `ES_PORT` | `9200` | Host port → Elasticsearch |
| `KIBANA_PORT` | `5601` | Host port → Kibana |
| `ES_HEAP` | `1g` | JVM heap size (keep ≤ half of available RAM) |

> **Security:** Change both passwords before exposing the stack on any shared network.

---

## Quick Start

**Windows**
```bat
run_docker.bat
```

**Linux / macOS / WSL**
```bash
docker-compose --env-file skadi.env up -d
```

### Startup sequence

```
1. skadi-es      → starts, waits until cluster is healthy
2. skadi-setup   → sets kibana_system password, then exits
3. skadi-kibana  → starts after setup completes successfully
```

Allow ~60 seconds on first boot for all services to become ready.

---

## Accessing the Stack

| Service | URL | Username | Password |
|---|---|---|---|
| Elasticsearch | http://localhost:9200 | `elastic` | `ELASTIC_PASSWORD` |
| Kibana | http://localhost:5601 | `elastic` | `ELASTIC_PASSWORD` |

**Quick health check:**
```bash
curl -u elastic:Y2K_passwd http://localhost:9200/_cluster/health?pretty
```

---

## Usage

```bash
# Start in the background
docker-compose --env-file skadi.env up -d

# Stream all logs
docker-compose --env-file skadi.env logs -f

# Stream logs for one service
docker-compose --env-file skadi.env logs -f elasticsearch

# Stop (keeps containers and data)
docker-compose --env-file skadi.env stop

# Remove containers (data volume preserved)
docker-compose --env-file skadi.env down

# Full reset — removes containers AND data
docker-compose --env-file skadi.env down -v
```

---

## Project Structure

```
kashy_elk_docker/
├── docker-compose.yml   # Service definitions
├── skadi.env            # Environment variables
├── run_docker.bat       # Windows one-click launcher
└── README.md
```

---

## Troubleshooting

<details>
<summary><strong>Kibana shows "server is not ready yet"</strong></summary>

Wait ~60 seconds after startup. The `setup` container must finish before Kibana can connect.

```bash
docker logs skadi-setup
```
</details>

<details>
<summary><strong>Elasticsearch exits immediately</strong></summary>

On Linux, `vm.max_map_count` is likely too low. Run:

```bash
sudo sysctl -w vm.max_map_count=262144
```

Also check that `ES_HEAP` is no more than half your available RAM.
</details>

<details>
<summary><strong>Port already in use</strong></summary>

Edit `skadi.env` and change `ES_PORT` or `KIBANA_PORT` to an available port.
</details>
