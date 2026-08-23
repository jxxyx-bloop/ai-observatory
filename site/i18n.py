"""Landing-page copy, in every language the site ships.

One dict per locale, flat keys, no framework. `site/build.py` renders one
static page per locale — English at the root, everything else under its own
directory — which keeps each language crawlable and lets the switcher be a
plain link rather than a script.

Three rules, from docs/design/DESIGN-SYSTEM.md §8:

  * Translate for meaning, not word-for-word. A locale may be shorter than the
    English. Nothing is padded to fill a layout.
  * `en` is the reference. Any key missing from a locale falls back to it, so
    a half-finished translation degrades to English instead of to a blank.
  * No trailing full stop on a heading (`hero_h1_*`, any `*_h2`, any `*_t`
    card title) in any locale — a stop inside for rhythm is fine, the last
    one is not. Body copy keeps normal punctuation; this is for headings.

The language set is deliberate: every Southeast Asian market with a distinct
language, plus the largest AI-developer markets outside the US. Singapore and
much of the Philippines read the English page; both still get their own entry
because the choice belongs to the reader.
"""

from __future__ import annotations

# (code, url directory, name in its own language, switcher badge, <html lang>)
# English lives at the root — "/" rather than "/en/" — because it is both the
# default and the canonical URL people will link to.
LOCALES = [
    ("en",      "",        "English",          "EN",  "en"),
    ("zh-Hans", "zh-hans", "简体中文",           "简",  "zh-Hans"),
    ("zh-Hant", "zh-hant", "繁體中文",           "繁",  "zh-Hant"),
    ("ja",      "ja",      "日本語",             "JA",  "ja"),
    ("ko",      "ko",      "한국어",             "KO",  "ko"),
    ("hi",      "hi",      "हिन्दी",              "HI",  "hi"),
    ("id",      "id",      "Bahasa Indonesia", "ID",  "id"),
    ("vi",      "vi",      "Tiếng Việt",       "VI",  "vi"),
    ("th",      "th",      "ไทย",               "TH",  "th"),
    ("ms",      "ms",      "Bahasa Melayu",    "MS",  "ms"),
    ("fil",     "fil",     "Filipino",         "FIL", "fil"),
    ("pt-BR",   "pt-br",   "Português (BR)",   "PT",  "pt-BR"),
    ("es",      "es",      "Español",          "ES",  "es"),
]

# English name of each locale, shown greyed beside the native name so someone
# who lands on the wrong page can still find their way back.
ENGLISH_NAME = {
    "en": "English", "zh-Hans": "Chinese, simplified", "zh-Hant": "Chinese, traditional",
    "ja": "Japanese", "ko": "Korean", "hi": "Hindi", "id": "Indonesian",
    "vi": "Vietnamese", "th": "Thai", "ms": "Malay", "fil": "Filipino",
    "pt-BR": "Portuguese", "es": "Spanish",
}

STRINGS: dict[str, dict[str, str]] = {}

STRINGS["en"] = {
    # README-only; rendered by site/tools/readmes.py.
    "rm_quick": "Quick start",
    "rm_own": "Then on your own usage:",
    "rm_docs_en": "Full documentation — configuration, commands, contributing — is in English:",
    "rm_translate": "Something read wrong? Every string on this page lives in one dict per language in `site/i18n.py`. One file, no framework.",
    "rm_generated": "Generated from the website's own copy, so this page and the site can never disagree.",
    "brand": "AI Observatory",
    "meta_title": "AI Observatory — know what to change",
    "meta_desc": "Reads the logs your coding agent already writes and turns them "
                 "into a short, ranked list of changes worth making. Free, local, "
                 "no account, nothing leaves your machine.",

    "nav_label": "Navigation",
    "nav_output": "Findings",
    "nav_how": "How",
    "nav_why": "Different",
    "nav_privacy": "Privacy",
    "nav_demo": "Demo",
    "nav_setup": "Set up",
    "lang_label": "Language",
    "theme_label": "Light / dark",

    "hero_eyebrow": "Open source · Runs on your machine",
    "hero_h1_a": "Know what to",
    "hero_h1_b": "change",
    "hero_h1_c": "",
    "hero_lede": "Your coding agent already logs every turn. This reads those logs "
                 "and tells you the few changes worth making — each with a number "
                 "attached.",
    "chip1": "Set up in under a minute",
    "chip2": "No account",
    "chip3": "Nothing leaves your machine",
    "cta_demo": "Open the live demo",
    "cta_github": "View source",
    "run_comment": "60 days of sample data, then the real dashboard",
    "run_note": "Python 3 standard library. No install, no dependencies, no build step.",

    "find_eyebrow": "The output",
    "find_h2": "Not a number. A next move",
    "find_note": "Fifteen checks. Anything worth under $15 a month is demoted, so "
                 "the top of the list always means something — and healthy usage is "
                 "reported as healthy.",
    "prev_label": "Previous",
    "next_label": "Next",
    "sev_high": "High",
    "sev_med": "Medium",
    "sev_low": "Low",

    "f1_title": "You're paying peak rates you didn't have to",
    "f1_save": "≈ $34/mo",
    "f1_body": "61% of your spend on time-priced models landed inside a peak window, "
               "where the same tokens cost up to twice as much.",
    "f1_act": "Queue the work that doesn't need watching — tests, migrations, doc "
              "sweeps — for an off-peak hour.",

    "f2_title": "Context is being rebuilt, not reused",
    "f2_save": "≈ $61/mo",
    "f2_body": "Cache reuse sits at 38%. Rebuilding context costs roughly 12× what "
               "reading it back does.",
    "f2_act": "Keep one session across related tasks instead of restarting. This gap "
              "is worth more than any model swap.",

    "f3_title": "Your $18 plan returned 23× what you paid",
    "f3_save": "23× return",
    "f3_body": "Metered, the same work would have cost $412. Nothing here needs fixing.",
    "f3_act": "Stay on the plan. Revisit if your monthly turns drop below 400.",

    "how_eyebrow": "How it works",
    "how_h2": "Three steps, about a second",
    "how_1_t": "Read",
    "how_1_d": "Your agent already wrote the logs. We read those files where they are — nothing to install, nothing to switch on.",
    "how_2_t": "Measure",
    "how_2_d": "Tokens, cache, timing and cost — priced at the rate that was "
               "actually in force when the work ran.",
    "how_3_t": "Act",
    "how_3_d": "A ranked list of changes, each with its evidence and what it is "
               "worth per month.",
    "how_note": "No API key, no proxy, no account, no network. Collection costs zero tokens.",

    "why_eyebrow": "Why it's different",
    "why_h2": "Priced the way you actually pay",
    "why_1_t": "The clock changes the price",
    "why_1_d": "DeepSeek and GLM charge by the hour. From UTC+7 to +9, their peak "
               "window is your working afternoon.",
    "why_2_t": "A plan is not a bill",
    "why_2_d": "On an $18 plan, “you spent $412” is fiction. “23× return” isn't.",
    "why_3_t": "Cache rates differ by vendor",
    "why_3_d": "The 0.1× discount is an Anthropic habit, not a law. Get it wrong and "
               "you misprice the biggest number on the page.",
    "why_4_t": "Thirteen currencies",
    "why_4_d": "IDR, VND, THB, PHP, MYR and more — set against a local day rate, "
               "because $412 does not mean one thing everywhere.",

    "priv_eyebrow": "Privacy",
    "priv_h2": "A mechanism, not a promise",
    "priv_lede": "Nothing leaves your machine unless you edit a file to say so.",
    "priv_1": "Never stored: prompts, replies, code, commands, file paths.",
    "priv_2": "Blocked where the file is parsed — so a leak would be a bug, not a "
              "policy question.",
    "priv_3": "The dashboard and this page make zero external requests. No CDN, no "
              "fonts, no analytics.",

    "start_h2": "One command, about a minute",
    "start_d": "One line. It checks your setup, reads what your coding agents "
               "already wrote on this disk, builds your dashboard, puts an icon "
               "in your Dock and opens it.",
    "start_cta1": "Open the live demo",

    # ── Setup walkthrough ───────────────────────────────────────────────────
    # Three commands, in the order a person actually runs them: see it, then
    # make it yours, then keep it. Step 1 deliberately uses sample data — the
    # product has to be visible before anyone earns the right to ask for a
    # real sync.
    "setup_copy": "Copy",
    "setup_more": "What that command does, step by step \u2192",
    "setup_copied": "Copied",

    # ── Troubleshooting ─────────────────────────────────────────────────────
    # The five things that actually go wrong. `observe.py doctor` prints the
    # same list locally, so a person who is offline is not worse off.
    "tr_h": "Something did not work",
    "tr_1_q": "\u201cpython3: command not found\u201d",
    "tr_1_a": "macOS and Linux ship Python 3 already, so this is almost always "
              "Windows. Install it from python.org and tick \u201cAdd Python to "
              "PATH\u201d during setup, then use python instead of python3.",
    "tr_2_q": "\u201csync: 0 new events from 0 sources\u201d",
    "tr_2_a": "No supported tool has run on this machine yet, or its transcripts "
              "live somewhere non-standard. This is expected on a fresh laptop \u2014 "
              "the sample data in step 1 still shows the whole product.",
    "tr_3_q": "The page says there is no digest yet",
    "tr_3_a": "Collection and rendering are separate steps. Run "
              "python3 observe.py digest report, or just python3 observe.py all, "
              "which does every step in order.",
    "tr_4_q": "Nothing opened in my browser",
    "tr_4_a": "The file is still there \u2014 open dist/observatory.html from the "
              "project folder. Scheduled runs never open a browser on purpose, "
              "so a morning refresh cannot steal focus while you work.",
    "tr_5_q": "macOS says the app is from an unidentified developer",
    "tr_5_a": "That warning belongs to downloaded apps. The launcher is generated "
              "on your own machine, so it should never appear \u2014 if it does, the "
              "app was copied from another computer. Delete it and run "
              "python3 observe.py install again to build a local one.",
    "tr_note": "Still stuck? Run python3 observe.py doctor \u2014 it checks every "
               "step and prints the exact fix for whichever one failed.",

    "foot_tag": "MIT licensed · Local-first · No account",
    "foot_docs": "Docs",
    "foot_limits": "Known limits",
    "foot_contrib": "Contribute",
}

