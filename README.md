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

## 环境要求

- Windows 10（19041 或以上）/ Windows 11，64 位。
- Steam 艾尔登法环 **2.7.1.0**；启动前登录 Steam，安装器会校验游戏 EXE。
- PCL 2，包含 `Plain Craft Launcher 2.exe`；本机使用 **2.13.1.1**。
- Python **3.12 或以上**，用于首次安装；常规游玩无需 Python 常驻。
- 首次安装需要网络。MC **26.3**、Fabric Loader **0.19.5**、Fabric API **0.161.0+26.3**、Java **25** 由安装器下载到专用目录。

两款游戏同时运行，性能取决于硬件和游戏设置。桥接支持离线单人；Minecraft 账号使用自己的 PCL 配置。

## 安装

1. 下载仓库 ZIP 并解压，或运行：

   ```powershell
   git clone https://github.com/Fishbone23333/EldenCraft-PCL.git
   cd EldenCraft-PCL
   ```

2. 复制 `trials/pcl-adapter/local.example.json` 为 `trials/pcl-adapter/local.json`，填写 PCL 路径。`game_path` 留空时从 Steam 安装记录查找法环，也可填写绝对路径：

   ```json
   {
     "pcl_root": "D:/PCL",
     "game_path": "D:/SteamLibrary/steamapps/common/ELDEN RING/Game/eldenring.exe",
     "release_root": "trials/EldenCraft-0.25.5",
     "data_root": "trials/EldenCraftData"
   }
   ```

   相对路径以仓库根目录为基准。`local.json` 仅保存在本机。PCL 文件名不同的情况下，需同步调整 `start-pcl.ps1` 和 `setup-pcl.ps1` 中的可执行文件名。

3. 关闭两款游戏和 PCL，双击 **`SETUP-EldenCraft-PCL.cmd`**。

   安装器下载并校验上游发布包、Java、me3 和 ReShade，再安装 Minecraft 专用实例和本仓库的优化 JAR。不会启动游戏；原生运行组件位于 `data_root/runtime`，法环安装目录保持原样。

   Python 不在 PATH 中时：

   ```powershell
   .\SETUP-EldenCraft-PCL.cmd -PythonCommand "C:\Python312\python.exe"
   ```

   也可提前将完整的上游 [Windows 发布包](https://github.com/SocketByte/EldenCraft/releases/download/v0.25.5/EldenCraft-0.25.5-windows-x64.zip) 解压到 `release_root`，该目录应直接包含 `release-manifest.json` 和 `payload`。安装器仍会验证文件。

## 启动和操作

1. 关闭现有 Minecraft、法环和 PCL，登录 Steam。
2. 双击 **`START-EldenCraft-PCL.cmd`**，脚本打开 PCL 并选择 `EldenCraft-26.3-Fabric-0.19.5`。
3. 在 PCL 点击“启动游戏”，保持脚本窗口打开。MC 自动进入专用世界，桥接加载后脚本启动法环。
4. 在法环中载入或创建角色，开始游玩。

**无需先手动启动两款游戏。** 从专用入口打开 PCL，Minecraft 才能继承桥接环境变量。

| 按键 | 操作 |
| --- | --- |
| 左键 / 右键 | 攻击、挖掘 / 使用、放置 |
| 滚轮 | 切换物品栏 |
| E / R | 背包 / 法环交互 |
| F5 | 第一 / 第三人称视角 |
| Y | 灵马 |
| F8 | Steve / 原生法环人物切换，需法环窗口在前台 |
| F6 | 人物切换备用键 |

GPU 画面异常时退出两款游戏和 PCL，改用 **`START-EldenCraft-PCL-CPU.cmd`**。两端须使用同一种传输模式。

只校验配置和文件、不启动游戏：

```powershell
.\START-EldenCraft-PCL.cmd -Mode check
```

Steam 尚未就绪导致法环启动失败时，可以保持专用 MC 世界打开，登录 Steam 后执行：

```powershell
.\START-EldenCraft-PCL.cmd -HostOnly
```

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
