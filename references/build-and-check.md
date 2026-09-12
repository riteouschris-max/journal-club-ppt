# 构建、缓存和检查

只在需要运行构建时读取。已有源工程继续用原来的构建器；以下脚本是新项目的可复用起点。

## 项目与输入

优先用 `scripts/run.py doctor` 检查；缺包时运行根目录 `setup.py`。后续 `run.py` 自动调用本技能 `.venv`，没有 `.venv` 时才使用当前解释器。只需要本技能列出的依赖，不读取其他技能的运行环境。`load_workspace_dependencies` 是可用时的 Python 定位帮助，不是硬依赖。

以下 `python` 应使用本技能 `.venv` 的解释器，或通过 `run.py project ...`、`run.py build ...`、`run.py audit ...` 包装。新项目自动选用实际存在的中文字体，写入项目 theme；已有项目字体不被静默替换。换设备后重新 doctor，若项目里的 `font_file` 已失效，更新到实际字体并重新全套渲染检查。

Windows 上为中文文件启用 `PYTHONUTF8=1` 和 `PYTHONIOENCODING=utf-8`。渲染器路径先检查是否存在；项目目录可能被移动，不能反复调用失效旧路径。

下列命令中的 `python` 替换成实际 Python，`SKILL` 和 `WORK` 用已解析绝对路径。脚本默认只输出小摘要；读取源码仅在修复脚本时必要。

```text
python SKILL/scripts/project.py init --workspace WORK --paper INPUT.pdf
python SKILL/scripts/project.py text --workspace WORK --pages 1-3,8
python SKILL/scripts/project.py preview --workspace WORK --pages 8
python SKILL/scripts/project.py crop --workspace WORK --request WORK/crops.json
```

同一 PDF 的文本缓存直接复用。不同 PDF 不能静默覆盖同一项目。预览命令返回图片路径，用图像查看工具检查原图；`crop` 不判断实验含义。

`init` 报告低文本量页面；扫描 PDF 需要查看原页并按需 OCR，不能把空文本缓存视为读完论文。OCR 仅帮助检索，组别、统计符号和基因名仍需核对原图。

`crops.json` 是数组，页码从 1 开始，rect 使用 PDF points，而非预览 PNG 像素。先从 `cache/index.json` 查页面尺寸，再把已查看的图像坐标换算回 PDF。示意：

```json
[{"id":"F2_A","page":7,"rect":[40,70,300,200],"dpi":450,
  "panel":"Fig.2A","readout":"填写从图注核对的指标"}]
```

先在原图预览核验区域确实包含完整轴、图例、panel 字母和标尺，再写真实坐标。不得照抄示意坐标。裁图命令生成 `assets.json`，包含来源 PDF 哈希、页/区域、图像哈希、尺寸。

外部概念插画另加到 `assets.json`：`{"path":"assets/concept.png","sha256":"实际文件哈希","kind":"concept"}`；用户提供的封面图片用 `kind: "user-cover"`。实验图片使用 `kind: "evidence"`，不能把概念图改标签伪装成证据。

补充材料单独缓存并核对，原 PDF 保存在项目内。导入其裁图时记录 `source_path`（如 `source/supplement.pdf`）及 `source_sha256`，避免把补图误标为正文页。已有原图缓存可直接按其来源记录导入，无须重新裁切。

## 科学清单与内容数据

`figure_inventory.json` 每个原 panel 一行。必须通过看原图与图注才把 `verified` 设为 true；它不是自动检查的替代品。

```json
[{"id":"Fig2A","assets":["F2_A"],"critical":true,
  "verified":true,"disposition":"slide","slide_ids":["result-02"]}]
```

同一 panel 分为两块原图时在 `assets` 中列出两块。非关键内容进备注/省略时分别用 `notes`/`omitted_with_reason` 并记录 `reason`。不要为了让脚本通过把未看过的 panel 标为已核验。

`deck.json` 格式如下。标题、条件、解释、补充说明、备注由模型根据论文写入，脚本不生成科学结论。

```json
{
  "slides":[{
    "id":"result-02", "kind":"result", "layout":"side",
    "title":"研究结果 2：完整的科学结论",
    "condition":"一行模型、干预和检测条件",
    "figures":["F2_A","F2_B"],
    "blocks":[
      {"head":"1｜A：实验设计","body":"具体比较和观察结果，说明其含义。"},
      {"head":"2｜B：独立验证","body":"解释为什么继续做、得到什么及证据贡献。"}
    ],
    "core":"这一页最重要的科学结论。",
    "supplement":"补充条件、差异或证据边界。",
    "notes":"目的、完整组别与样本量、统计、来源页/图注、解释边界及转场理由。"
  }]
}
```