STRINGS["zh-Hans"] = {
    # README-only; rendered by site/tools/readmes.py.
    "rm_quick": "快速开始",
    "rm_own": "然后在你自己的用量上运行：",
    "rm_docs_en": "完整文档（配置、命令、贡献指南）为英文：",
    "rm_translate": "哪里读着别扭？本页每一句都放在 `site/i18n.py` 里，每种语言一个字典。一个文件，没有框架。",
    "rm_generated": "本页由网站同一份文案生成，因此不会与网站说法不一致。",
    "brand": "AI Observatory",
    "meta_title": "AI Observatory — 知道该改什么",
    "meta_desc": "读取编程 Agent 已经写好的本地日志，输出一份排好序的、值得动手的改进清单。免费、本地运行、无需账号，数据不出本机。",

    "nav_label": "导航",
    "nav_output": "结论",
    "nav_how": "原理",
    "nav_why": "差异",
    "nav_privacy": "隐私",
    "nav_demo": "演示",
    "lang_label": "语言",
    "theme_label": "浅色 / 深色",

    "hero_eyebrow": "开源 · 在你自己的机器上运行",
    "hero_h1_a": "知道该",
    "hero_h1_b": "改什么",
    "hero_h1_c": "",
    "hero_lede": "编程 Agent 已经把每一轮对话写进了日志。本工具读取这些日志，告诉你少数几件值得改的事——每一件都带一个数字。",
    "chip1": "一分钟内就能跑起来",
    "chip2": "无需账号",
    "chip3": "数据不出本机",
    "cta_demo": "打开在线演示",
    "cta_github": "查看源码",
    "run_comment": "60 天示例数据，直接生成完整看板",
    "run_note": "仅用 Python 3 标准库。无需安装、无依赖、无构建步骤。",

    "find_eyebrow": "输出结果",
    "find_h2": "不是一个数字，是下一步该做什么",
    "find_note": "十五项检测。每月价值低于 15 美元的会被降级，所以排在最前面的一定值得看——用得健康时，它也会照实说健康。",
    "prev_label": "上一条",
    "next_label": "下一条",
    "sev_high": "高",
    "sev_med": "中",
    "sev_low": "低",

    "f1_title": "你在按高峰价买 token，本可以不用",
    "f1_save": "≈ 34 美元/月",
    "f1_body": "按时段计价的模型上，61% 的花费落在高峰时段，同样的 token 最多要贵一倍。",
    "f1_act": "不需要盯着的任务——测试生成、迁移、文档整理——排到非高峰时段跑。",

    "f2_title": "上下文在被重建，而不是复用",
    "f2_save": "≈ 61 美元/月",
    "f2_body": "缓存复用率只有 38%。重建上下文的成本约为读回它的 12 倍。",
    "f2_act": "相关任务放在同一个会话里做，不要反复重开。这个差距比换任何模型都值钱。",

    "f3_title": "18 美元的套餐给你带来了 23 倍回报",
    "f3_save": "23 倍回报",
    "f3_body": "如果按量计费，同样的工作要花 412 美元。这里没有需要改的地方。",
    "f3_act": "继续用这个套餐。等每月轮次跌破 400 再重新评估。",

    "how_eyebrow": "工作方式",
    "how_h2": "三步，约一秒钟",
    "how_1_t": "读取",
    "how_1_d": "Agent 已经把日志写好了。我们就地读取这些文件——无需安装，也不用开启任何东西。",
    "how_2_t": "计量",
    "how_2_d": "token、缓存、时段与成本——按任务实际运行时生效的价格计算。",
    "how_3_t": "行动",
    "how_3_d": "一份排好序的改进清单，每条都附证据，以及每月值多少钱。",
    "how_note": "无需 API key、无代理、无账号、不联网。采集本身消耗零 token。",

    "why_eyebrow": "有何不同",
    "why_h2": "按你真实付费的方式计价",
    "why_1_t": "时钟会改变价格",
    "why_1_d": "DeepSeek 与 GLM 按时段计价。在 UTC+7 到 +9，它们的高峰时段正好是你的工作下午。",
    "why_2_t": "套餐不等于账单",
    "why_2_d": "在 18 美元的套餐上，“你花了 412 美元”是虚构的，“23 倍回报”不是。",
    "why_3_t": "缓存折扣因厂商而异",
    "why_3_d": "0.1× 是 Anthropic 的惯例，不是定律。算错它，页面上最重要的那个数字就错了。",
    "why_4_t": "十三种货币",
    "why_4_d": "IDR、VND、THB、PHP、MYR 等——并对照当地日薪，因为 412 美元在各地的分量并不一样。",

    "priv_eyebrow": "隐私",
    "priv_h2": "这是机制，不是承诺",
    "priv_lede": "除非你亲手改配置文件，否则没有任何数据离开本机。",
    "priv_1": "从不存储：提示词、回复、代码、命令、文件路径。",
    "priv_2": "在解析文件的那一层就挡掉——所以泄漏是 bug，而不是政策问题。",
    "priv_3": "看板和本页都不发起任何外部请求。无 CDN、无字体、无统计。",

    "start_cta1": "打开在线演示",

    "foot_tag": "MIT 许可 · 本地优先 · 无需账号",
    "foot_docs": "文档",
    "foot_limits": "已知限制",
    "foot_contrib": "参与贡献",
}

STRINGS["zh-Hant"] = {
    # README-only; rendered by site/tools/readmes.py.
    "rm_quick": "快速開始",
    "rm_own": "接著在你自己的用量上執行：",
    "rm_docs_en": "完整文件（設定、指令、貢獻指南）為英文：",
    "rm_translate": "哪裡讀起來怪怪的？本頁每一句都放在 `site/i18n.py`，每種語言一個字典。一個檔案，沒有框架。",
    "rm_generated": "本頁由網站同一份文案產生，因此不會與網站說法不一致。",
    "brand": "AI Observatory",
    "meta_title": "AI Observatory — 知道該改什麼",
    "meta_desc": "讀取編碼 Agent 已經寫好的本機日誌，產生一份排序過、值得動手的改進清單。免費、本機執行、免帳號，資料不離開你的電腦。",

    "nav_label": "導覽",
    "nav_output": "結論",
    "nav_how": "原理",
    "nav_why": "差異",
    "nav_privacy": "隱私",
    "nav_demo": "示範",
    "lang_label": "語言",
    "theme_label": "淺色 / 深色",

    "hero_eyebrow": "開源 · 在你自己的電腦上執行",
    "hero_h1_a": "知道該",
    "hero_h1_b": "改什麼",
    "hero_h1_c": "",
    "hero_lede": "編碼 Agent 已經把每一輪對話寫進日誌。本工具讀取這些日誌，告訴你少數幾件值得改的事——每一件都附上一個數字。",
    "chip1": "一分鐘內就能跑起來",
    "chip2": "免帳號",
    "chip3": "資料不離開本機",
    "cta_demo": "開啟線上示範",
    "cta_github": "檢視原始碼",
    "run_comment": "60 天範例資料，直接產生完整儀表板",
    "run_note": "只用 Python 3 標準函式庫。免安裝、無相依套件、無建置步驟。",

    "find_eyebrow": "輸出結果",
    "find_h2": "不是一個數字，是下一步該做什麼",
    "find_note": "十五項檢測。每月價值低於 15 美元的會被降級，所以排在最前面的一定值得看——用得健康時，它也會照實說健康。",
    "prev_label": "上一則",
    "next_label": "下一則",
    "sev_high": "高",
    "sev_med": "中",
    "sev_low": "低",

    "f1_title": "你在用尖峰價買 token，其實不必",
    "f1_save": "≈ 34 美元/月",
    "f1_body": "在按時段計價的模型上，61% 的花費落在尖峰時段，同樣的 token 最多貴一倍。",
    "f1_act": "不需要盯著的工作——測試產生、遷移、文件整理——排到離峰時段執行。",

    "f2_title": "脈絡在被重建，而不是重用",
    "f2_save": "≈ 61 美元/月",
    "f2_body": "快取重用率只有 38%。重建脈絡的成本約為讀回它的 12 倍。",
    "f2_act": "相關工作留在同一個 session，不要反覆重開。這個差距比換任何模型都值錢。",

    "f3_title": "18 美元的方案帶來了 23 倍回報",
    "f3_save": "23 倍回報",
    "f3_body": "若按量計費，同樣的工作要花 412 美元。這裡沒有需要改的地方。",
    "f3_act": "繼續用這個方案。等每月輪次低於 400 再重新評估。",

    "how_eyebrow": "運作方式",
    "how_h2": "三個步驟，約一秒",
    "how_1_t": "讀取",
    "how_1_d": "Agent 已經把日誌寫好了。我們就地讀取這些檔案——免安裝，也不必啟用任何東西。",
    "how_2_t": "計量",
    "how_2_d": "token、快取、時段與成本——依工作實際執行當下生效的價格計算。",
    "how_3_t": "行動",
    "how_3_d": "一份排序過的改進清單，每條都附證據，以及每月值多少錢。",
    "how_note": "免 API key、免 proxy、免帳號、不連網。蒐集本身消耗零 token。",

    "why_eyebrow": "有何不同",
    "why_h2": "依你真實付費的方式計價",
    "why_1_t": "時鐘會改變價格",
    "why_1_d": "DeepSeek 與 GLM 按時段計價。在 UTC+7 到 +9，它們的尖峰時段正好是你的工作下午。",
    "why_2_t": "方案不等於帳單",
    "why_2_d": "在 18 美元的方案上，「你花了 412 美元」是虛構的，「23 倍回報」不是。",
    "why_3_t": "快取折扣因廠商而異",
    "why_3_d": "0.1× 是 Anthropic 的慣例，不是定律。算錯它，頁面上最重要的數字就錯了。",
    "why_4_t": "十三種貨幣",
    "why_4_d": "IDR、VND、THB、PHP、MYR 等——並對照當地日薪，因為 412 美元在各地的份量並不相同。",

    "priv_eyebrow": "隱私",
    "priv_h2": "這是機制，不是承諾",
    "priv_lede": "除非你親手改設定檔，否則沒有任何資料離開本機。",
    "priv_1": "從不儲存：提示詞、回覆、程式碼、指令、檔案路徑。",
    "priv_2": "在解析檔案那一層就擋掉——所以外洩是 bug，不是政策問題。",
    "priv_3": "儀表板與本頁都不發出任何外部請求。無 CDN、無字型、無分析。",

    "start_cta1": "開啟線上示範",

    "foot_tag": "MIT 授權 · 本機優先 · 免帳號",
    "foot_docs": "文件",
    "foot_limits": "已知限制",
    "foot_contrib": "參與貢獻",
}

