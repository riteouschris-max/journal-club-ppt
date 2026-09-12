# 独立能力清单

用户在已有多技能环境中完成 PPT 后，希望同一个 skill 可以在其他设备独立复用。本清单用于说明实现位置，不要求执行时加载原 skill。

| 原流程中涉及的能力 | 本仓库的独立实现 |
|---|---|
| nature-paper2ppt 的论文类型、论证顺序、实验衔接 | paper-to-deck.md 的论文类型与证据链规则 |
| nature-shared 的术语统一思路 | 本项目 terminology.json 约定，首次全称、规范词与来源记录 |
| 原图 panel、图例、轴、标尺的完整性 | project.py 来源裁图、figure_inventory.json、科学阅读与视觉检查 |
| presentation-skill 的运行环境隔离与检测思路 | setup.py、requirements.txt、check_environment.py、run.py，独立实现，不调用原脚本 |
| 原生 PPT 对象、图文布局、主题、溢出修复 | render_deck.py、assets/theme.json、visual-standard.md |
| 成稿中新增的四块证据总结布局 | concept + wide + evidence-grid，已纳入渲染器和示例 |
| 来源真实性与修改锁定 | audit.py、verify_source_pixels.py、manifest、locks.json |
| PDF 导出、渲染预览与最终检查 | LibreOffice 适配、Windows PowerPoint 适配、raster、audit |
| 继续任务、省去重复解析和制图 | project.py 缓存、state.json、逐页哈希与 changes |
| 概念插图的设计方法 | visual-standard.md 的图像提示骨架与原生图备用布局 |

这次核对发现，原来的三类脚本已能覆盖多数结果页工作；缺口集中在安装、字体/导出发现、实际成稿新增的总结布局和新用户示例。现已把相关通用能力直接放入本包。它没有依赖其他 skill 的 import、目录路径或隐含的辅助文档。

没有复制外部技能的整套源代码或参考库；论文组织、运行环境和检查的通用做法在本仓库按当前目标整理实现。颜色、字号和图文结构遵循此项目用户已经定稿的要求，不能让另一套技能的通用小字号或封面规则覆盖它。

无法封装进 skill 的部分：基础模型及其图文理解、宿主工具权限、图像生成服务、商业 Office 授权和系统字体许可。它们是运行条件，不是其他 skill 的隐藏能力。安装/检测可以识别本机程序与字体，但不能替用户取得这些服务权限。

“一条指令使用”的验收含义：在具备图文与命令工具的宿主中，用本包建立独立依赖环境，完成论文阅读和逐页设计，构建 PPTX，真实导出 PDF，核查源图并查看渲染后交付。纯本地脚本样例通过只证明安装与模板链路，不能替代对一篇新论文的科学阅读验收。
