<h1 align="center">AI Observatory</h1>

<p align="center">
  <strong>本地分析你的 AI 编程用量 —— 并告诉你该改什么。</strong><br>
  <sub>为东南亚与中国开发者的真实付费方式而设计：包月套餐、分时段计价的 token、以及不是美元的货币。</sub>
</p>

<p align="center">
  <a href="#快速开始">快速开始</a> ·
  <a href="#有什么不一样">有什么不一样</a> ·
  <a href="#隐私">隐私</a> ·
  <a href="CONTRIBUTING.md">参与贡献</a> ·
  <a href="README.md">English</a>
</p>

---

其他 token 统计工具都是**里程表** —— 只告诉你花了多少。
这个是**教练**：15 条确定性规则把你自己的会话记录变成分级结论，每条都带证据、
可执行的建议、置信度，以及在可论证的情况下，每月能省下多少。

采集**零 token 成本**。它只读取你的编程 agent 已经写到磁盘上的 JSONL 记录。
不需要 API key，不需要代理，不需要账号，不需要联网。

## 快速开始

```bash
git clone https://github.com/jxxyx-bloop/ai-observatory
cd ai-observatory/observatory

# 用 60 天合成数据立刻看到完整效果
python3 observe.py demo digest report

# 或者跑你自己的真实用量
python3 observe.py all
```

然后打开 `dist/observatory.html`。**仅依赖 Python 3 标准库 —— 无依赖、免安装、无构建步骤。**

> `demo` 存在是因为这类工具都有同一个问题：仪表盘本身就是卖点，但你得先攒够几周
> 数据才能看到。合成数据是确定性的，所以每个人看到的数字一样，可以直接在 issue 里讨论。

## 命令

| 命令 | 作用 |
|---|---|
| `observe.py sync` | 增量采集新事件到 `data/`（约 0.2 秒） |
| `observe.py digest` | 聚合 + 运行检测规则 → `data/digest.json` |
| `observe.py report` | 渲染 → `dist/observatory.html` |
| `observe.py insights` | 以文本打印结论 —— 方便在 agent 会话里直接读 |
| `observe.py demo` | 60 天确定性合成用量 |
| `observe.py share` | 生成社区上报内容并**打印出来** —— 永远不上传 |
| `observe.py all` | sync → digest → report |

命令可以串联：`observe.py sync digest report` 只启动一个进程。

## 有什么不一样

### 1. 它告诉你该改什么，而不只是花了多少

```
[HIGH] 你在按峰值价买 token，而这本来可以避免                              ~$34/月
  你在分时计价厂商（deepseek、zhipu）上 61.4% 的花费落在峰值时段，
  同样的 token 在此期间最高要付两倍价格。
  -> 峰值时段是公开且很窄的。任何不需要你盯着的工作 —— 生成测试、
     数据迁移、批量改文档 —— 都可以排到非峰值时段，对你没有任何代价。
```

有**重要性门槛**：每月价值低于 15 美元的结论会被降级，所以列表顶部永远是真正值得看的。
**用得好就说用得好** —— 一个为了显得有用而编造问题的工具，你很快就不会再信它。

### 2. 它按你的厂商真实的方式计价

- **峰值/非峰值时段。** DeepSeek 在 UTC 01:00–04:00 与 06:00–10:00 按全价计费，
  其余时段半价。智谱 GLM 仅在工作日 UTC+8 14:00–18:00 为峰值。对 UTC+7 至 +9 的
  开发者来说，第二个窗口正好是**工作日下午** —— 你每天都在无意中按峰值付费。
  我们按每一轮实际发生时生效的价格计价，省下的钱是对你自己 token 的算术，不是估算。
  **目前没有任何开源工具处理这件事。**
- **各厂商缓存计价不同。** 0.1× 的缓存命中折扣是 Anthropic 的惯例，不是通用规则 ——
  Kimi K2.6 大约是 0.074×。缓存是省钱的大头，乘数错了，页面上最重要的数字就错了。
- **套餐价值，而不是虚构的美元数。** 在 18 美元/月的 GLM 套餐上，「你花了 412 美元」
  是影子价格，不是账单。真正有意义的数字是 **23 倍回报** —— 反过来也一样：
  *「你在为用不到的额度付钱。」*
- **13 种货币**，包含 IDR、VND、THB、PHP、MYR，并把金额换算成「相当于本地日薪的几天」——
  因为 `$412` 在雅加达和在旧金山完全不是一回事。

### 3. 加一个工具是写一个 JSON 文件，不是等维护者写代码