STRINGS["ja"] = {
    # README-only; rendered by site/tools/readmes.py.
    "rm_quick": "クイックスタート",
    "rm_own": "次に、自分の使用状況に対して実行します。",
    "rm_docs_en": "設定・コマンド・コントリビュートを含む完全なドキュメントは英語です。",
    "rm_translate": "読みづらい箇所があれば。このページの文言はすべて `site/i18n.py` の言語ごとの辞書にあります。ファイル1つ、フレームワークなし。",
    "rm_generated": "サイトと同じ文言から生成しているので、このページとサイトが食い違うことはありません。",
    "brand": "AI Observatory",
    "meta_title": "AI Observatory — 何を変えるべきかがわかる",
    "meta_desc": "コーディングエージェントがすでに残しているログを読み、手を打つ価値のある変更を優先順位つきで短くまとめます。無料、ローカル動作、アカウント不要。データは端末から出ません。",

    "nav_label": "ナビゲーション",
    "nav_output": "結果",
    "nav_how": "仕組み",
    "nav_why": "違い",
    "nav_privacy": "プライバシー",
    "nav_demo": "デモ",
    "lang_label": "言語",
    "theme_label": "ライト / ダーク",

    "hero_eyebrow": "オープンソース · 自分の端末で動く",
    "hero_h1_a": "何を",
    "hero_h1_b": "変えるべきか",
    "hero_h1_c": "",
    "hero_lede": "エージェントは毎ターンをすでに記録しています。そのログを読み、手を打つ価値のある数点だけを、数字つきで示します。",
    "chip1": "設定は1分もかからない",
    "chip2": "アカウント不要",
    "chip3": "データは端末の外に出ない",
    "cta_demo": "デモを開く",
    "cta_github": "ソースを見る",
    "run_comment": "60日分のサンプルから、そのままダッシュボードまで",
    "run_note": "Python 3 標準ライブラリのみ。インストール・依存・ビルド、いずれも不要。",

    "find_eyebrow": "出力",
    "find_h2": "数字ではなく、次の一手を",
    "find_note": "15種類の検査。月15ドル未満の項目は格下げされるので、上位は常に意味があります。健全な使い方は、健全と報告します。",
    "prev_label": "前へ",
    "next_label": "次へ",
    "sev_high": "高",
    "sev_med": "中",
    "sev_low": "低",

    "f1_title": "払わなくてよいピーク料金を払っています",
    "f1_save": "≈ 月34ドル",
    "f1_body": "時間帯課金モデルでの支出の61%がピーク時間帯に入っており、同じトークンが最大2倍の値段になっています。",
    "f1_act": "見ている必要のない作業（テスト生成・移行・ドキュメント整理）はオフピーク帯に回してください。",

    "f2_title": "コンテキストを再利用せず、作り直しています",
    "f2_save": "≈ 月61ドル",
    "f2_body": "キャッシュ再利用率は38%。コンテキストの再構築は、読み戻すおよそ12倍のコストがかかります。",
    "f2_act": "関連する作業は同じセッションで続けてください。この差はモデルの入れ替えより効きます。",

    "f3_title": "月18ドルのプランが23倍を返しています",
    "f3_save": "23倍",
    "f3_body": "従量課金なら同じ作業に412ドルかかっていました。ここに直すところはありません。",
    "f3_act": "このまま継続を。月間ターンが400を下回ったら再検討してください。",

    "how_eyebrow": "仕組み",
    "how_h2": "3ステップ、約1秒",
    "how_1_t": "読む",
    "how_1_d": "エージェントがすでにログを書いています。その場のファイルをそのまま読むだけ——インストールも、有効化も不要です。",
    "how_2_t": "測る",
    "how_2_d": "トークン、キャッシュ、時間帯、コスト。実行された時点で有効だった料金で計算します。",
    "how_3_t": "動く",
    "how_3_d": "優先順位つきの変更リスト。根拠と、月あたりの価値が必ず添えられます。",
    "how_note": "APIキー・プロキシ・アカウント・通信、いずれも不要。収集自体のトークン消費はゼロです。",

    "why_eyebrow": "違い",
    "why_h2": "実際の支払い方に合わせて計算する",
    "why_1_t": "時刻で価格が変わる",
    "why_1_d": "DeepSeekとGLMは時間帯課金です。UTC+7〜+9では、そのピーク帯がちょうど仕事の午後にあたります。",
    "why_2_t": "プランは請求書ではない",
    "why_2_d": "月18ドルのプランで「412ドル使った」は作り話です。「23倍」は違います。",
    "why_3_t": "キャッシュ料率はベンダーごとに違う",
    "why_3_d": "0.1倍はAnthropicの慣習であって法則ではありません。ここを外すと、最重要の数字が狂います。",
    "why_4_t": "13の通貨",
    "why_4_d": "IDR・VND・THB・PHP・MYRほか。現地の日当と並べて示します。412ドルの重みは、どこでも同じではありません。",

    "priv_eyebrow": "プライバシー",
    "priv_h2": "約束ではなく、仕組みで",
    "priv_lede": "設定ファイルを自分で書き換えない限り、データは端末の外に出ません。",
    "priv_1": "決して保存しないもの：プロンプト、応答、コード、コマンド、ファイルパス。",
    "priv_2": "解析の入口で遮断しています。だから漏えいは方針の問題ではなく、バグです。",
    "priv_3": "ダッシュボードもこのページも外部リクエストはゼロ。CDNもフォントも解析タグもありません。",

    "start_cta1": "デモを開く",

    "foot_tag": "MITライセンス · ローカルファースト · アカウント不要",
    "foot_docs": "ドキュメント",
    "foot_limits": "既知の制限",
    "foot_contrib": "コントリビュート",
}

STRINGS["ko"] = {
    # README-only; rendered by site/tools/readmes.py.
    "rm_quick": "빠른 시작",
    "rm_own": "그다음, 본인의 사용 기록으로 실행합니다:",
    "rm_docs_en": "설정, 명령, 기여 방법을 포함한 전체 문서는 영어로 되어 있습니다:",
    "rm_translate": "어색하게 읽히는 곳이 있나요? 이 페이지의 모든 문구는 `site/i18n.py`에 언어별 딕셔너리로 있습니다. 파일 하나, 프레임워크 없음.",
    "rm_generated": "사이트와 같은 문구에서 생성되므로 이 페이지와 사이트가 어긋날 수 없습니다.",
    "brand": "AI Observatory",
    "meta_title": "AI Observatory — 무엇을 바꿔야 하는지 알려줍니다",
    "meta_desc": "코딩 에이전트가 이미 남긴 로그를 읽어, 손볼 가치가 있는 변경 사항만 우선순위대로 짧게 정리합니다. 무료, 로컬 실행, 계정 불필요. 데이터는 기기를 벗어나지 않습니다.",

    "nav_label": "내비게이션",
    "nav_output": "결과",
    "nav_how": "원리",
    "nav_why": "차이",
    "nav_privacy": "프라이버시",
    "nav_demo": "데모",
    "lang_label": "언어",
    "theme_label": "라이트 / 다크",

    "hero_eyebrow": "오픈소스 · 내 기기에서 실행",
    "hero_h1_a": "무엇을",
    "hero_h1_b": "바꿔야 할지",
    "hero_h1_c": "",
    "hero_lede": "에이전트는 이미 모든 턴을 기록하고 있습니다. 그 로그를 읽어, 손볼 가치가 있는 몇 가지만 숫자와 함께 알려줍니다.",
    "chip1": "설정에 1분도 안 걸립니다",
    "chip2": "계정 불필요",
    "chip3": "데이터는 기기 밖으로 나가지 않음",
    "cta_demo": "라이브 데모 열기",
    "cta_github": "소스 보기",
    "run_comment": "60일치 샘플 데이터로 실제 대시보드까지",
    "run_note": "Python 3 표준 라이브러리만 사용. 설치도, 의존성도, 빌드도 없습니다.",

    "find_eyebrow": "결과물",
    "find_h2": "숫자가 아니라, 다음 행동",
    "find_note": "열다섯 가지 검사. 월 15달러 미만은 순위에서 내려가므로 맨 위는 언제나 의미가 있습니다. 건강한 사용은 건강하다고 그대로 보고합니다.",
    "prev_label": "이전",
    "next_label": "다음",
    "sev_high": "높음",
    "sev_med": "보통",
    "sev_low": "낮음",

    "f1_title": "내지 않아도 될 피크 요금을 내고 있습니다",
    "f1_save": "≈ 월 34달러",
    "f1_body": "시간대 과금 모델 지출의 61%가 피크 구간에 들어갔고, 같은 토큰이 최대 두 배까지 비쌉니다.",
    "f1_act": "지켜볼 필요 없는 작업(테스트 생성, 마이그레이션, 문서 정리)은 비피크 시간대로 미루세요.",

    "f2_title": "컨텍스트를 재사용하지 않고 다시 만들고 있습니다",
    "f2_save": "≈ 월 61달러",
    "f2_body": "캐시 재사용률이 38%입니다. 컨텍스트를 다시 쌓는 비용은 다시 읽는 것의 약 12배입니다.",
    "f2_act": "연관된 작업은 한 세션에서 이어가세요. 이 격차가 모델 교체보다 큽니다.",

    "f3_title": "월 18달러 플랜이 23배를 돌려줬습니다",
    "f3_save": "23배",
    "f3_body": "종량제였다면 같은 작업에 412달러가 들었습니다. 여기서 고칠 것은 없습니다.",
    "f3_act": "플랜을 유지하세요. 월 턴 수가 400 아래로 떨어지면 다시 보면 됩니다.",

    "how_eyebrow": "작동 방식",
    "how_h2": "세 단계, 약 1초",
    "how_1_t": "읽기",
    "how_1_d": "에이전트가 이미 로그를 남겼습니다. 그 파일을 있는 자리에서 읽습니다 — 설치할 것도, 켤 것도 없습니다.",
    "how_2_t": "측정",
    "how_2_d": "토큰, 캐시, 시간대, 비용 — 작업이 실제로 실행된 시점의 요율로 계산합니다.",
    "how_3_t": "실행",
    "how_3_d": "우선순위가 매겨진 변경 목록. 근거와 월 단위 가치가 함께 붙습니다.",
    "how_note": "API 키도, 프록시도, 계정도, 네트워크도 없습니다. 수집 자체는 토큰을 쓰지 않습니다.",

    "why_eyebrow": "무엇이 다른가",
    "why_h2": "실제로 결제하는 방식 그대로 계산합니다",
    "why_1_t": "시각이 가격을 바꾼다",
    "why_1_d": "DeepSeek과 GLM은 시간대별로 과금합니다. UTC+7~+9에서는 그 피크 구간이 바로 업무 오후입니다.",
    "why_2_t": "플랜은 청구서가 아니다",
    "why_2_d": "월 18달러 플랜에서 “412달러를 썼다”는 허구입니다. “23배”는 아닙니다.",
    "why_3_t": "캐시 요율은 업체마다 다르다",
    "why_3_d": "0.1배는 Anthropic의 관행이지 법칙이 아닙니다. 여기서 틀리면 가장 중요한 숫자가 틀립니다.",
    "why_4_t": "13개 통화",
    "why_4_d": "IDR, VND, THB, PHP, MYR 등 — 현지 일당과 나란히 보여줍니다. 412달러의 무게는 어디서나 같지 않으니까요.",

    "priv_eyebrow": "프라이버시",
    "priv_h2": "약속이 아니라 구조로",
    "priv_lede": "설정 파일을 직접 바꾸지 않는 한, 어떤 데이터도 기기를 벗어나지 않습니다.",
    "priv_1": "절대 저장하지 않는 것: 프롬프트, 응답, 코드, 명령어, 파일 경로.",
    "priv_2": "파일을 파싱하는 지점에서 차단합니다. 그래서 유출은 정책 문제가 아니라 버그입니다.",
    "priv_3": "대시보드도 이 페이지도 외부 요청이 0건입니다. CDN도, 폰트도, 애널리틱스도 없습니다.",

    "start_cta1": "라이브 데모 열기",

    "foot_tag": "MIT 라이선스 · 로컬 우선 · 계정 불필요",
    "foot_docs": "문서",
    "foot_limits": "알려진 한계",
    "foot_contrib": "기여하기",
}

