# EldenCraft PCL 适配版

在艾尔登法环里使用 Minecraft 人物、物品栏、方块和战斗系统，通过 **PCL 2** 启动 Minecraft。

当前桥接版本 **`0.25.5-pcl.2`**，基于 [SocketByte/EldenCraft v0.25.5](https://github.com/SocketByte/EldenCraft/releases/tag/v0.25.5)，保留上游原生 DLL，增加 PCL 安装/启动入口和 Minecraft 端优化。这是社区适配版本。

## 改进内容

| 功能 | 行为 |
| --- | --- |
| PCL 启动 | 创建独立 MC 实例；在 PCL 点击启动后，脚本等待桥接就绪，再启动法环 |
| 免费体力 | MC 桥接攻击、射击和格挡不消耗体力，隐藏体力条 |
| 卡顿优化 | 临时状态改为后台写入，合并过期状态，缓存物品属性，减少游戏线程重复工作 |
| 滚轮切换 | 逐帧采集滚轮，合并最终物品栏位置，避免事件丢失和切换积压 |
| 短拉弓 | 拉弓至少 1 个游戏 tick（约 0.05 秒）即可发射低威力箭；满拉保持正常威力 |
| 头顶血条 | 普通敌人和 BOSS 显示头顶血条、血量数字和受伤尾段；保留顶部 BOSS 血条 |
| 人物切换 | 法环窗口前台按 F8 切换 Steve / 原生法环人物，F6 为原生备用键 |

F8 切到原生法环人物后，体力仍遵循原版规则。切换的是当前角色的控制/显示模式，使用独立 `EldenCraft.sl2`，不会加载原版存档中的其他角色。

## 第一步：准备哪些版本

系统要求：**Windows 10（内部版本 19041 或以上）或 Windows 11，64 位**。两款游戏会同时运行；首次安装和下载资源需要联网，游玩桥接使用离线单人模式。

### 需要自己下载或准备的 4 项

| 项目 | 使用版本 / 文件 | 下载入口 | 下载后怎么处理 |
| --- | --- | --- | --- |
| 本仓库 | `main` 分支，包含 **`0.25.5-pcl.2`** 优化 JAR | [直接下载 EldenCraft-PCL-main.zip](https://github.com/Fishbone23333/EldenCraft-PCL/archive/refs/heads/main.zip) | 完整解压，例如放到 `D:\Games\EldenCraft-PCL-main` |
| 艾尔登法环 | **Steam Windows 版**；当前适配的 `eldenring.exe` **产品版本为 `2.7.1.0`** | [Steam 商店](https://store.steampowered.com/app/1245620/ELDEN_RING/) | 在 Steam 安装游戏，记住 `Game\eldenring.exe` 的路径 |
| PCL 启动器 | 本机验证版本 **`2.13.1.1`**，推荐使用相同版本 | [PCL 官方下载入口](https://meloong.com/pcl) | 放在独立目录，例如 `D:\PCL`；脚本要求文件名为 `Plain Craft Launcher 2.exe` |
| Python | 推荐 **`3.12.10`，Windows 64 位**；脚本最低支持 3.12 | [Python 3.12.10 64 位安装器](https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe) | 安装时勾选 **Add python.exe to PATH**，然后点击 Install Now |

**版本核对：**法环的 `2.7.1.0` 是 Windows 文件“属性 → 详细信息 → 产品版本”，不是要求标题画面显示相同数字。脚本还会验证 EXE 的 SHA256；其他法环版本不能直接套用。PCL 官网会更新版本，如果下载的是其他版本，本文的启动流程仍以 `2.13.1.1` 为验证基准，其他版本尚未逐一验证。

Python 已安装且为 3.12 或以上时可继续使用。下载的 PCL 程序如果叫 `PCL2.exe` 等其他名称，请将它重命名为 **`Plain Craft Launcher 2.exe`**，或自行修改两份脚本中的程序名。

### 安装脚本会自动下载的组件

下面这些组件**不需要在 PCL 的“下载”页手动安装**，也不需要逐个寻找 JAR 或 DLL：

| 组件 | 固定版本 | 安装方式 |
| --- | --- | --- |
| 上游 EldenCraft 原生组件 | **`v0.25.5`**，文件 `EldenCraft-0.25.5-windows-x64.zip` | 脚本从上游 GitHub 下载并解压 |
| Minecraft Java Edition | **`26.3`** | 脚本从 Mojang 下载游戏、库和资源 |
| Fabric Loader | **`0.19.5`** | 脚本从 Fabric 获取启动配置 |
| Fabric API | **`0.161.0+26.3`** | 脚本下载并放入专用实例的 `mods` |
| Java 运行时 | **Temurin JRE `25.0.4.1+1`，Windows x64** | 脚本下载并复制到专用实例的 `java` |
| me3 | **`0.13.0`** | 脚本下载，用于离线启动法环 |
| ReShade | **`6.8.0 Addon`** | 脚本下载并准备画面合成运行组件 |
| MC 桥接 Mod | **`eldencraft-bridge-0.25.5-pcl.2.jar`** | 本仓库已经包含，脚本校验后安装 |

最终使用的 MC 实例名称是 **`EldenCraft-26.3-Fabric-0.19.5`**。`1.21.1` 等其他 MC 版本不能替代这个实例；本教程使用 PCL 启动，无需另外安装 Prism。

## 第二步：首次安装

### 1. 解压到本地文件夹

完整解压 `EldenCraft-PCL-main.zip`，进入能看到下面文件的目录。不要在 ZIP 内直接双击脚本：

```text
D:\Games\EldenCraft-PCL-main\
├─ README.md
├─ SETUP-EldenCraft-PCL.cmd       首次安装 / 更新
├─ START-EldenCraft-PCL.cmd       日常启动，默认 GPU 模式
├─ START-EldenCraft-PCL-CPU.cmd   GPU 画面异常时使用
└─ trials\pcl-adapter\
   ├─ local.example.json
   └─ patches\eldencraft-bridge-0.25.5-pcl.2.jar
```

PCL 程序放在另一个目录，例如 `D:\PCL\Plain Craft Launcher 2.exe`。可以先打开 PCL，设置平时使用的 Minecraft 账号，设置完成后关闭 PCL。

### 2. 填写 PCL 和法环路径

打开 `trials\pcl-adapter`，复制一份 `local.example.json`，将副本命名为 **`local.json`**，用记事本编辑。打开资源管理器的“文件扩展名”显示，确认不是 `local.json.txt`。

例如 PCL 位于 `D:\PCL`、法环位于 `D:\SteamLibrary` 时：

```json
{
  "pcl_root": "D:/PCL",
  "game_path": "D:/SteamLibrary/steamapps/common/ELDEN RING/Game/eldenring.exe",
  "release_root": "trials/EldenCraft-0.25.5",
  "data_root": "trials/EldenCraftData"
}
```

| 配置项 | 填写方法 |
| --- | --- |
| `pcl_root` | **PCL 程序所在文件夹**，不要填写 EXE 文件，也不要填写 `.minecraft` 目录 |
| `game_path` | **`eldenring.exe` 的完整文件路径**；可在 Steam → 游戏属性 → 已安装文件 → 浏览中找到 `Game` 文件夹。留空 `""` 则由脚本从 Steam 安装记录查找 |
| `release_root` | 保持示例值，下载的上游发布包放在这里 |
| `data_root` | 保持示例值，运行配置、组件、日志和备份放在这里 |

示例路径中的盘符和目录要换成自己的。JSON 中建议使用 `/`；如用 `\`，需写成 `\\`。后两个相对路径以本仓库根目录为基准。

### 3. 运行安装入口

关闭 Minecraft、法环和 PCL，在仓库根目录双击 **`SETUP-EldenCraft-PCL.cmd`**。保持窗口打开，等待所有下载和校验完成；首次需要下载大量 MC 资源，耗时取决于网络。

看到下面这行才表示安装完成：

```text
Setup complete. Run START-EldenCraft-PCL.cmd, then click Launch in PCL.
```

安装过程中不会自动开始游玩。若窗口报错，先处理错误再重跑安装脚本；已下载且校验正确的文件会复用。

如果提示找不到 `python`，打开仓库目录的终端，用 Python 的实际路径运行，例如：

```powershell
.\SETUP-EldenCraft-PCL.cmd -PythonCommand "C:\Python312\python.exe"
```

安装成功后，PCL 游戏目录中应出现：

```text
D:\PCL\.minecraft\versions\EldenCraft-26.3-Fabric-0.19.5\
├─ EldenCraft-26.3-Fabric-0.19.5.json
├─ java\bin\javaw.exe
└─ mods\
   ├─ eldencraft-bridge-0.25.5-pcl.2.jar
   └─ fabric-api-0.161.0+26.3.jar
```

如果自动下载上游发布包失败，可以手动下载固定的 [EldenCraft-0.25.5-windows-x64.zip](https://github.com/SocketByte/EldenCraft/releases/download/v0.25.5/EldenCraft-0.25.5-windows-x64.zip)，解压到 `trials\EldenCraft-0.25.5` 后重跑安装。该目录下应直接看到 `release-manifest.json` 和 `payload`，不要再多套一层同名文件夹。其他依赖仍由脚本自动下载。

## 第三步：每次怎么启动

**每次按下面的顺序启动，首次安装完成后也一样。不要先手动打开两款游戏。**

1. **登录 Steam。** 等 Steam 登录完成；保持 Steam 运行，关闭现有 Minecraft、法环和 PCL 窗口。
2. **双击本仓库根目录的 `START-EldenCraft-PCL.cmd`。** 脚本检查组件、备份存档，并打开 PCL。保持脚本窗口打开。
3. **在 PCL 确认选中的版本是 `EldenCraft-26.3-Fabric-0.19.5`，然后点击“启动游戏”。** 如果没有自动选中，在 PCL 的版本选择里选择它。无需再下载一个同名 MC 版本。
4. **等待 MC 和法环启动。** MC 会自动创建或进入专用世界；脚本检测到桥接加载后，会自动启动法环。MC 首次加载、Steam 冷启动可能需要等待。
5. **在自动打开的法环窗口中进入游戏。** 载入独立 `EldenCraft.sl2` 中的角色，或首次创建新角色。进入世界后保持法环窗口在前台，使用桥接游玩。

完整顺序为：**Steam 登录 → 双击 START → PCL 点击启动 → MC 加载 → 法环自动打开 → 载入/创建角色**。

默认使用独立存档，你原版 `ER0000.sl2` 中的角色不会自动出现在这里。常规游玩使用 **`START`** 入口，**`SETUP`** 仅用于安装、补齐组件或更新；不要直接运行上游的 `EldenCraft.cmd`，它走的是上游启动流程。

如果 PCL 提示 Java 不兼容，在该版本的设置中选择安装器提供的 **Java 25**，路径为：

```text
<PCL目录>\.minecraft\versions\EldenCraft-26.3-Fabric-0.19.5\java\bin\javaw.exe
```

如果 GPU 模式画面异常，退出两款游戏和 PCL，重新双击 **`START-EldenCraft-PCL-CPU.cmd`**，其余步骤相同。结束游玩时先分别保存退出两款游戏，再关闭启动脚本窗口。

## 游戏按键

| 按键 | 操作 |
| --- | --- |
| 左键 / 右键 | 攻击、挖掘 / 使用、放置 |
| 滚轮 | 切换物品栏 |
| E / R | 背包 / 法环交互 |
| F5 | 第一 / 第三人称视角 |
| Y | 灵马 |
| F8 | Steve / 原生法环人物切换，需法环窗口在前台 |
| F6 | 人物切换备用键 |

## 启动排错命令

只校验配置和文件、不启动游戏：

```powershell
.\START-EldenCraft-PCL.cmd -Mode check
```

如果 MC 已启动但 Steam 尚未就绪导致法环退出，可以保持专用 MC 世界打开，关闭残留法环进程，登录 Steam 后从仓库根目录的终端执行：

```powershell
.\START-EldenCraft-PCL.cmd -HostOnly
```

`-HostOnly` 只补启动法环。使用 CPU 传输模式时，应运行 `START-EldenCraft-PCL-CPU.cmd -HostOnly`，保证两端模式一致。

## 血条与配置

运行配置位于 `data_root/campaign.json`，修改后重启两款游戏。不要修改上游发布包内的模板，否则完整性检查会失败。

头顶血条设置位于 `hud.enemyBar`：

```json
{
  "enabled": true,
  "width": 88,
  "height": 7,
  "headOffset": 0.35,
  "maxDistance": 32,
  "showNumbers": true
}
```

宽高为 Minecraft GUI 像素；`headOffset` 为目标碰撞体顶部上方的偏移量，单位米。无精确头骨坐标时以碰撞体顶部作为头顶。颜色复用 `hud.bossBar`。

显示范围还受上游原生发布限制：附近约 **16 米**、最多 **16 个目标**。巨大 BOSS 以身体边界判断距离；头顶超出视野时查看顶部 BOSS 血条。死亡、被原生遮挡、离开画面、菜单打开或桥接断开时隐藏。

## 存档、更新和回退

- 法环由 me3 以离线模式、独立 **`EldenCraft.sl2`** 启动。
- MC 使用独立实例和世界，安装器拒绝修改未标记的同名实例。
- 启动前备份法环存档、专用 MC 世界和战役数据，位于 `data_root/backups`。
- 更换 JAR 时旧版移到 `pcl-optimization-*` 备份目录，首次清零体力前也会备份配置。
- 更新后关闭两款游戏，重新运行安装入口；不要同时放入多个 `eldencraft-bridge*.jar`。
- 回退时关闭游戏，用备份 JAR 替换当前 JAR，并恢复匹配的 `patches/manifest.json` 和配置。

## 源码和构建

```text
minecraft/                 MC 桥接源码、Gradle 和回归检查
native/                    上游原生桥接源码
compositor/                上游画面合成源码
config/campaign-pcl.json   优化配置样例与回归检查输入
trials/pcl-adapter/        PCL 安装、路径配置、启动和 F8 程序
trials/pcl-adapter/patches/ 已编译 pcl.2 JAR 与 SHA256 清单
README.upstream.md         原始上游说明
```

构建 MC 桥接需要 **JDK 25**：

```powershell
cd minecraft
.\gradlew.bat build
```

输出位于 `minecraft/build/libs`。修改源码后将新 JAR 放入 `trials/pcl-adapter/patches`，更新清单的文件名、版本和 SHA256，再重新安装。

PCL 脚本检查：

```powershell
cd trials/pcl-adapter
python -m unittest test_install_pcl test_optimized_bridge test_pcl_paths
powershell -NoProfile -ExecutionPolicy Bypass -File test-character-switch.ps1
```

原生构建见 [native/README.md](native/README.md)，PCL 安装直接使用上游发布包的原生组件。

## 验证范围与排错

本地 `pcl.2` 完整 Gradle 构建通过：血条检查 **173 项**，PCL 优化检查 **7064 项**，覆盖镜头、分辨率、遮挡、死亡、过期数据、免费体力、短拉弓和滚轮。安装完整性检查和 Minecraft/Fabric 初始化检查通过。**实际游玩、血条画面和卡顿改善幅度由使用者测试**；CPU 回退也待实机确认。便携安装入口的脚本和路径逻辑已检查，尚未在全新电脑完成整套安装。

- MC 日志：`pcl_root/.minecraft/versions/EldenCraft-26.3-Fabric-0.19.5/logs/latest.log`。
- 启动/loader 日志：`data_root/logs`；原生运行数据与日志：`data_root/runtime/data`。
- EXE 校验失败：确认法环版本符合要求，参照上游兼容说明，不要跳过哈希检查。
- 血条不显示：确认使用 MC 桥接模式、`hud.enemyBar.enabled` 为 true，在近距离无遮挡视野内观察。
- 不能连接：确认仅运行一个桥接实例，两端传输模式一致，并从专用入口启动 PCL。

## 来源与许可证

上游源码基准：[`0ed8381cb19b46e7f89965deeb3ed9d04a70a58f`](https://github.com/SocketByte/EldenCraft/commit/0ed8381cb19b46e7f89965deeb3ed9d04a70a58f)。感谢 [SocketByte/EldenCraft](https://github.com/SocketByte/EldenCraft)、PCL、Fabric、me3 和 ReShade。

遵循上游 **MIT License**，保留 [LICENSE](LICENSE) 和 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。仓库包含源码、适配脚本和桥接 JAR；游戏文件、上游原生发布包和外部依赖通过安装器从原始来源获取。
