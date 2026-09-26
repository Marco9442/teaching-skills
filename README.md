# Teaching Skills

大学教学用的一组技能。内容来自 [YujxZJCN/teaching-skills](https://github.com/YujxZJCN/teaching-skills)，每 6 小时自动同步。

每个技能是一个独立目录，可以单独安装。它要读的说明已经放在自己的目录里，不依赖仓库里的其他技能。

许可是 MIT，版权归上游作者 Jiaxing Yu。

## 安装

克隆后，把要用的目录放进技能文件夹：

```bash
git clone https://github.com/Marco9442/teaching-skills.git
ln -s "$PWD/teaching-skills/lesson-builder" ~/.grok/skills/lesson-builder
```

Claude Code 用 `~/.claude/skills/`，放法相同。

GitHub 上的仓库会自己更新。电脑上的副本要自己 `git pull` 才会跟上。

## 技能

| 目录 | 做什么 |
| --- | --- |
| `teaching-pipeline` | 串起一门课从设计到复盘的全过程 |
| `course-designer` | 定学习成果、考核方案、学期安排和大纲 |
| `lesson-builder` | 备课：教案、讲稿、课件提纲、课堂活动 |
| `assessment-architect` | 出考试、测验、评分量表和项目任务书 |
| `submission-auditor` | 按你的要求检查学生提交的作业 |
| `student-mentor` | 写反馈、沟通困难学生、推荐信 |
| `teaching-reflector` | 看教学评价，整理教学反思和陈述 |
| `deck-studio` | 把课件提纲做成幻灯片 |
| `lab-forge` | 做实验讲义、数据和自动评分 |
| `media-scripter` | 写录课脚本和分镜 |
| `course-publisher` | 写课程通知、周邮件，整理课程站点 |
| `ta-coordinator` | 安排助教分工和评分校准 |
| `accreditation-mapper` | 把成果对照到认证标准 |
| `bilingual-courseware` | 做中英对照的课件和术语表 |
| `cohort-analyst` | 根据学情调整后续教学 |

直接对助手说你要做什么即可，例如「帮我准备下周二的课」。技能目录里的 `SKILL.md` 写了它能做的事和它不做的事。

## 自动更新

定时任务只从上游取技能，并覆盖本仓库里的技能目录。`README.md` 和 `.github` 会保留。

上游长时间没有新内容时，大约每三周会有一次空提交，用来避免 GitHub 关掉定时任务。