STRINGS["hi"] = {
    # README-only; rendered by site/tools/readmes.py.
    "rm_quick": "क्विक स्टार्ट",
    "rm_own": "फिर अपने ख़ुद के इस्तेमाल पर:",
    "rm_docs_en": "पूरा दस्तावेज़ — कॉन्फ़िगरेशन, कमांड, योगदान — अंग्रेज़ी में है:",
    "rm_translate": "कुछ अटपटा लगा? इस पेज की हर पंक्ति `site/i18n.py` में है, हर भाषा का एक डिक्शनरी। एक फ़ाइल, कोई फ़्रेमवर्क नहीं।",
    "rm_generated": "वेबसाइट की उसी कॉपी से बना है, इसलिए यह पेज और साइट कभी अलग बात नहीं कहेंगे।",
    "brand": "AI Observatory",
    "meta_title": "AI Observatory — जानिए क्या बदलना है",
    "meta_desc": "आपका कोडिंग एजेंट जो लॉग पहले से लिख रहा है, उन्हीं को पढ़कर एक छोटी, क्रमबद्ध सूची बनाता है — वे बदलाव जो सचमुच करने लायक हैं। मुफ़्त, लोकल, बिना अकाउंट। डेटा आपकी मशीन से बाहर नहीं जाता।",

    "nav_label": "नेविगेशन",
    "nav_output": "नतीजे",
    "nav_how": "तरीका",
    "nav_why": "अंतर",
    "nav_privacy": "निजता",
    "nav_demo": "डेमो",
    "lang_label": "भाषा",
    "theme_label": "लाइट / डार्क",

    "hero_eyebrow": "ओपन सोर्स · आपकी अपनी मशीन पर चलता है",
    "hero_h1_a": "जानिए क्या",
    "hero_h1_b": "बदलना है",
    "hero_h1_c": "",
    "hero_lede": "आपका एजेंट हर टर्न पहले से लॉग कर रहा है। यह उन्हीं लॉग को पढ़कर बताता है कि कौन से कुछ बदलाव करने लायक हैं — हर एक के साथ एक आँकड़ा।",
    "chip1": "एक मिनट से कम में तैयार",
    "chip2": "अकाउंट नहीं चाहिए",
    "chip3": "कुछ भी मशीन से बाहर नहीं जाता",
    "cta_demo": "लाइव डेमो खोलें",
    "cta_github": "सोर्स देखें",
    "run_comment": "60 दिन का नमूना डेटा, फिर पूरा डैशबोर्ड",
    "run_note": "सिर्फ़ Python 3 स्टैंडर्ड लाइब्रेरी। न इंस्टॉल, न डिपेंडेंसी, न बिल्ड।",

    "find_eyebrow": "आउटपुट",
    "find_h2": "आँकड़ा नहीं। अगला क़दम",
    "find_note": "पंद्रह जाँचें। महीने में $15 से कम मूल्य वाली बात नीचे चली जाती है, इसलिए सूची का शीर्ष हमेशा मायने रखता है — और सेहतमंद इस्तेमाल को सेहतमंद ही बताया जाता है।",
    "prev_label": "पिछला",
    "next_label": "अगला",
    "sev_high": "उच्च",
    "sev_med": "मध्यम",
    "sev_low": "कम",

    "f1_title": "आप पीक दर चुका रहे हैं, जिसकी ज़रूरत नहीं थी",
    "f1_save": "≈ $34/माह",
    "f1_body": "समय-आधारित दर वाले मॉडलों पर आपका 61% ख़र्च पीक विंडो में पड़ा, जहाँ वही टोकन दोगुने तक महँगे हैं।",
    "f1_act": "जिस काम पर नज़र रखने की ज़रूरत नहीं — टेस्ट, माइग्रेशन, डॉक्स — उसे ऑफ़-पीक घंटे में चलाएँ।",

    "f2_title": "कॉन्टेक्स्ट दोबारा बन रहा है, दोबारा इस्तेमाल नहीं हो रहा",
    "f2_save": "≈ $61/माह",
    "f2_body": "कैश पुनः-उपयोग 38% पर है। कॉन्टेक्स्ट दोबारा बनाने की लागत उसे पढ़ने से लगभग 12 गुना है।",
    "f2_act": "जुड़े हुए कामों के लिए एक ही सेशन चलाएँ। यह फ़र्क़ किसी भी मॉडल बदलने से ज़्यादा क़ीमती है।",

    "f3_title": "आपके $18 प्लान ने 23 गुना लौटाया",
    "f3_save": "23× रिटर्न",
    "f3_body": "प्रति-टोकन दर पर यही काम $412 का पड़ता। यहाँ सुधारने को कुछ नहीं है।",
    "f3_act": "प्लान बनाए रखें। महीने के टर्न 400 से नीचे आएँ तो दोबारा देखें।",

    "how_eyebrow": "यह कैसे काम करता है",
    "how_h2": "तीन क़दम, लगभग एक सेकंड",
    "how_1_t": "पढ़ना",
    "how_1_d": "आपका एजेंट लॉग पहले ही लिख चुका है। हम वही फ़ाइलें वहीं पढ़ते हैं — न कुछ इंस्टॉल करना है, न कुछ चालू करना।",
    "how_2_t": "मापना",
    "how_2_d": "टोकन, कैश, समय और लागत — उसी दर पर जो काम चलने के वक़्त लागू थी।",
    "how_3_t": "करना",
    "how_3_d": "बदलावों की क्रमबद्ध सूची, हर एक के साथ सबूत और महीने की क़ीमत।",
    "how_note": "न API की, न प्रॉक्सी, न अकाउंट, न नेटवर्क। डेटा जुटाने में शून्य टोकन लगते हैं।",

    "why_eyebrow": "यह अलग क्यों है",
    "why_h2": "जैसे आप सचमुच भुगतान करते हैं, वैसे ही गिनती",
    "why_1_t": "घड़ी क़ीमत बदल देती है",
    "why_1_d": "DeepSeek और GLM घंटे के हिसाब से चार्ज करते हैं। UTC+5:30 से +9 तक उनकी पीक विंडो आपके काम की दोपहर है।",
    "why_2_t": "प्लान बिल नहीं होता",
    "why_2_d": "$18 के प्लान पर “आपने $412 ख़र्च किए” कल्पना है। “23 गुना रिटर्न” नहीं।",
    "why_3_t": "कैश दर हर वेंडर की अलग",
    "why_3_d": "0.1× Anthropic की आदत है, नियम नहीं। यह ग़लत हुआ तो पेज का सबसे बड़ा आँकड़ा ग़लत हो जाता है।",
    "why_4_t": "तेरह मुद्राएँ",
    "why_4_d": "INR, IDR, VND, THB, PHP, MYR और भी — स्थानीय दिहाड़ी के सामने रखकर, क्योंकि $412 हर जगह एक जैसा नहीं होता।",

    "priv_eyebrow": "निजता",
    "priv_h2": "वादा नहीं, बनावट",
    "priv_lede": "जब तक आप ख़ुद कोई फ़ाइल बदलकर अनुमति न दें, कुछ भी आपकी मशीन से बाहर नहीं जाता।",
    "priv_1": "कभी संग्रहित नहीं: प्रॉम्प्ट, जवाब, कोड, कमांड, फ़ाइल पाथ।",
    "priv_2": "फ़ाइल पढ़ने की जगह पर ही रोका जाता है — इसलिए रिसाव नीति का सवाल नहीं, बग है।",
    "priv_3": "डैशबोर्ड और यह पेज कोई बाहरी अनुरोध नहीं करते। न CDN, न फ़ॉन्ट, न एनालिटिक्स।",

    "start_cta1": "लाइव डेमो खोलें",

    "foot_tag": "MIT लाइसेंस · लोकल-फ़र्स्ट · बिना अकाउंट",
    "foot_docs": "दस्तावेज़",
    "foot_limits": "ज्ञात सीमाएँ",
    "foot_contrib": "योगदान करें",
}

STRINGS["id"] = {
    # README-only; rendered by site/tools/readmes.py.
    "rm_quick": "Mulai cepat",
    "rm_own": "Lalu pada pemakaian Anda sendiri:",
    "rm_docs_en": "Dokumentasi lengkap — konfigurasi, perintah, kontribusi — dalam bahasa Inggris:",
    "rm_translate": "Ada yang terasa janggal? Semua teks di halaman ini ada di `site/i18n.py`, satu dict per bahasa. Satu berkas, tanpa framework.",
    "rm_generated": "Dibuat dari teks yang sama dengan situsnya, jadi halaman ini dan situs tidak mungkin berbeda.",
    "brand": "AI Observatory",
    "meta_title": "AI Observatory — tahu apa yang perlu diubah",
    "meta_desc": "Membaca log yang sudah ditulis coding agent Anda, lalu mengubahnya menjadi daftar pendek berperingkat: perubahan yang benar-benar layak dilakukan. Gratis, lokal, tanpa akun, tidak ada data yang keluar dari perangkat Anda.",

    "nav_label": "Navigasi",
    "nav_output": "Temuan",
    "nav_how": "Cara kerja",
    "nav_why": "Bedanya",
    "nav_privacy": "Privasi",
    "nav_demo": "Demo",
    "lang_label": "Bahasa",
    "theme_label": "Terang / gelap",

    "hero_eyebrow": "Sumber terbuka · Berjalan di perangkat Anda",
    "hero_h1_a": "Tahu apa yang perlu",
    "hero_h1_b": "diubah",
    "hero_h1_c": "",
    "hero_lede": "Coding agent Anda sudah mencatat setiap giliran. Alat ini membaca catatan itu dan menyebut beberapa perubahan yang layak dilakukan — masing-masing dengan angkanya.",
    "chip1": "Siap dalam kurang dari satu menit",
    "chip2": "Tanpa akun",
    "chip3": "Tidak ada data yang keluar",
    "cta_demo": "Buka demo langsung",
    "cta_github": "Lihat kode",
    "run_comment": "60 hari data contoh, langsung jadi dasbor sungguhan",
    "run_note": "Hanya pustaka standar Python 3. Tanpa instalasi, tanpa dependensi, tanpa build.",

    "find_eyebrow": "Hasilnya",
    "find_h2": "Bukan angka. Langkah berikutnya",
    "find_note": "Lima belas pemeriksaan. Apa pun yang bernilai di bawah $15 per bulan diturunkan, jadi bagian atas daftar selalu berarti — dan pemakaian yang sehat memang dilaporkan sehat.",
    "prev_label": "Sebelumnya",
    "next_label": "Berikutnya",
    "sev_high": "Tinggi",
    "sev_med": "Sedang",
    "sev_low": "Rendah",

    "f1_title": "Anda membayar tarif puncak yang sebenarnya bisa dihindari",
    "f1_save": "≈ $34/bln",
    "f1_body": "61% pengeluaran Anda pada model bertarif waktu jatuh di jendela puncak, saat token yang sama bisa dua kali lebih mahal.",
    "f1_act": "Jadwalkan pekerjaan yang tak perlu ditunggui — tes, migrasi, penyisiran dokumen — ke jam di luar puncak.",

    "f2_title": "Konteks dibangun ulang, bukan dipakai ulang",
    "f2_save": "≈ $61/bln",
    "f2_body": "Pemakaian ulang cache hanya 38%. Membangun ulang konteks kira-kira 12× lebih mahal daripada membacanya kembali.",
    "f2_act": "Pakai satu sesi untuk tugas-tugas yang berkaitan. Selisih ini lebih besar daripada ganti model apa pun.",

    "f3_title": "Paket $18 Anda mengembalikan 23×",
    "f3_save": "23× balik modal",
    "f3_body": "Dengan tarif per token, pekerjaan yang sama berbiaya $412. Tidak ada yang perlu diperbaiki di sini.",
    "f3_act": "Pertahankan paketnya. Tinjau lagi jika giliran bulanan turun di bawah 400.",

    "how_eyebrow": "Cara kerjanya",
    "how_h2": "Tiga langkah, sekitar satu detik",
    "how_1_t": "Baca",
    "how_1_d": "Agent Anda sudah menulis lognya. Kami membaca berkas itu di tempatnya — tidak ada yang perlu dipasang atau dinyalakan.",
    "how_2_t": "Ukur",
    "how_2_d": "Token, cache, waktu, dan biaya — dihitung pada tarif yang benar-benar berlaku saat itu.",
    "how_3_t": "Bertindak",
    "how_3_d": "Daftar perubahan berperingkat, lengkap dengan buktinya dan nilainya per bulan.",
    "how_note": "Tanpa kunci API, tanpa proxy, tanpa akun, tanpa jaringan. Pengumpulan data memakai nol token.",

    "why_eyebrow": "Apa bedanya",
    "why_h2": "Dihitung sebagaimana Anda benar-benar membayar",
    "why_1_t": "Jam mengubah harga",
    "why_1_d": "DeepSeek dan GLM menagih per jam. Di UTC+7 sampai +9, jendela puncak mereka adalah sore kerja Anda.",
    "why_2_t": "Paket bukan tagihan",
    "why_2_d": "Pada paket $18, “Anda menghabiskan $412” itu fiksi. “23× balik modal” tidak.",
    "why_3_t": "Tarif cache beda tiap vendor",
    "why_3_d": "Diskon 0,1× itu kebiasaan Anthropic, bukan hukum alam. Salah di sini, angka terpenting di halaman ikut salah.",
    "why_4_t": "Tiga belas mata uang",
    "why_4_d": "IDR, VND, THB, PHP, MYR dan lainnya — disandingkan dengan upah harian setempat, karena $412 tidak berarti sama di mana-mana.",

    "priv_eyebrow": "Privasi",
    "priv_h2": "Mekanisme, bukan janji",
    "priv_lede": "Tidak ada yang keluar dari perangkat Anda kecuali Anda sendiri yang mengubah berkasnya.",
    "priv_1": "Tidak pernah disimpan: prompt, jawaban, kode, perintah, jalur berkas.",
    "priv_2": "Dihentikan di titik berkas dibaca — jadi kebocoran itu bug, bukan urusan kebijakan.",
    "priv_3": "Dasbor dan halaman ini nol permintaan eksternal. Tanpa CDN, tanpa font, tanpa analitik.",

    "start_cta1": "Buka demo langsung",

    "foot_tag": "Lisensi MIT · Lokal dulu · Tanpa akun",
    "foot_docs": "Dokumentasi",
    "foot_limits": "Batasan yang diketahui",
    "foot_contrib": "Berkontribusi",
}