覆盖面决定了工具对陌生人有没有用，而它通常卡在维护者身上 —— 他要去逆向自己根本
不用的格式。在这里，一个 provider 就是一个
[声明式 spec](observatory/collectors/specs/README.md) 加一个 fixture。
如果你用通义灵码、Qwen Code、CodeBuddy 或文心快码，**只有你能把它加对** —— 而这只需要一个文件。

### 4. 社区榜单比的是效率，不是消耗量

现有榜单按 token 总量排名。榜首按定义就是浪费最多的人 —— 在 200 美元/月的席位很常见的
地方这是个乐子，在中位套餐 18 美元的地方这是种冒犯。

我们排的是**缓存复用率、每次改动消耗的 token、每活跃小时成本、峰值时段自律度、
套餐回报倍数**。总花费会显示，但永远不参与排名。效率是可以提升的，所以榜单有回访的
理由；岘港的学生和新加坡的资深工程师在同一个维度上竞争。

*选择性加入，默认关闭，尚未上线 ——
见[协议说明](docs/specs/Community-Share-Protocol.md)。*

## 隐私

**除非你亲手改配置文件，否则没有任何数据离开你的机器。**

任何情况下都不会存储：提示词 · 模型回复 · 思考内容 · 文件内容 · 工具参数值 ·
shell 命令 · 绝对路径。

会存储的：计数、模型名、工具名，以及粗粒度的派生标签 —— 仓库名和像 `app:checkout`
这样的目录分类。这些约束在解析边界上强制执行，而不是事后脱敏
（[ADR-006](docs/adr/ADR-006-Metadata-Only.md)、
[ADR-008](docs/adr/ADR-008-Derived-Path-Labels.md)）。

渲染出的仪表盘**不发起任何外部请求** —— 没有 CDN，没有字体，没有统计。

即使你将来加入社区层，上报内容也不到 1 KB，里面只有分桶索引而不是原始数值，
不含仓库名、会话 ID 或任何标识符。`observe.py share` 会把全部内容打印出来，
而且这条代码路径根本不联网。可以直接读
[`share.py`](observatory/share.py) —— 它被刻意写得足够短，让你在同意之前能读完。

## 配置

| 文件 | 用途 |
|---|---|
| [`settings.json`](observatory/settings.json) | 时区、货币、你的套餐、社区选项 |
| [`topology.json`](observatory/topology.json) | 仓库位置、目录分类、工作/个人分流 |
| [`pricing.json`](observatory/pricing.json) | 价目表 —— 50 个模型、峰值时段表 |
| [`plans.json`](observatory/plans.json) | 订阅套餐、额度单位、货币 |

改完 `topology.json` 需要执行 `observe.py sync --full` 才会生效。

## 测试

```bash
observatory/tests/run.sh
```

引擎、collector spec、各 provider 的 fixture，以及仪表盘的无头运行测试。
没有测试框架 —— 只有标准库 Python 和一个可选的 node 脚本。

## 文档

| 路径 | 内容 |
|---|---|
| [`docs/strategy/`](docs/strategy/) | **竞品拆解 · 定位 · 东南亚/中国产品论证 · 增长飞轮 · 风险** |
| [`docs/00-*.md`](docs/) | 愿景、工程原则、架构、决策日志 |
| [`docs/adr/`](docs/adr/) | 15 份决策记录，包含被否决的方案及原因 |
| [`docs/specs/`](docs/specs/) | 事件 schema · 成本估算 · 峰值计价 · 套餐与额度 · 社区协议 · 认证 |
| [`docs/context/`](docs/context/) | 术语表 · **已知局限** |

**在相信任何关于「价值」的结论之前，请先读
[Known-Limitations](docs/context/Known-Limitations.md)。**
这个工具能精确测量精力花在了哪里，但只能间接推断它产出了什么。

## 参与贡献

按投入从小到大，三种最有用的贡献：

1. **修正过期价格**（`pricing.json`）—— 改一行，附上出处链接。
2. **补充一个套餐**（`plans.json`）。
3. **加入你用的编程工具** —— 写一个
   [collector spec](observatory/collectors/specs/README.md) 和一个 fixture。

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。特别希望有人补充：Qwen Code、iFlow CLI、
CodeBuddy、Trae、通义灵码、文心快码 Comate、豆包、CodeGeeX、Cline、Roo Code、
Aider、OpenCode、Goose、Zed。

## 状态

早期阶段。引擎、仪表盘、检测规则和隐私边界都已可用并有测试覆盖。
社区层已完成设计但尚未实现。见 [ROADMAP.md](docs/ROADMAP.md)。

## 许可证

[MIT](LICENSE)。
