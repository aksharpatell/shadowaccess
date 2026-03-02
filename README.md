# 🛡️ ShadowAccess

**ShadowAccess** is a security analysis tool that evaluates **GitHub repository and organization access risk** by inspecting permissions, branch protection, and ownership controls — while explicitly accounting for **limited API visibility**.

Unlike many tools that over-promise certainty, ShadowAccess separates **risk severity** from **confidence**, mirroring how real-world security platforms operate under partial data.

ShadowAccess helps small engineering teams understand who actually has access to their code before it becomes a breach.
---

## Demo & Screenshots

Demo: shadowaccess.vercel.app

API: shadowaccess-zrjr.onrender.com

### Home Page
The landing page explains the purpose of ShadowAccess and allows users to scan a GitHub username or organization.

![Home Page](screenshots/Home%20Page.png)

---

### Risk Scoring Model
Explanation of the 0–100 normalized risk scale and how confidence-aware scoring works under limited visibility.

![Scoring Details](screenshots/Scoring%20Details.png)

---

### Security Scanning Output
Results view showing repository risk scores, visibility level, and export options.

![Security Scanning Output](screenshots/Security%20Scanning%20Output.png)

---

## Problem

GitHub repositories frequently accumulate **silent access risks**:
- excessive admin privileges  
- missing branch protection  
- no CODEOWNERS enforcement  
- single-maintainer “bus factor” risk  

Most developers — especially students and early teams — have no visibility into these risks until something goes wrong.

Existing tools often:
- assume full access they don’t actually have  
- hide uncertainty  
- provide misleading “safe” labels  

---

## Solution

ShadowAccess analyzes repositories using **available GitHub APIs** and produces:

- a **0–100 normalized risk score**
- a **visibility / confidence label**
- concrete, human-readable risk explanations
- exportable JSON reports

When GitHub restricts access, ShadowAccess **does not guess silently** — it falls back to **conservative heuristic scoring** and clearly labels the result.

---

## 🔍 How It Works

ShadowAccess evaluates repositories using multiple signals:

### 🔐 Access & Permissions
- collaborator roles (admin / maintain / write)
- privilege concentration
- single-maintainer risk

### 🧾 CODEOWNERS
- existence of CODEOWNERS file
- ownership coverage enforcement

### 🧠 Confidence Model
ShadowAccess separates **risk** from **confidence**:

| Visibility Label | Meaning |
|-----------------|---------|
| **FULL VISIBILITY** | GitHub APIs allowed direct inspection |
| **LIMITED VISIBILITY** | Access restricted — score conservatively inferred |

> Visibility indicates **confidence in the data**, not security quality.

## 🛠️ Tech Stack

### Backend
- Python
- Flask
- GitHub REST API

### Frontend
- React (Vite)
- Custom dark UI
- No UI frameworks

---