STRINGS["vi"] = {
    # README-only; rendered by site/tools/readmes.py.
    "rm_quick": "Bắt đầu nhanh",
    "rm_own": "Rồi chạy trên chính dữ liệu của bạn:",
    "rm_docs_en": "Tài liệu đầy đủ — cấu hình, lệnh, đóng góp — bằng tiếng Anh:",
    "rm_translate": "Có chỗ nào đọc chưa xuôi? Mọi câu chữ trên trang này nằm trong `site/i18n.py`, mỗi ngôn ngữ một dict. Một tệp, không framework.",
    "rm_generated": "Được sinh ra từ chính phần chữ của website, nên trang này và website không thể nói khác nhau.",
    "brand": "AI Observatory",
    "meta_title": "AI Observatory — biết cần thay đổi điều gì",
    "meta_desc": "Đọc chính những log mà coding agent của bạn đã ghi, rồi rút ra một danh sách ngắn, xếp hạng: những thay đổi đáng làm. Miễn phí, chạy cục bộ, không cần tài khoản, không có gì rời khỏi máy bạn.",

    "nav_label": "Điều hướng",
    "nav_output": "Kết quả",
    "nav_how": "Cách hoạt động",
    "nav_why": "Khác biệt",
    "nav_privacy": "Riêng tư",
    "nav_demo": "Demo",
    "lang_label": "Ngôn ngữ",
    "theme_label": "Sáng / tối",

    "hero_eyebrow": "Mã nguồn mở · Chạy trên máy của bạn",
    "hero_h1_a": "Biết cần",
    "hero_h1_b": "thay đổi",
    "hero_h1_c": " điều gì",
    "hero_lede": "Agent của bạn vốn đã ghi lại từng lượt. Công cụ này đọc các log đó và chỉ ra vài thay đổi đáng làm — mỗi thay đổi kèm một con số.",
    "chip1": "Cài đặt trong chưa đầy một phút",
    "chip2": "Không cần tài khoản",
    "chip3": "Không gì rời khỏi máy bạn",
    "cta_demo": "Mở bản demo",
    "cta_github": "Xem mã nguồn",
    "run_comment": "60 ngày dữ liệu mẫu, ra thẳng bảng điều khiển thật",
    "run_note": "Chỉ dùng thư viện chuẩn Python 3. Không cài đặt, không phụ thuộc, không bước build.",

    "find_eyebrow": "Kết quả",
    "find_h2": "Không phải một con số. Là bước tiếp theo",
    "find_note": "Mười lăm phép kiểm tra. Mục nào đáng dưới 15 đô một tháng sẽ bị hạ bậc, nên đầu danh sách luôn có ý nghĩa — và nếu bạn đang dùng hợp lý, nó nói đúng là hợp lý.",
    "prev_label": "Trước",
    "next_label": "Sau",
    "sev_high": "Cao",
    "sev_med": "Trung bình",
    "sev_low": "Thấp",

    "f1_title": "Bạn đang trả giá giờ cao điểm mà lẽ ra không cần",
    "f1_save": "≈ 34 $/tháng",
    "f1_body": "61% chi tiêu trên các mô hình tính giá theo giờ rơi vào khung cao điểm, nơi cùng số token có thể đắt gấp đôi.",
    "f1_act": "Đẩy những việc không cần ngồi canh — sinh test, migration, quét tài liệu — sang giờ thấp điểm.",

    "f2_title": "Ngữ cảnh đang bị dựng lại thay vì tái dùng",
    "f2_save": "≈ 61 $/tháng",
    "f2_body": "Tỷ lệ tái dùng cache chỉ 38%. Dựng lại ngữ cảnh tốn khoảng 12 lần so với đọc lại nó.",
    "f2_act": "Giữ một phiên cho các việc liên quan thay vì mở lại. Khoảng cách này đáng giá hơn mọi lần đổi mô hình.",

    "f3_title": "Gói 18 đô của bạn đã trả lại gấp 23 lần",
    "f3_save": "gấp 23 lần",
    "f3_body": "Nếu tính theo lượng, cùng khối lượng việc đó tốn 412 đô. Ở đây không có gì cần sửa.",
    "f3_act": "Giữ nguyên gói. Xem lại khi số lượt mỗi tháng xuống dưới 400.",

    "how_eyebrow": "Cách hoạt động",
    "how_h2": "Ba bước, khoảng một giây",
    "how_1_t": "Đọc",
    "how_1_d": "Agent của bạn đã ghi log sẵn. Chúng tôi đọc chính các tệp đó tại chỗ — không phải cài gì, không phải bật gì.",
    "how_2_t": "Đo",
    "how_2_d": "Token, cache, thời điểm và chi phí — tính theo đúng mức giá đang áp dụng lúc chạy.",
    "how_3_t": "Hành động",
    "how_3_d": "Một danh sách thay đổi có xếp hạng, kèm bằng chứng và giá trị mỗi tháng.",
    "how_note": "Không API key, không proxy, không tài khoản, không mạng. Việc thu thập tốn 0 token.",

    "why_eyebrow": "Khác ở chỗ nào",
    "why_h2": "Tính đúng cách bạn thật sự trả tiền",
    "why_1_t": "Đồng hồ làm đổi giá",
    "why_1_d": "DeepSeek và GLM tính tiền theo giờ. Ở UTC+7 đến +9, khung cao điểm của họ đúng là buổi chiều làm việc của bạn.",
    "why_2_t": "Gói thuê bao không phải hoá đơn",
    "why_2_d": "Trên gói 18 đô, “bạn đã tiêu 412 đô” là hư cấu. “Gấp 23 lần” thì không.",
    "why_3_t": "Giá cache khác nhau theo nhà cung cấp",
    "why_3_d": "Mức 0,1× là thói quen của Anthropic, không phải quy luật. Sai chỗ này là sai con số lớn nhất trên trang.",
    "why_4_t": "Mười ba loại tiền tệ",
    "why_4_d": "VND, IDR, THB, PHP, MYR và hơn nữa — đặt cạnh mức công nhật địa phương, vì 412 đô không mang cùng một ý nghĩa ở mọi nơi.",

    "priv_eyebrow": "Riêng tư",
    "priv_h2": "Là cơ chế, không phải lời hứa",
    "priv_lede": "Không gì rời khỏi máy bạn, trừ khi chính bạn sửa tệp cấu hình để cho phép.",
    "priv_1": "Không bao giờ lưu: prompt, câu trả lời, mã nguồn, lệnh, đường dẫn tệp.",
    "priv_2": "Chặn ngay tại chỗ đọc tệp — nên rò rỉ là một lỗi, không phải câu chuyện chính sách.",
    "priv_3": "Bảng điều khiển và trang này không gửi bất kỳ yêu cầu ra ngoài nào. Không CDN, không font, không analytics.",

    "start_cta1": "Mở bản demo",

    "foot_tag": "Giấy phép MIT · Ưu tiên cục bộ · Không cần tài khoản",
    "foot_docs": "Tài liệu",
    "foot_limits": "Giới hạn đã biết",
    "foot_contrib": "Đóng góp",
}

