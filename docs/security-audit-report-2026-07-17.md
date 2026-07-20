# PQ-AI 依赖与敏感信息审计记录（2026-07-17）

## 审计基线

- Node 锁文件：`package-lock.json`，`lockfileVersion=3`，SHA-256 `e50b2ff2e3a935c11a85866e50bdc3bc6eca930317fd436df5de2676935921b8`。
- Python 依赖清单：`services/api/pyproject.toml`，项目版本 `0.1.0`，生产直接依赖使用精确版本，SHA-256 `dd0797b1a3c313d987b1076be62a099b927d0f98cd7db2003aba6723524929d3`。
- Python 审计工具：`pip-audit 2.10.1`。
- 漏洞豁免：无。

Python 当前没有单独的传递依赖锁文件，因此每次镜像构建仍必须重新执行依赖审计；不得把本记录当作未来构建自动通过的依据。

## 执行命令与结果

```bash
npm audit --omit=dev --audit-level=moderate
# found 0 vulnerabilities

cd services/api
env -u PYTHONPATH .venv/Scripts/python.exe -m pip_audit --strict .
# No known vulnerabilities found
```

结论：在上述文件哈希和审计时间点下，无未豁免的中、高或严重风险。文件哈希变化后，本结论自动失效，CI 必须重新审计并生成新记录。

敏感信息扫描同时覆盖受 Git 管理和待提交文本文件，排除 `.git`、`node_modules`、`.next`、虚拟环境和二进制资源；账户、密码、令牌、私钥头和已知测试账号模式命中数为 0。