- `layout: side`：左图右文；`wide`：上图下方 2–3 个解释模块。每个模块标题约一行，正文通常 40–70 中文字；检查实际排版，不机械按字数删科学内容。
- 默认按原比例自动排列图片。需保留配对时用 `groups: [["F2_A","F2_B"],["F2_C"]]` 指定各行；顺序按数据排列。
- 密集图可使用 `figures: [{"asset":"F2_A","box":[x,y,w,h]}]`；坐标单位英寸，原图仍等比 contain，脚本不裁数据。所有 figures 同时用 box 或同时用自动模式。
- 结果页可用图域：side `[.65,1.77,8.05,5.36]`；wide `[.65,1.72,14.70,3.50]`。避免向标题、解释或页脚侵占。
- `kind: concept` 使用相同解释/页脚，可用 `image` 引用概念图，或 `chain: [{"label":"阶段","detail":"证据类型"}]` 画可编辑流程；chain 使用 wide 布局。不要把所有概念页都变成相同卡片。
- 原生流程为 2–6 个简短节点；总结页可用 `diagram: evidence-grid` 和正好 4 个节点组成两行两列证据关系图。原生图必须 `kind: concept`、`layout: wide`，不与 image/figures 叠放。可运行例子见 `examples/deck.json`。
- 默认首页用 `kind: paper-cover`，填写 `id`、`title`、`image` 和 `notes`。`image` 指向从原 PDF 首页渲染/裁切并登记来源的截图（`kind: evidence`）；沿用裁图缓存与来源哈希，无需加入实验 panel 清单。截图等比放在 `[.65,.55,14.70,7.90]` 区域，`title` 仅用于目录/备注，不在截图上重复绘制。先看原页后确定截图区域，保证期刊、题目和作者完整清楚。
- 用户另选设计式封面时，`kind: cover` 使用 `title`、`subtitle`、`citation`、可选 `image`。已提供完整封面图片且要求不改可用 `kind: locked-image`、`image`、`locked: true`。已有可编辑封面使用原工程保留，不用截图替换。
- 自定义复杂概念图时复用脚本的文本/图像函数或原工程组件，不把整套重新写一遍。

## 构建和导出

```text
python SKILL/scripts/render_deck.py build --workspace WORK --pages 2,5,12
python SKILL/scripts/render_deck.py export --workspace WORK --soffice SOFFICE --input WORK/build/proof.pptx
python SKILL/scripts/render_deck.py raster --workspace WORK --pdf WORK/output/proof.pdf
```

这是内部样张检查，不要求用户审批；修好代表页后直接批量生成。`--soffice` 可省略，自动发现 LibreOffice，Windows 无 LibreOffice 时尝试已安装的 PowerPoint。LibreOffice 使用项目专属 profile；PowerPoint 在已经打开时停止，不接管用户演示文稿。需要手动路径时只配置实际存在的程序。

```text
python SKILL/scripts/render_deck.py build --workspace WORK
python SKILL/scripts/render_deck.py export --workspace WORK --soffice SOFFICE
python SKILL/scripts/render_deck.py raster --workspace WORK
python SKILL/scripts/audit.py --workspace WORK
```

完整文件为 `build/deck.pptx`、`output/deck.pdf`，备注同时写入 PPTX 与 `build/deck.notes.md`。带 `--pages` 的输出始终是 proof，不能当作完整交付。

一次运行上述四步可用 `python SKILL/scripts/run.py finish --workspace WORK`。随后运行 `python SKILL/scripts/verify_source_pixels.py --workspace WORK`，查看实际渲染并修正发现的问题。命令成功不代表视觉或科学审查已经通过。

宿主已有其他可靠导出方式时，先记录当前 PPTX 的 SHA256，再将该 PPTX 真正导出 PDF，然后运行：

```text
python SKILL/scripts/render_deck.py record-export --workspace WORK --pdf ACTUAL_EXPORTED.pdf --pptx-sha256 HASH_RECORDED_BEFORE_EXPORT
python SKILL/scripts/render_deck.py raster --workspace WORK
python SKILL/scripts/audit.py --workspace WORK
```

登记命令检查页数和 PPTX 是否变化，不证明 PDF 是由该 PPTX 导出的；调用方必须确保真实导出，不使用另行绘制的 PDF 或旧文件冒充。所有导出器缺失时保存 `pending_export` 检查点，交代 PPTX 已生成、PDF 和视觉检查未完成。

脚本不自动缩小字号；溢出时修改文字或布局，必要时在授权范围内调整分组。主要组别/轴仍看不清时继续修，不能只用高 DPI 宣称现场可读。

## 增量、锁定和真实检查

修改前：

```text
python SKILL/scripts/audit.py --workspace WORK --snapshot --mode layout
python SKILL/scripts/render_deck.py changes --workspace WORK
python SKILL/scripts/render_deck.py build --workspace WORK --pages changed
```

`layout` 锁页序、核心结论、模型条件、原图及保留页；`typography` 还锁解释和备注。只有用户授权改变锁定范围时才用 `--replace-snapshot`，不可为通过检查而刷新。

`changes` 对比主题、逐页数据和图像哈希。完整 build 更新机器构建基线；proof 不更新。全套导出后机器检查原图字节、页数、图文重叠、尺寸、PDF 文字完整和来源去向。

实际查看当前 PNG 后才运行：

```text
python SKILL/scripts/audit.py --workspace WORK --reviewed-pages all
```

局部修改可写 `--reviewed-pages 5-7`。未改页只有当前 PNG 哈希与上次已审 PNG 一致时才复用视觉检查；变化后自动失效。`NEEDS_VISUAL_REVIEW` 不是最终 PASS。自动检查不能确认图像真实性、科学推断或物理会场投影效果。

标准文献汇报不需要外部技能。复杂动画、嵌入媒体或未支持的特殊 Office 对象属于额外能力；用户确实要求时再选择工具，不把这些工具作为普通制作的隐藏依赖。

检查点：

```text
python SKILL/scripts/project.py checkpoint --workspace WORK --phase layout --completed source_cached,science,assets --pending dense_page_review,export --next "检查结果页12，然后完整导出"
```

交付前记录准确待办与输出状态，避免中断后重复生成或把 proof 误当成 final。