STRINGS["th"] = {
    # README-only; rendered by site/tools/readmes.py.
    "rm_quick": "เริ่มต้นอย่างรวดเร็ว",
    "rm_own": "จากนั้นรันกับการใช้งานจริงของคุณ:",
    "rm_docs_en": "เอกสารฉบับเต็ม — การตั้งค่า คำสั่ง และการร่วมพัฒนา — เป็นภาษาอังกฤษ:",
    "rm_translate": "อ่านแล้วรู้สึกแปลกตรงไหน ทุกข้อความในหน้านี้อยู่ใน `site/i18n.py` ภาษาละหนึ่ง dict ไฟล์เดียว ไม่มีเฟรมเวิร์ก",
    "rm_generated": "สร้างจากข้อความชุดเดียวกับเว็บไซต์ หน้านี้กับเว็บไซต์จึงไม่มีทางพูดไม่ตรงกัน",
    "brand": "AI Observatory",
    "meta_title": "AI Observatory — รู้ว่าต้องเปลี่ยนอะไร",
    "meta_desc": "อ่านล็อกที่ coding agent ของคุณเขียนไว้อยู่แล้ว แล้วสรุปเป็นรายการสั้น ๆ ที่จัดลำดับไว้ว่าควรเปลี่ยนอะไร ฟรี ทำงานบนเครื่องคุณ ไม่ต้องมีบัญชี และไม่มีข้อมูลใดออกจากเครื่อง",

    "nav_label": "การนำทาง",
    "nav_output": "ผลลัพธ์",
    "nav_how": "วิธีทำงาน",
    "nav_why": "ต่างอย่างไร",
    "nav_privacy": "ความเป็นส่วนตัว",
    "nav_demo": "เดโม",
    "lang_label": "ภาษา",
    "theme_label": "สว่าง / มืด",

    "hero_eyebrow": "โอเพนซอร์ส · ทำงานบนเครื่องของคุณ",
    "hero_h1_a": "รู้ว่าต้อง",
    "hero_h1_b": "เปลี่ยนอะไร",
    "hero_h1_c": "",
    "hero_lede": "agent ของคุณบันทึกทุกเทิร์นไว้อยู่แล้ว เครื่องมือนี้อ่านบันทึกเหล่านั้น แล้วบอกว่ามีไม่กี่อย่างที่ควรเปลี่ยน — พร้อมตัวเลขกำกับทุกข้อ",
    "chip1": "ตั้งค่าเสร็จในไม่ถึงหนึ่งนาที",
    "chip2": "ไม่ต้องมีบัญชี",
    "chip3": "ไม่มีข้อมูลออกจากเครื่อง",
    "cta_demo": "เปิดเดโม",
    "cta_github": "ดูซอร์สโค้ด",
    "run_comment": "ข้อมูลตัวอย่าง 60 วัน แล้วได้แดชบอร์ดจริงเลย",
    "run_note": "ใช้เฉพาะไลบรารีมาตรฐานของ Python 3 ไม่ต้องติดตั้ง ไม่มี dependency ไม่มีขั้นตอน build",

    "find_eyebrow": "ผลลัพธ์",
    "find_h2": "ไม่ใช่ตัวเลข แต่คือก้าวต่อไป",
    "find_note": "การตรวจสิบห้าแบบ อะไรที่มีมูลค่าต่ำกว่า 15 ดอลลาร์ต่อเดือนจะถูกลดอันดับ หัวรายการจึงมีความหมายเสมอ — และถ้าคุณใช้งานได้ดีอยู่แล้ว มันก็จะบอกตามนั้น",
    "prev_label": "ก่อนหน้า",
    "next_label": "ถัดไป",
    "sev_high": "สูง",
    "sev_med": "กลาง",
    "sev_low": "ต่ำ",

    "f1_title": "คุณกำลังจ่ายราคาช่วงพีคทั้งที่ไม่จำเป็น",
    "f1_save": "≈ 34 ดอลลาร์/เดือน",
    "f1_body": "61% ของค่าใช้จ่ายบนโมเดลที่คิดราคาตามเวลา ตกอยู่ในช่วงพีค ซึ่งโทเคนเท่าเดิมอาจแพงขึ้นถึงสองเท่า",
    "f1_act": "งานที่ไม่ต้องนั่งเฝ้า — สร้างเทสต์ ย้ายโครงสร้าง ไล่แก้เอกสาร — ให้เลื่อนไปรันช่วงนอกพีค",

    "f2_title": "คอนเท็กซ์ถูกสร้างใหม่ ไม่ได้ถูกใช้ซ้ำ",
    "f2_save": "≈ 61 ดอลลาร์/เดือน",
    "f2_body": "อัตราการใช้แคชซ้ำอยู่ที่ 38% การสร้างคอนเท็กซ์ใหม่แพงกว่าการอ่านกลับราว 12 เท่า",
    "f2_act": "ทำงานที่เกี่ยวข้องกันในเซสชันเดียวแทนการเปิดใหม่ ช่องว่างนี้คุ้มกว่าการเปลี่ยนโมเดลใด ๆ",

    "f3_title": "แพ็กเกจ 18 ดอลลาร์ของคุณให้ผลตอบแทน 23 เท่า",
    "f3_save": "23 เท่า",
    "f3_body": "ถ้าคิดตามการใช้จริง งานเท่ากันนี้จะราคา 412 ดอลลาร์ ตรงนี้ไม่มีอะไรต้องแก้",
    "f3_act": "ใช้แพ็กเกจนี้ต่อไป กลับมาดูอีกครั้งเมื่อจำนวนเทิร์นต่อเดือนต่ำกว่า 400",

    "how_eyebrow": "วิธีทำงาน",
    "how_h2": "สามขั้นตอน ราวหนึ่งวินาที",
    "how_1_t": "อ่าน",
    "how_1_d": "agent ของคุณเขียนล็อกไว้แล้ว เราอ่านไฟล์เหล่านั้นตรงที่มันอยู่ — ไม่ต้องติดตั้ง ไม่ต้องเปิดใช้อะไรเลย",
    "how_2_t": "วัด",
    "how_2_d": "โทเคน แคช ช่วงเวลา และต้นทุน — คิดตามอัตราที่มีผลจริงตอนงานนั้นรัน",
    "how_3_t": "ลงมือ",
    "how_3_d": "รายการสิ่งที่ควรเปลี่ยน จัดลำดับไว้ พร้อมหลักฐานและมูลค่าต่อเดือน",
    "how_note": "ไม่ต้องใช้ API key ไม่ต้องมีพร็อกซี ไม่ต้องมีบัญชี ไม่ต้องต่อเน็ต การเก็บข้อมูลใช้โทเคนเป็นศูนย์",

    "why_eyebrow": "ต่างอย่างไร",
    "why_h2": "คิดราคาตามที่คุณจ่ายจริง",
    "why_1_t": "เวลาเปลี่ยนราคา",
    "why_1_d": "DeepSeek และ GLM คิดราคาตามช่วงเวลา ในโซน UTC+7 ถึง +9 ช่วงพีคของพวกเขาคือบ่ายของวันทำงานคุณพอดี",
    "why_2_t": "แพ็กเกจไม่ใช่บิล",
    "why_2_d": "บนแพ็กเกจ 18 ดอลลาร์ คำว่า “คุณใช้ไป 412 ดอลลาร์” คือเรื่องแต่ง แต่ “คืนทุน 23 เท่า” ไม่ใช่",
    "why_3_t": "อัตราแคชต่างกันตามผู้ให้บริการ",
    "why_3_d": "ส่วนลด 0.1× เป็นธรรมเนียมของ Anthropic ไม่ใช่กฎ ถ้าคิดผิด ตัวเลขที่สำคัญที่สุดบนหน้าก็ผิดตาม",
    "why_4_t": "สิบสามสกุลเงิน",
    "why_4_d": "THB, IDR, VND, PHP, MYR และอื่น ๆ — เทียบกับค่าแรงรายวันในพื้นที่ เพราะ 412 ดอลลาร์ไม่ได้มีความหมายเท่ากันทุกที่",

    "priv_eyebrow": "ความเป็นส่วนตัว",
    "priv_h2": "เป็นกลไก ไม่ใช่คำสัญญา",
    "priv_lede": "ไม่มีอะไรออกจากเครื่องคุณ เว้นแต่คุณจะแก้ไฟล์เพื่ออนุญาตเอง",
    "priv_1": "ไม่เก็บเด็ดขาด: พรอมป์ต์ คำตอบ โค้ด คำสั่ง และพาธไฟล์",
    "priv_2": "ปิดกั้นตั้งแต่จุดที่อ่านไฟล์ — การรั่วไหลจึงเป็นบั๊ก ไม่ใช่เรื่องนโยบาย",
    "priv_3": "ทั้งแดชบอร์ดและหน้านี้ไม่มีการเรียกภายนอกเลย ไม่มี CDN ไม่มีฟอนต์ ไม่มี analytics",

    "start_cta1": "เปิดเดโม",

    "foot_tag": "สัญญาอนุญาต MIT · ทำงานบนเครื่องเป็นหลัก · ไม่ต้องมีบัญชี",
    "foot_docs": "เอกสาร",
    "foot_limits": "ข้อจำกัดที่ทราบ",
    "foot_contrib": "ร่วมพัฒนา",
}

