# DeployWatch 🚀

> **Production Readiness Agent** — Score any GitHub repo across 8 dimensions, get AI-powered recommendations, compare repos, and know exactly what to fix before you ship.

[![DeployWatch Score](https://img.shields.io/badge/DeployWatch-Live-brightgreen?style=flat-square&logo=github)](https://rishavraj379.github.io/DeployWatch)
[![GitHub Pages](https://img.shields.io/badge/Deployed-GitHub%20Pages-blue?style=flat-square)](https://rishavraj379.github.io/DeployWatch)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

---

## 🔗 Live Demo

**[rishavraj379.github.io/DeployWatch](https://rishavraj379.github.io/DeployWatch)**

Paste any public GitHub URL → get a full production readiness report in seconds.

---

## 🤔 What is DeployWatch?

Most developers push to production without knowing if their repo is actually ready. No health endpoints, no CI/CD, no license, no security policy — and they find out the hard way.

DeployWatch scans any GitHub repository using the live GitHub API and gives it a score out of 100 across **8 production readiness dimensions**. It tells you exactly what's missing and how to fix it.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **8-Dimension Scoring** | Activity, Documentation, Code Quality, Community, Reliability, Security, Performance, Innovation |
| **Live GitHub Data** | Fetches real-time data directly from the GitHub API — always up to date |
| **Recommendations** | Prioritised action items (high / medium / low) with exact steps to fix each issue |
| **Repo Compare** | Side-by-side comparison of two repos across all 8 dimensions |
| **Scan History** | Last 20 scans saved locally — click any to re-analyze |
| **Share Link** | Copy a URL that auto-runs the analysis for anyone who opens it |
| **Badge Generator** | Get a shields.io badge to embed in your README |
| **No Backend** | Runs entirely in the browser — no server, no login, no data stored |

---

## 📊 Scoring Breakdown

| Dimension | Weight | What it measures |
|-----------|--------|-----------------|
| Activity & Maintenance | 18% | Commit frequency, push recency, open issues |
| Documentation Quality | 15% | README, description, wiki, GitHub Pages |
| Code Quality | 15% | Language stack, repo size, branch setup |
| Community Engagement | 15% | Stars, forks, watchers |
| Reliability & Testing | 12% | CI/CD pipelines, issue management |
| Security & Best Practices | 10% | SECURITY.md, license, maintenance status |
| Performance | 8% | Repo size, visibility, issue overhead |
| Innovation & Impact | 7% | Age, topic tags, traction |

### Grade Scale

| Score | Grade | Label |
|-------|-------|-------|
| 85–100 | A+ | Production Ready |
| 75–84 | A | Almost There |
| 65–74 | B | Needs Attention |
| 50–64 | C | Improvements Needed |
| 35–49 | D | Not Production Safe |
| 0–34 | F | Critical Issues |

---

## 🛠 Tech Stack

- **Frontend** — Vanilla HTML, CSS, JavaScript (zero dependencies, zero frameworks)
- **Data** — GitHub REST API v3
- **Fonts** — Bebas Neue + DM Sans + DM Mono
- **Hosting** — GitHub Pages
- **Storage** — localStorage (scan history)

---

## 🚀 Run Locally

```bash
git clone https://github.com/RishavRaj379/DeployWatch.git
cd DeployWatch

# Just open the file — no server needed
open index.html
```

Or serve it locally:

```bash
npx serve .
# open http://localhost:3000
```

---

## ⚙️ Configuration

Open `index.html` and find this line near the top of the `<script>` tag:

```js
const GH_TOKEN = 'ghp_your_token_here';
```

Replace with your GitHub Personal Access Token (no scopes needed — public repo read is default). This raises the rate limit from **60 req/hr** to **5,000 req/hr**.

Get a token at: [github.com/settings/tokens](https://github.com/settings/tokens)

---

## 👥 Team

| Name | Role |
|------|------|
| [Amrit Mundlapudi] | Backend, Scoring Engine, Architecture |
| [Rishav Raj](https://github.com/RishavRaj379) | Frontend, Deployment, GitHub Pages |

---

## 🏆 Built For

**MLH Production Engineering Hackathon 2026**

---

## 📄 License

MIT — see [LICENSE](LICENSE)
