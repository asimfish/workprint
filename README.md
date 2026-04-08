# Workprint

**Distill real behavior traces into executable AI skills.**

> Unlike nuwa-skill (analyzes writings) and yourself-skill (analyzes diaries),  
> Workprint distills what engineers **actually do** — commit history, shell patterns, workflows.  
> Every pattern is backed by empirical behavioral evidence, not inferred from self-reports.

---

## The Difference

| Tool | Input | Output | Core Question |
|------|-------|--------|---------------|
| **nuwa-skill** | Public writings, interviews | Cognitive framework | How do they **think**? |
| **yourself-skill** | Your diary + chats | Personality model | How do you **talk**? |
| **Workprint** | Real traces (git, shell, notes) | Behavioral skill | How do they **work**? |

---

## 已蒸馏工程师 (18 engineers)

Workprint has analyzed the real GitHub commit behavior of 18 world-class engineers.  
Each entry is backed by actual commit evidence — not interviews, not articles.

### AI / Machine Learning

| Engineer | Domain | Repo Analyzed | Key Behavioral Pattern |
|----------|--------|---------------|------------------------|
| 🔥 **Andrej Karpathy** | AI Education | [karpathy/nanoGPT](https://github.com/karpathy/nanoGPT) | 初始大爆炸发布 + 极简 commit 消息，代码即教材 |
| 🔥 **George Hotz (geohot)** | AI Framework | [tinygrad/tinygrad](https://github.com/tinygrad/tinygrad) | 极速迭代，删代码是主要工作，随性风格 |
| 🔥 **François Chollet** | AI Framework | [keras-team/keras](https://github.com/keras-team/keras) | API 可用性优先，兼容性是硬约束 |
| ⭐ **Sebastian Raschka** | AI Education | [rasbt/LLMs-from-scratch](https://github.com/rasbt/LLMs-from-scratch) | 章节驱动 commit，读者反馈即时响应 |
| ⭐ **Phil Wang (lucidrains)** | AI Research | [lucidrains/denoising-diffusion-pytorch](https://github.com/lucidrains/denoising-diffusion-pytorch) | 论文名即 commit 消息，100+ 仓库并行维护 |
| ⭐ **Simon Willison** | AI Tools | [simonw/llm](https://github.com/simonw/llm) | Issue 驱动，博客文章 → 代码，插件优先 |
| **Thomas Wolf** | AI Ecosystem | [huggingface/transformers](https://github.com/huggingface/transformers) | 新论文上线即实现，统一 API 标准 |
| **Jeremy Howard** | AI Education | [fastai/fastai](https://github.com/fastai/fastai) | notebook-first 开发，用户体验 > 性能 |

### Systems / Infrastructure

| Engineer | Domain | Repo Analyzed | Key Behavioral Pattern |
|----------|--------|---------------|------------------------|
| 🔥 **Linus Torvalds** | OS Kernel | [torvalds/linux](https://github.com/torvalds/linux) | Merge 驱动工作流，极短消息，低 bug 率 |
| ⭐ **Salvatore Sanfilippo (antirez)** | Database | [redis/redis](https://github.com/redis/redis) | 设计意图写进 body，原子 commit，拒绝过度工程 |
| **Mitchell Hashimoto** | Infrastructure | [hashicorp/vagrant](https://github.com/hashicorp/vagrant) | 文档与代码同步，详细 body，大量 docs commit |

### Programming Languages / Web

| Engineer | Domain | Repo Analyzed | Key Behavioral Pattern |
|----------|--------|---------------|------------------------|
| **Guido van Rossum** | Language Design | [python/cpython](https://github.com/python/cpython) | Issue 编号前缀，60%+ commit 附 body 解释 why |
| 🔥 **David Heinemeier Hansson (DHH)** | Web Framework | [rails/rails](https://github.com/rails/rails) | 口语化有态度，大功能一次提交，不用规范前缀 |
| 🔥 **Evan You** | Frontend | [vuejs/core](https://github.com/vuejs/core) | 严格 Conventional Commits，超短消息，fix 为主 |
| **TJ Holowaychuk** | Web Framework | [expressjs/express](https://github.com/expressjs/express) | 平均 25 字符，0% body，极简到底 |

### Open Source Ecosystem

| Engineer | Domain | Repo Analyzed | Key Behavioral Pattern |
|----------|--------|---------------|------------------------|
| ⭐ **Sindre Sorhus** | OSS Tools | [sindresorhus/got](https://github.com/sindresorhus/got) | 高 chore 比例，TypeScript 迁移先行者 |
| **Dan Abramov** | Frontend | [facebook/react](https://github.com/facebook/react) | 教育性消息，TDD 节奏，65%+ commit 有 body |
| **Jared Palmer** | Dev Tools | [jaredpalmer/formik](https://github.com/jaredpalmer/formik) | Conventional Commits + 语义化版本，DX 优先 |

---

## What You Learn

Each engineer teaches a different **behavioral principle**:

```
Karpathy  → 教育优先，用最少代码说明最深思想
geohot    → 极速迭代，删除即优化，速度即护城河
Chollet   → API 设计即产品设计，用户体验是硬约束
antirez   → 简洁是美德，commit body 是设计文档
Torvalds  → 代码不需要解释，行为是最好的文档
Evan You  → 规范即标准，小 commit 快速响应
simonw    → 写作驱动开发，issue 是代码的起点
```

---

## Quick Start

```bash
# Install
pip install git+https://github.com/asimfish/workprint.git

# Analyze your own traces
workprint analyze --git-dir ~/projects/myapp --output my_workprint.md

# Or use DevTwin (full version with continuous learning)
# http://localhost:5173/workprint
```

---

## How It Works

```
GitHub Commits → Pattern Extraction → Behavioral Evidence → SKILL.md
     ↓                  ↓                    ↓                  ↓
Real traces    Statistical mining    Concrete examples    Executable skill
```

**Key difference from nuwa-skill**: We don't analyze what they *said* in interviews.  
We analyze what they *did* in their repos. Commit messages don't lie.

---

## DevTwin Integration

Workprint is the **export layer** of [DevTwin](https://github.com/asimfish/ShrimpFlow) —  
a continuous behavioral learning system that mines your own work patterns in real time.

```
DevTwin: Shadow → Mirror → Brain → Workprint
                                      ↓
                               Your SKILL.md
```

---

## Contributing

Want to add a new engineer to the catalog? Open a PR with:
1. Their GitHub login and primary repo
2. Pre-analyzed patterns (backed by real commit evidence)
3. A one-line tagline summarizing their behavioral philosophy

---

## License

MIT