STRINGS["ms"] = {
    # README-only; rendered by site/tools/readmes.py.
    "rm_quick": "Mula pantas",
    "rm_own": "Kemudian pada penggunaan anda sendiri:",
    "rm_docs_en": "Dokumentasi penuh — konfigurasi, arahan, sumbangan — dalam bahasa Inggeris:",
    "rm_translate": "Ada yang berbunyi janggal? Semua teks di halaman ini ada dalam `site/i18n.py`, satu dict setiap bahasa. Satu fail, tiada framework.",
    "rm_generated": "Dijana daripada teks laman web itu sendiri, jadi halaman ini dan laman web tidak mungkin bercanggah.",
    "brand": "AI Observatory",
    "meta_title": "AI Observatory — tahu apa yang perlu diubah",
    "meta_desc": "Membaca log yang sudah ditulis oleh coding agent anda, lalu menjadikannya senarai pendek yang tersusun: perubahan yang benar-benar berbaloi. Percuma, tempatan, tanpa akaun, tiada data keluar dari mesin anda.",

    "nav_label": "Navigasi",
    "nav_output": "Penemuan",
    "nav_how": "Cara kerja",
    "nav_why": "Bezanya",
    "nav_privacy": "Privasi",
    "nav_demo": "Demo",
    "lang_label": "Bahasa",
    "theme_label": "Cerah / gelap",

    "hero_eyebrow": "Sumber terbuka · Berjalan pada mesin anda",
    "hero_h1_a": "Tahu apa yang perlu",
    "hero_h1_b": "diubah",
    "hero_h1_c": "",
    "hero_lede": "Coding agent anda sudah pun merekod setiap giliran. Alat ini membaca rekod itu dan menyebut beberapa perubahan yang berbaloi — setiap satu dengan angkanya.",
    "chip1": "Sedia dalam kurang seminit",
    "chip2": "Tanpa akaun",
    "chip3": "Tiada data keluar dari mesin anda",
    "cta_demo": "Buka demo langsung",
    "cta_github": "Lihat kod sumber",
    "run_comment": "60 hari data contoh, terus jadi papan pemuka sebenar",
    "run_note": "Pustaka standard Python 3 sahaja. Tanpa pemasangan, tanpa kebergantungan, tanpa langkah build.",

    "find_eyebrow": "Hasilnya",
    "find_h2": "Bukan angka. Langkah seterusnya",
    "find_note": "Lima belas pemeriksaan. Apa-apa yang bernilai bawah $15 sebulan diturunkan, jadi bahagian atas senarai sentiasa bermakna — dan penggunaan yang sihat memang dilaporkan sihat.",
    "prev_label": "Sebelum",
    "next_label": "Seterusnya",
    "sev_high": "Tinggi",
    "sev_med": "Sederhana",
    "sev_low": "Rendah",

    "f1_title": "Anda membayar kadar waktu puncak yang sebenarnya boleh dielak",
    "f1_save": "≈ $34/bln",
    "f1_body": "61% perbelanjaan anda pada model berharga mengikut masa jatuh dalam tetingkap puncak, di mana token yang sama boleh dua kali ganda mahal.",
    "f1_act": "Jadualkan kerja yang tidak perlu ditunggu — ujian, migrasi, kemas kini dokumen — ke jam luar puncak.",

    "f2_title": "Konteks dibina semula, bukan diguna semula",
    "f2_save": "≈ $61/bln",
    "f2_body": "Guna semula cache hanya 38%. Membina semula konteks kira-kira 12× lebih mahal daripada membacanya kembali.",
    "f2_act": "Kekalkan satu sesi untuk kerja yang berkaitan. Jurang ini lebih bernilai daripada menukar mana-mana model.",

    "f3_title": "Pelan $18 anda memulangkan 23×",
    "f3_save": "pulangan 23×",
    "f3_body": "Pada kadar per token, kerja yang sama berharga $412. Tiada apa yang perlu dibaiki di sini.",
    "f3_act": "Kekalkan pelan itu. Tinjau semula jika giliran bulanan jatuh bawah 400.",

    "how_eyebrow": "Cara ia berfungsi",
    "how_h2": "Tiga langkah, kira-kira sesaat",
    "how_1_t": "Baca",
    "how_1_d": "Agent anda sudah menulis lognya. Kami membaca fail itu di tempatnya — tiada apa perlu dipasang atau dihidupkan.",
    "how_2_t": "Ukur",
    "how_2_d": "Token, cache, masa dan kos — dikira pada kadar yang benar-benar berkuat kuasa ketika itu.",
    "how_3_t": "Bertindak",
    "how_3_d": "Senarai perubahan yang tersusun, lengkap dengan buktinya dan nilainya sebulan.",
    "how_note": "Tanpa kunci API, tanpa proksi, tanpa akaun, tanpa rangkaian. Pengumpulan data menggunakan sifar token.",

    "why_eyebrow": "Apa bezanya",
    "why_h2": "Dikira mengikut cara anda benar-benar membayar",
    "why_1_t": "Jam mengubah harga",
    "why_1_d": "DeepSeek dan GLM mengenakan bayaran mengikut jam. Di UTC+7 hingga +9, tetingkap puncak mereka ialah petang kerja anda.",
    "why_2_t": "Pelan bukan bil",
    "why_2_d": "Pada pelan $18, “anda belanja $412” itu rekaan. “Pulangan 23×” tidak.",
    "why_3_t": "Kadar cache berbeza ikut vendor",
    "why_3_d": "Diskaun 0.1× ialah kebiasaan Anthropic, bukan hukum. Silap di sini, angka terpenting di halaman ikut silap.",
    "why_4_t": "Tiga belas mata wang",
    "why_4_d": "MYR, IDR, VND, THB, PHP dan lagi — disandingkan dengan kadar harian tempatan, kerana $412 tidak bermakna sama di mana-mana.",

    "priv_eyebrow": "Privasi",
    "priv_h2": "Satu mekanisme, bukan janji",
    "priv_lede": "Tiada apa-apa keluar dari mesin anda melainkan anda sendiri mengubah fail untuk membenarkannya.",
    "priv_1": "Tidak pernah disimpan: prompt, jawapan, kod, arahan, laluan fail.",
    "priv_2": "Dihalang pada titik fail dibaca — jadi kebocoran ialah pepijat, bukan soal dasar.",
    "priv_3": "Papan pemuka dan halaman ini sifar permintaan luar. Tanpa CDN, tanpa fon, tanpa analitik.",

    "start_cta1": "Buka demo langsung",

    "foot_tag": "Lesen MIT · Tempatan dahulu · Tanpa akaun",
    "foot_docs": "Dokumentasi",
    "foot_limits": "Batasan diketahui",
    "foot_contrib": "Menyumbang",
}

STRINGS["fil"] = {
    # README-only; rendered by site/tools/readmes.py.
    "rm_quick": "Mabilisang simula",
    "rm_own": "Tapos sa sarili mong paggamit:",
    "rm_docs_en": "Ang buong dokumentasyon — configuration, mga command, pag-ambag — ay nasa Ingles:",
    "rm_translate": "May tunog na mali? Nasa `site/i18n.py` ang bawat teksto sa pahinang ito, isang dict kada wika. Isang file, walang framework.",
    "rm_generated": "Ginawa mula sa mismong teksto ng site, kaya hindi maaaring magkaiba ang pahinang ito at ang site.",
    "brand": "AI Observatory",
    "meta_title": "AI Observatory — alamin kung ano ang dapat baguhin",
    "meta_desc": "Binabasa ang mga log na isinusulat na ng iyong coding agent, at ginagawang maikling nakaranggong listahan ng mga pagbabagong sulit gawin. Libre, lokal, walang account, at walang datos na lumalabas ng iyong makina.",

    "nav_label": "Nabigasyon",
    "nav_output": "Natuklasan",
    "nav_how": "Paano",
    "nav_why": "Pagkakaiba",
    "nav_privacy": "Privacy",
    "nav_demo": "Demo",
    "lang_label": "Wika",
    "theme_label": "Maliwanag / madilim",

    "hero_eyebrow": "Open source · Tumatakbo sa sarili mong makina",
    "hero_h1_a": "Alamin kung ano ang dapat",
    "hero_h1_b": "baguhin",
    "hero_h1_c": "",
    "hero_lede": "Nakatala na ng iyong agent ang bawat turn. Binabasa ito ng tool at sinasabi ang iilang pagbabagong sulit gawin — bawat isa ay may kasamang numero.",
    "chip1": "Handa sa wala pang isang minuto",
    "chip2": "Walang account",
    "chip3": "Walang lumalabas ng makina mo",
    "cta_demo": "Buksan ang live demo",
    "cta_github": "Tingnan ang source",
    "run_comment": "60 araw na sample data, tapos ang totoong dashboard",
    "run_note": "Python 3 standard library lang. Walang install, walang dependency, walang build.",

    "find_eyebrow": "Ang resulta",
    "find_h2": "Hindi numero. Susunod na hakbang",
    "find_note": "Labinlimang pagsusuri. Anumang wala pang $15 kada buwan ang halaga ay ibinababa, kaya laging may saysay ang nasa itaas — at kung maayos ang paggamit mo, sasabihin nitong maayos.",
    "prev_label": "Nakaraan",
    "next_label": "Susunod",
    "sev_high": "Mataas",
    "sev_med": "Katamtaman",
    "sev_low": "Mababa",

    "f1_title": "Nagbabayad ka ng peak rate na hindi naman kailangan",
    "f1_save": "≈ $34/buwan",
    "f1_body": "61% ng gastos mo sa mga modelong naka-presyo ayon sa oras ay bumagsak sa peak window, kung saan hanggang doble ang halaga ng parehong token.",
    "f1_act": "Ilipat sa off-peak na oras ang trabahong hindi mo naman kailangang bantayan — test, migration, doc sweep.",

    "f2_title": "Muling itinatayo ang konteksto sa halip na gamitin ulit",
    "f2_save": "≈ $61/buwan",
    "f2_body": "38% lang ang cache reuse. Ang muling pagtatayo ng konteksto ay mga 12× ang mahal kaysa basahin itong muli.",
    "f2_act": "Panatilihin ang isang session para sa magkakaugnay na gawain. Mas malaki ang epekto nito kaysa sa pagpapalit ng modelo.",

    "f3_title": "Nagbalik ng 23× ang $18 mong plano",
    "f3_save": "23× na balik",
    "f3_body": "Kung per token, $412 sana ang parehong trabaho. Walang kailangang ayusin dito.",
    "f3_act": "Manatili sa plano. Balikan kapag bumaba sa 400 ang buwanang turn.",

    "how_eyebrow": "Paano ito gumagana",
    "how_h2": "Tatlong hakbang, mga isang segundo",
    "how_1_t": "Basahin",
    "how_1_d": "Naisulat na ng agent mo ang mga log. Binabasa namin ang mga file na iyon kung nasaan sila — walang i-install, walang buksan.",
    "how_2_t": "Sukatin",
    "how_2_d": "Token, cache, oras at gastos — sa presyong talagang umiiral noong tumakbo ang trabaho.",
    "how_3_t": "Kumilos",
    "how_3_d": "Nakaranggong listahan ng mga pagbabago, may ebidensiya at halaga kada buwan.",
    "how_note": "Walang API key, walang proxy, walang account, walang network. Zero token ang gastos ng pangongolekta.",

    "why_eyebrow": "Bakit ito kakaiba",
    "why_h2": "Nakapresyo ayon sa totoong paraan ng pagbabayad mo",
    "why_1_t": "Binabago ng orasan ang presyo",
    "why_1_d": "Oras-oras maningil ang DeepSeek at GLM. Sa UTC+7 hanggang +9, ang peak window nila ang hapon mong trabaho.",
    "why_2_t": "Hindi bill ang plano",
    "why_2_d": "Sa $18 na plano, kathang-isip ang “gumastos ka ng $412.” Ang “23× na balik” ay hindi.",
    "why_3_t": "Iba-iba ang cache rate kada vendor",
    "why_3_d": "Ugali ng Anthropic ang 0.1×, hindi batas. Mali dito, mali ang pinakamahalagang numero sa pahina.",
    "why_4_t": "Labintatlong pera",
    "why_4_d": "PHP, IDR, VND, THB, MYR at iba pa — katabi ng lokal na arawang kita, dahil hindi pare-pareho ang bigat ng $412 saanman.",

    "priv_eyebrow": "Privacy",
    "priv_h2": "Mekanismo, hindi pangako",
    "priv_lede": "Walang lumalabas ng makina mo maliban kung ikaw mismo ang mag-edit ng file para payagan ito.",
    "priv_1": "Hindi kailanman iniimbak: prompt, sagot, code, command, file path.",
    "priv_2": "Hinaharang sa mismong pagbasa ng file — kaya bug ang leak, hindi usapin ng patakaran.",
    "priv_3": "Zero external request ang dashboard at ang pahinang ito. Walang CDN, walang font, walang analytics.",

    "start_cta1": "Buksan ang live demo",

    "foot_tag": "MIT license · Lokal muna · Walang account",
    "foot_docs": "Dokumentasyon",
    "foot_limits": "Kilalang limitasyon",
    "foot_contrib": "Mag-ambag",
}

