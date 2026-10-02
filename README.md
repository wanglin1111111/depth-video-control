# depth-video-control

深度驱动的 AI 视频控制技能：用实拍视频抽出的**深度图/深度序列**当空间骨架约束 AI 生成。

一句话：**AI 视频的控制权，正从"文字提示词"前移到"真实空间结构"。** 别让 AI 猜空间，把空间直接喂给它。

## 解决什么

| 痛点 | 本技能的做法 |
|---|---|
| 复杂站位/遮挡/远近关系，提示词反复描述仍不稳定 | 深度图控制：实拍抽深度，人物前后/遮挡/远近一次复刻 |
| 手持抖动、推拉摇移等"不稳定镜头"提示词永远写不准 | 深度视频驱动：实拍深度序列天然带运动信息，直接还原运镜 |
| 提示词又写构图又写风格，越长越抽卡 | 提示词降级三要素：主体特征/材质风格/光线氛围，构图运镜交给深度 |
| 算力成本过高，空间推理烧卡 | 算力替代：低成本结构输入替代高算力模型的空间推理 |

## 与其他 AI 视频技能的关系

与 `ai-video-prompt-studio`（分镜表/提示词工程）互补而非替代：那边解决"文字怎么说"，这边解决"空间由谁托底"。走深度路线的镜头，提示词按本技能的三要素规则写，再按需接入分镜表流程。

## 安装

复制本目录到 `~/.agents/skills/`（或你的 Skill 加载路径）即可。

## 自检

```bash
python scripts/validate.py tests/sample_good.json   # 必须 exit 0
python scripts/validate.py tests/sample_bad.json    # 必须 exit 1
```

## 结构

```
SKILL.md                          工作流入口（一条主线 + 7 步流程 + 硬规则）
references/shot-routing.md        镜头路由决策表（深度路线 vs 抽卡路线）
references/workflow.md            实拍要求 + 深度估计工具链与验收标准
references/prompt-slim.md         三要素提示词模板 + 降级前后对照
references/gotchas.md             四类崩点清单、实拍要求、常见翻车与对策
scripts/validate.py               镜头计划六维校验器（exit 0/1/2）
tests/sample_good.json            通过基准
tests/sample_bad.json             拦截基准（崩点硬上/三要素缺失/构图词混入…）
docs/methodology.md               方法论全文（奥卡姆剃刀提炼 + 现实行动指南）
```
