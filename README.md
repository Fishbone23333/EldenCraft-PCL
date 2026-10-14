# EldenCraft PCL 适配版

在艾尔登法环里使用 Minecraft 人物、物品栏、方块和战斗系统，通过 **PCL 2** 启动 Minecraft。

当前桥接版本 **`0.25.5-pcl.4`**，基于 [SocketByte/EldenCraft v0.25.5](https://github.com/SocketByte/EldenCraft/releases/tag/v0.25.5)，包含配套 MC Mod 和修订的原生核心 DLL，保留上游 loader 与画面合成组件。这是社区适配版本。

## 改进内容

| 功能 | 行为 |
| --- | --- |
| PCL 启动 | 创建独立 MC 实例；在 PCL 点击启动后，脚本等待桥接就绪，再启动法环 |
| 免费体力 | MC 桥接攻击、射击和格挡不消耗体力，隐藏体力条 |
| 卡顿优化 | 临时状态改为后台写入，合并过期状态，缓存物品属性，减少游戏线程重复工作 |
| 滚轮切换 | 逐帧采集滚轮，合并最终物品栏位置，避免事件丢失和切换积压 |
| 短拉弓 | 拉弓至少 1 个游戏 tick（约 0.05 秒）即可发射低威力箭；满拉保持正常威力 |
| 盾牌反馈 | 确认格挡后播放 MC 格挡音效、盾牌受击回弹，抑制本地法环受伤语音；未挡住的伤害照常反馈 |
| 创造飞行 | 修正飞行横向输入的坐标方向，A/D 与画面左右一致 |
| R 拾取 | 普通拾取和关闭拾取提示跳过额外的移动等待；开门、进雾等仍保留原生动作处理 |
| 敌人血条 | 取消 MC 自绘头顶血条，普通敌人使用法环原生血条并匹配第一人称镜头；现有 BOSS 血条保持不变 |
| 人物切换 | 法环窗口前台按 F8 切换 Steve / 原生法环人物，F6 为原生备用键 |
| 多角色存档 | 为不同法环角色选择独立 MC 世界，保留各自物品、经验和进度；绑定不匹配时显示可读的提示 |

F8 切到原生法环人物后，体力仍遵循原版规则。切换的是当前角色的控制/显示模式，使用独立 `EldenCraft.sl2`，不会加载原版存档中的其他角色。

## 第一步：准备哪些版本

系统要求：**Windows 10（内部版本 19041 或以上）或 Windows 11，64 位**。两款游戏会同时运行；首次安装和下载资源需要联网，游玩桥接使用离线单人模式。

### 需要下载或准备的 5 项（含 Minecraft 版本）

**我的世界使用 Minecraft Java Edition `26.3`，搭配 Fabric Loader `0.19.5`。** 运行下面的安装步骤时，脚本会自动下载这个版本；你只需在启动时选择 **`EldenCraft-26.3-Fabric-0.19.5`** 实例。

| 项目 | 使用版本 / 文件 | 下载入口 | 下载后怎么处理 |
| --- | --- | --- | --- |
| 本仓库 | `main` 分支，包含 **`0.25.5-pcl.4`** 优化 JAR | [直接下载 EldenCraft-PCL-main.zip](https://github.com/Fishbone23333/EldenCraft-PCL/archive/refs/heads/main.zip) | 完整解压，例如放到 `D:\Games\EldenCraft-PCL-main` |
| 艾尔登法环 | **Steam Windows 版**；当前适配的 `eldenring.exe` **产品版本为 `2.7.1.0`** | [Steam 商店](https://store.steampowered.com/app/1245620/ELDEN_RING/) | 在 Steam 安装游戏，记住 `Game\eldenring.exe` 的路径 |
| PCL 启动器 | 本机验证版本 **`2.13.1.1`**，推荐使用相同版本 | [PCL 官方下载入口](https://meloong.com/pcl) | 放在独立目录，例如 `D:\PCL`；脚本要求文件名为 `Plain Craft Launcher 2.exe` |
| 我的世界 | **Minecraft Java Edition `26.3` + Fabric Loader `0.19.5`** | 运行本仓库的 `SETUP-EldenCraft-PCL.cmd`，由脚本从 Mojang / Fabric 自动下载 | 安装后在 PCL 选择 **`EldenCraft-26.3-Fabric-0.19.5`**；无需自己在 PCL 下载页另装，也不能用基岩版或 Java `1.21.1` 替代 |
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
| MC 桥接 Mod | **`eldencraft-bridge-0.25.5-pcl.4.jar`** | 本仓库已经包含，脚本校验后安装 |
| 修订的原生核心 | **`pcl.4` 的 `eldencraft_core.dll`** | 本仓库已包含，安装器备份并替换核心；loader 与 compositor 保留上游版本 |

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
├─ SELECT-EldenCraft-WORLD.cmd    新角色 / 切换 MC 世界
└─ trials\pcl-adapter\
   ├─ local.example.json
   └─ patches\eldencraft-bridge-0.25.5-pcl.4.jar
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
   ├─ eldencraft-bridge-0.25.5-pcl.4.jar
   └─ fabric-api-0.161.0+26.3.jar
```

如果自动下载上游发布包失败，可以手动下载固定的 [EldenCraft-0.25.5-windows-x64.zip](https://github.com/SocketByte/EldenCraft/releases/download/v0.25.5/EldenCraft-0.25.5-windows-x64.zip)，解压到 `trials\EldenCraft-0.25.5` 后重跑安装。该目录下应直接看到 `release-manifest.json` 和 `payload`，不要再多套一层同名文件夹。其他依赖仍由脚本自动下载。

## 第三步：每次怎么启动

**每次按下面的顺序启动，首次安装完成后也一样。不要先手动打开两款游戏。**

1. **登录 Steam。** 等 Steam 登录完成；保持 Steam 运行，关闭现有 Minecraft、法环和 PCL 窗口。
2. **双击本仓库根目录的 `START-EldenCraft-PCL.cmd`。** 脚本检查组件、备份存档，并打开 PCL。保持脚本窗口打开。
3. **在 PCL 确认选中的版本是 `EldenCraft-26.3-Fabric-0.19.5`，然后点击“启动游戏”。** 如果没有自动选中，在 PCL 的版本选择里选择它。无需再下载一个同名 MC 版本。
4. **等待 MC 和法环启动。** MC 会自动创建或进入专用世界；脚本检测到桥接加载后，会自动启动法环。MC 首次加载、Steam 冷启动可能需要等待。
5. **在自动打开的法环窗口中进入游戏。** 载入独立 `EldenCraft.sl2` 中与当前 MC 世界对应的角色；第一次游玩可以创建新角色。已有角色后再开新角色，请先按下面“新角色与 MC 世界”的步骤选择独立世界。进入世界后保持法环窗口在前台，使用桥接游玩。

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

### 新角色与 MC 世界：出现“角色与存档不匹配”怎么办

**一个 MC 世界绑定一个法环角色。** 在法环中创建新角色不会自动创建新的 MC 世界。旧世界仍保存旧角色的物品、经验、建造和奖励记录，所以桥接会暂停连接，避免把这些数据混给新角色。游戏中的简短提示下方说明可按 **T** 打开 MC 聊天记录阅读；中文界面会显示中文说明。

要继续玩旧角色：在法环载入原来的角色，并选择它原来使用的 MC 世界。原先默认世界的编号为 **`default`**。

要玩新角色，请按以下步骤操作：

1. **分别保存并退出 MC、法环和 PCL。** 不要在游戏运行时更换世界。
2. **双击 `SELECT-EldenCraft-WORLD.cmd`。** 输入 **`0`**，再输入一个新编号，例如 **`new-character`** 或 **`role2`**。编号使用 1–40 个英文字母、数字、`-`、`_`，以字母或数字开头。大小写统一为小写。
3. 脚本会记住编号并打开 PCL。在 PCL 启动 **`EldenCraft-26.3-Fabric-0.19.5`**，MC 会创建新的独立世界；已存在的编号会打开对应世界。
4. 法环自动启动后，**载入你刚创建的新角色**。第一次连接会绑定这个新 MC 世界。
5. 以后继续玩同一角色时，直接用 `START-EldenCraft-PCL.cmd`。它会记住上次选择的编号；换回旧角色时，再运行 `SELECT-EldenCraft-WORLD.cmd` 并选择 **`default`** 或旧角色对应的编号。

`SELECT` 同时完成世界选择和正常启动，无需再运行一次 `START`。选择器更改的是 MC 世界编号，法环角色仍需你在法环菜单中选择。旧世界会完整保留，不会清空背包、移除绑定或删除存档。

| 编号 | MC 存档目录（专用实例的 `saves` 下） |
| --- | --- |
| `default` | `EldenCraft`；只有旧版世界时继续使用 `EldenCraft Passthrough Lab` |
| `new-character` | `EldenCraft - new-character` |
| `role2` | `EldenCraft - role2` |

选择记录保存在 **`data_root/world-profile.json`**。如果刚换了世界，务必载入与它对应的法环角色。继续开第三个角色时再用新的编号，不要重复使用已经绑定的编号。

也可以从仓库根目录运行（会记住选择）：

```powershell
.\START-EldenCraft-PCL.cmd -WorldProfile new-character
.\START-EldenCraft-PCL.cmd -WorldProfile default
```

CPU 模式用 `START-EldenCraft-PCL-CPU.cmd -SelectWorld` 打开相同选择菜单。`-HostOnly` 无法更换已打开的 MC 世界。

### 检查文件和补启动法环

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

`pcl.4` 已取消 MC 自绘头顶血条，安装器将旧配置的 `hud.enemyBar.enabled` 设为 `false`，即使手动改回 `true` 也不会注册旧绘制器。BOSS 血条继续使用原有 `hud.bossBar` 设置。

普通敌人由法环原生 HUD 绘制：MC 命中会进入原生受伤血条登记，投影使用桥接第一人称镜头。显示时间、位置裁剪和最多 8 个普通敌人槽位仍由法环处理，属于受伤后短时显示，不是所有怪物永久显示。测试时确认法环设置中 HUD 显示已开启，然后在视野内攻击普通敌人；BOSS 沿用原有血条。

## 存档、更新和回退

- 法环由 me3 以离线模式、独立 **`EldenCraft.sl2`** 启动。
- MC 使用独立实例和世界，安装器拒绝修改未标记的同名实例。
- 启动前备份法环存档、专用 MC 世界和战役数据，位于 `data_root/backups`。
- 更换 JAR 时旧版移到 `pcl-optimization-*` 备份目录，首次清零体力前也会备份配置。
- 更换核心 DLL 前先验证仓库清单，再将旧 DLL 复制到 `pcl-native-*`；不会修改下载的上游发布包。
- 更新后关闭两款游戏，重新运行安装入口；不要同时放入多个 `eldencraft-bridge*.jar`。
- 回退时关闭游戏，恢复同一版本的 JAR、核心 DLL、`patches/manifest.json` 和配置；建议直接恢复完整旧版仓库后重新安装。

## 源码和构建

```text
minecraft/                 MC 桥接源码、Gradle 和回归检查
native/                    原生桥接源码及格挡、拾取、血条修订
compositor/                上游画面合成源码
config/campaign-pcl.json   优化配置样例与回归检查输入
trials/pcl-adapter/        PCL 安装、路径配置、启动和 F8 程序
trials/pcl-adapter/patches/ 已编译 pcl.4 JAR、核心 DLL 与 SHA256 清单
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
powershell -NoProfile -ExecutionPolicy Bypass -File test-world-profiles.ps1
```

原生构建见 [native/README.md](native/README.md)。PCL 安装器使用仓库内已校验的 `eldencraft_core.dll`；loader、compositor 和其它依赖来自上游发布包。自行构建核心后也需更新 `patches/manifest.json` 的 `nativeCore.sha256`。

## 验证范围与排错

`pcl.4` 运行完整 Gradle 构建与自动回归检查、原生 Rust 检查（492 项），以及 Python 安装完整性、F8、世界选择与存档隔离检查。自动检查覆盖飞行方向、格挡钩子、拾取分类、语音抑制范围和安装校验。**本次没有启动游戏；盾牌声音与动作、拾取时移动和第一人称原生血条画面由使用者实测。** CPU 回退和全新电脑整套安装也仍待实机确认。

- MC 日志：`pcl_root/.minecraft/versions/EldenCraft-26.3-Fabric-0.19.5/logs/latest.log`。
- 启动/loader 日志：`data_root/logs`；原生运行数据与日志：`data_root/runtime/data`。
- EXE 校验失败：确认法环版本符合要求，参照上游兼容说明，不要跳过哈希检查。
- 普通敌人血条不显示：确认已安装配套 `pcl.4` JAR 与核心 DLL、法环 HUD 显示开启，在视野内攻击普通敌人；不要启用旧 `enemyBar`。检查原生日志的 `Native enemy gauges` 或相关错误。
- 不能连接：确认仅运行一个桥接实例，两端传输模式一致，并从专用入口启动 PCL。

## 来源与许可证

上游源码基准：[`0ed8381cb19b46e7f89965deeb3ed9d04a70a58f`](https://github.com/SocketByte/EldenCraft/commit/0ed8381cb19b46e7f89965deeb3ed9d04a70a58f)。感谢 [SocketByte/EldenCraft](https://github.com/SocketByte/EldenCraft)、PCL、Fabric、me3 和 ReShade。

遵循上游 **MIT License**，保留 [LICENSE](LICENSE) 和 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。仓库包含源码、适配脚本、桥接 JAR 和核心 DLL；游戏文件、上游原生发布包和外部依赖通过安装器从原始来源获取。
