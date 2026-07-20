# PQ-AI 上位机代理

该代理只使用 Node.js 内置模块，构建后是单个 Windows x64 `.exe`。目标上位机无需安装 Node.js、Python、Java、Electron 或其他运行时，也不会联网下载依赖。

## 运行边界

- 云端 `PREPARE_RELEASE` 只把完整刷子表写入本地暂存目录，不调用机器人或上位机接口。
- 现场人员必须打开 `http://127.0.0.1:19090` 并确认或拒绝发布单；未确认时云端不能继续提交，拒绝后该发布单终止。
- `SIMULATOR` 只更新本机模拟文件，适合联调，不影响生产。
- `FILE_DROP` 只原子写入工厂/Dürr 认可的导入目录；只有上位机完成导入并产生一致回读时才算成功。
- `DURR_APPROVED_ADAPTER` 只调用工厂批准、已签名的适配器程序，不直接使用未公开机器人协议。
- 通信固定使用双向 TLS，拒绝匿名 TCP、明文 TCP 和未受信任证书。

## 离线构建

在隔离的 Windows 构建机离线准备 Node.js 25.5 或更高版本，然后执行：

```powershell
.\build-windows.ps1 -NodePath "D:\approved-tools\node.exe"
```

构建脚本不访问互联网。完成后，对 `dist\pq-upper-agent.exe` 做公司签名、病毒扫描和哈希登记，再将以下文件通过批准的离线介质送入上位机：

- `pq-upper-agent.exe`
- 由 `agent-config.template.ini` 填写形成的 `agent-config.ini`
- 上位机服务端证书、私钥和受信任客户端 CA 证书
- 工厂批准的适配器程序（仅 `DURR_APPROVED_ADAPTER` 使用）

## 启动

```powershell
.\pq-upper-agent.exe --config=.\agent-config.ini
```

建议由工厂 IT/OT 运维按批准流程配置 Windows 服务、程序签名白名单、目录权限和防火墙白名单。代理日志只记录发布单号、动作、时间和结果，不记录证书私钥或完整参数内容。

详细通信说明见 [`../../docs/pq-upper-computer-protocol.md`](../../docs/pq-upper-computer-protocol.md)。