STRINGS["pt-BR"] = {
    # README-only; rendered by site/tools/readmes.py.
    "rm_quick": "Início rápido",
    "rm_own": "Depois, no seu próprio uso:",
    "rm_docs_en": "A documentação completa — configuração, comandos, contribuição — está em inglês:",
    "rm_translate": "Algo soou estranho? Todo texto desta página está em `site/i18n.py`, um dict por idioma. Um arquivo, sem framework.",
    "rm_generated": "Gerado a partir do próprio texto do site, então esta página e o site não podem divergir.",
    "brand": "AI Observatory",
    "meta_title": "AI Observatory — saiba o que mudar",
    "meta_desc": "Lê os logs que o seu agente de código já grava e os transforma em uma lista curta e ordenada das mudanças que valem a pena. Grátis, local, sem conta, e nada sai da sua máquina.",

    "nav_label": "Navegação",
    "nav_output": "Resultados",
    "nav_how": "Como funciona",
    "nav_why": "Diferença",
    "nav_privacy": "Privacidade",
    "nav_demo": "Demo",
    "lang_label": "Idioma",
    "theme_label": "Claro / escuro",

    "hero_eyebrow": "Código aberto · Roda na sua máquina",
    "hero_h1_a": "Saiba o que",
    "hero_h1_b": "mudar",
    "hero_h1_c": "",
    "hero_lede": "Seu agente de código já registra cada turno. Isto lê esses registros e aponta as poucas mudanças que valem a pena — cada uma com um número junto.",
    "chip1": "Pronto em menos de um minuto",
    "chip2": "Sem conta",
    "chip3": "Nada sai da sua máquina",
    "cta_demo": "Abrir a demo",
    "cta_github": "Ver o código",
    "run_comment": "60 dias de dados de exemplo e o painel de verdade",
    "run_note": "Apenas a biblioteca padrão do Python 3. Sem instalação, sem dependências, sem build.",

    "find_eyebrow": "O resultado",
    "find_h2": "Não é um número. É o próximo passo",
    "find_note": "Quinze verificações. O que vale menos de US$ 15 por mês é rebaixado, então o topo da lista sempre significa algo — e um uso saudável é relatado como saudável.",
    "prev_label": "Anterior",
    "next_label": "Próximo",
    "sev_high": "Alta",
    "sev_med": "Média",
    "sev_low": "Baixa",

    "f1_title": "Você paga tarifa de pico sem precisar",
    "f1_save": "≈ US$ 34/mês",
    "f1_body": "61% do seu gasto em modelos com preço por horário caiu dentro da janela de pico, onde os mesmos tokens custam até o dobro.",
    "f1_act": "Programe para fora do pico o trabalho que não exige acompanhamento — testes, migrações, varreduras de documentação.",

    "f2_title": "O contexto está sendo reconstruído, não reaproveitado",
    "f2_save": "≈ US$ 61/mês",
    "f2_body": "O reaproveitamento de cache está em 38%. Reconstruir o contexto custa cerca de 12× o que custa relê-lo.",
    "f2_act": "Mantenha uma sessão para tarefas relacionadas em vez de recomeçar. Essa diferença vale mais que trocar de modelo.",

    "f3_title": "Seu plano de US$ 18 devolveu 23×",
    "f3_save": "retorno de 23×",
    "f3_body": "No preço por token, o mesmo trabalho custaria US$ 412. Não há nada a corrigir aqui.",
    "f3_act": "Mantenha o plano. Reavalie se os turnos mensais caírem abaixo de 400.",

    "how_eyebrow": "Como funciona",
    "how_h2": "Três passos, cerca de um segundo",
    "how_1_t": "Ler",
    "how_1_d": "Seu agente já gravou os logs. A gente lê esses arquivos onde eles estão — nada para instalar, nada para ativar.",
    "how_2_t": "Medir",
    "how_2_d": "Tokens, cache, horário e custo — pelo preço que realmente estava valendo na hora.",
    "how_3_t": "Agir",
    "how_3_d": "Uma lista ordenada de mudanças, cada uma com a evidência e quanto vale por mês.",
    "how_note": "Sem chave de API, sem proxy, sem conta, sem rede. A coleta custa zero tokens.",

    "why_eyebrow": "Por que é diferente",
    "why_h2": "Calculado do jeito que você paga de verdade",
    "why_1_t": "O relógio muda o preço",
    "why_1_d": "DeepSeek e GLM cobram por horário. De UTC+7 a +9, a janela de pico deles é a sua tarde de trabalho.",
    "why_2_t": "Plano não é fatura",
    "why_2_d": "Num plano de US$ 18, “você gastou US$ 412” é ficção. “Retorno de 23×” não é.",
    "why_3_t": "A taxa de cache muda por fornecedor",
    "why_3_d": "O desconto de 0,1× é um costume da Anthropic, não uma lei. Errar isso é errar o maior número da página.",
    "why_4_t": "Treze moedas",
    "why_4_d": "BRL, IDR, VND, THB, PHP, MYR e outras — comparadas a uma diária local, porque US$ 412 não significa a mesma coisa em todo lugar.",

    "priv_eyebrow": "Privacidade",
    "priv_h2": "Um mecanismo, não uma promessa",
    "priv_lede": "Nada sai da sua máquina a menos que você edite um arquivo autorizando.",
    "priv_1": "Nunca armazenado: prompts, respostas, código, comandos, caminhos de arquivo.",
    "priv_2": "Bloqueado no ponto em que o arquivo é lido — então um vazamento seria um bug, não uma questão de política.",
    "priv_3": "O painel e esta página fazem zero requisições externas. Sem CDN, sem fontes, sem analytics.",

    "start_cta1": "Abrir a demo",

    "foot_tag": "Licença MIT · Local em primeiro lugar · Sem conta",
    "foot_docs": "Documentação",
    "foot_limits": "Limitações conhecidas",
    "foot_contrib": "Contribuir",
}

STRINGS["es"] = {
    # README-only; rendered by site/tools/readmes.py.
    "rm_quick": "Inicio rápido",
    "rm_own": "Luego, sobre tu propio uso:",
    "rm_docs_en": "La documentación completa — configuración, comandos, contribución — está en inglés:",
    "rm_translate": "¿Algo suena raro? Todo el texto de esta página está en `site/i18n.py`, un dict por idioma. Un archivo, sin framework.",
    "rm_generated": "Generado a partir del propio texto del sitio, así que esta página y el sitio no pueden contradecirse.",
    "brand": "AI Observatory",
    "meta_title": "AI Observatory — saber qué cambiar",
    "meta_desc": "Lee los registros que tu agente de código ya escribe y los convierte en una lista corta y ordenada de los cambios que merecen la pena. Gratis, local, sin cuenta, y nada sale de tu máquina.",

    "nav_label": "Navegación",
    "nav_output": "Hallazgos",
    "nav_how": "Cómo funciona",
    "nav_why": "Diferencia",
    "nav_privacy": "Privacidad",
    "nav_demo": "Demo",
    "lang_label": "Idioma",
    "theme_label": "Claro / oscuro",

    "hero_eyebrow": "Código abierto · Funciona en tu máquina",
    "hero_h1_a": "Saber qué",
    "hero_h1_b": "cambiar",
    "hero_h1_c": "",
    "hero_lede": "Tu agente de código ya registra cada turno. Esto lee esos registros y te dice los pocos cambios que merecen la pena, cada uno con una cifra al lado.",
    "chip1": "Listo en menos de un minuto",
    "chip2": "Sin cuenta",
    "chip3": "Nada sale de tu máquina",
    "cta_demo": "Abrir la demo",
    "cta_github": "Ver el código",
    "run_comment": "60 días de datos de ejemplo y el panel de verdad",
    "run_note": "Solo la biblioteca estándar de Python 3. Sin instalación, sin dependencias, sin build.",

    "find_eyebrow": "El resultado",
    "find_h2": "No es una cifra. Es el siguiente paso",
    "find_note": "Quince comprobaciones. Lo que vale menos de 15 $ al mes baja de puesto, así que lo primero de la lista siempre importa — y si tu uso es sano, lo dice tal cual.",
    "prev_label": "Anterior",
    "next_label": "Siguiente",
    "sev_high": "Alta",
    "sev_med": "Media",
    "sev_low": "Baja",

    "f1_title": "Estás pagando tarifa punta sin necesidad",
    "f1_save": "≈ 34 $/mes",
    "f1_body": "El 61 % de tu gasto en modelos con precio por horas cayó dentro de la franja punta, donde los mismos tokens cuestan hasta el doble.",
    "f1_act": "Programa fuera de punta el trabajo que no hace falta vigilar: pruebas, migraciones, barridos de documentación.",

    "f2_title": "El contexto se reconstruye en lugar de reutilizarse",
    "f2_save": "≈ 61 $/mes",
    "f2_body": "La reutilización de caché está en el 38 %. Reconstruir el contexto cuesta unas 12 veces lo que cuesta releerlo.",
    "f2_act": "Mantén una sesión para tareas relacionadas en vez de empezar de cero. Esta diferencia vale más que cambiar de modelo.",

    "f3_title": "Tu plan de 18 $ devolvió 23×",
    "f3_save": "retorno de 23×",
    "f3_body": "Con precio por token, el mismo trabajo habría costado 412 $. Aquí no hay nada que arreglar.",
    "f3_act": "Sigue con el plan. Revísalo si los turnos mensuales bajan de 400.",

    "how_eyebrow": "Cómo funciona",
    "how_h2": "Tres pasos, un segundo aproximadamente",
    "how_1_t": "Leer",
    "how_1_d": "Tu agente ya escribió los registros. Leemos esos archivos donde están: nada que instalar, nada que activar.",
    "how_2_t": "Medir",
    "how_2_d": "Tokens, caché, horario y coste, al precio que de verdad estaba vigente cuando se ejecutó.",
    "how_3_t": "Actuar",
    "how_3_d": "Una lista ordenada de cambios, cada uno con su evidencia y lo que vale al mes.",
    "how_note": "Sin clave de API, sin proxy, sin cuenta, sin red. Recoger los datos cuesta cero tokens.",

    "why_eyebrow": "Por qué es distinto",
    "why_h2": "Calculado como pagas de verdad",
    "why_1_t": "El reloj cambia el precio",
    "why_1_d": "DeepSeek y GLM cobran por franja horaria. De UTC+7 a +9, su hora punta es tu tarde de trabajo.",
    "why_2_t": "Un plan no es una factura",
    "why_2_d": "Con un plan de 18 $, «has gastado 412 $» es ficción. «Retorno de 23×» no lo es.",
    "why_3_t": "La tarifa de caché cambia según el proveedor",
    "why_3_d": "El descuento de 0,1× es una costumbre de Anthropic, no una ley. Fallar ahí es fallar la cifra más importante de la página.",
    "why_4_t": "Trece monedas",
    "why_4_d": "IDR, VND, THB, PHP, MYR y más, comparadas con un jornal local, porque 412 $ no significan lo mismo en todas partes.",

    "priv_eyebrow": "Privacidad",
    "priv_h2": "Un mecanismo, no una promesa",
    "priv_lede": "Nada sale de tu máquina salvo que edites un archivo para permitirlo.",
    "priv_1": "Nunca se guarda: prompts, respuestas, código, comandos, rutas de archivo.",
    "priv_2": "Se bloquea en el punto donde se lee el archivo, así que una fuga sería un fallo, no una cuestión de política.",
    "priv_3": "El panel y esta página no hacen ninguna petición externa. Sin CDN, sin fuentes, sin analítica.",

    "start_cta1": "Abrir la demo",

    "foot_tag": "Licencia MIT · Local primero · Sin cuenta",
    "foot_docs": "Documentación",
    "foot_limits": "Limitaciones conocidas",
    "foot_contrib": "Contribuir",
}


def strings(code: str) -> dict:
    """Every key for `code`, with English filling any gap.

    A missing key is a translation still in progress, not a bug worth failing a
    build over — so the page renders that one line in English and everything
    else in the reader's language.
    """
    merged = dict(STRINGS["en"])
    merged.update(STRINGS.get(code, {}))
    return merged


def missing() -> dict:
    """Keys each locale still inherits from English. Printed by the build."""
    ref = set(STRINGS["en"])
    return {c: sorted(ref - set(STRINGS.get(c, {})))
            for c, *_ in LOCALES if c != "en" and ref - set(STRINGS.get(c, {}))}
