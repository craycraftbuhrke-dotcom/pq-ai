"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const tls = require("node:tls");

const PROTOCOL = "PQRP/1";
const VERSION = "1.0.0";

function parseIni(text) {
  const result = {};
  for (const rawLine of text.replace(/^\uFEFF/, "").split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#") || line.startsWith(";")) continue;
    const separator = line.indexOf("=");
    if (separator < 1) continue;
    result[line.slice(0, separator).trim()] = line.slice(separator + 1).trim();
  }
  return result;
}

function resolvePath(baseDir, value) {
  if (!value) return "";
  return path.isAbsolute(value) ? value : path.resolve(baseDir, value);
}

function loadConfig() {
  const configArgument = process.argv.find((value) => value.startsWith("--config="));
  const configPath = configArgument
    ? path.resolve(configArgument.slice("--config=".length))
    : path.resolve(path.dirname(process.execPath), "agent-config.ini");
  if (!fs.existsSync(configPath)) {
    throw new Error(`找不到配置文件：${configPath}`);
  }
  const values = parseIni(fs.readFileSync(configPath, "utf8"));
  const baseDir = path.dirname(configPath);
  const required = ["agentId", "certificateFile", "privateKeyFile", "trustedClientCaFile", "dataDirectory"];
  const missing = required.filter((key) => !values[key]);
  if (missing.length) throw new Error(`配置文件缺少：${missing.join(", ")}`);
  const adapterMode = values.adapterMode || "SIMULATOR";
  if (!["SIMULATOR", "FILE_DROP", "DURR_APPROVED_ADAPTER"].includes(adapterMode)) {
    throw new Error("adapterMode 只能是 SIMULATOR、FILE_DROP 或 DURR_APPROVED_ADAPTER");
  }
  if (adapterMode === "FILE_DROP" && !values.importInbox) {
    throw new Error("FILE_DROP 模式必须配置厂家认可的参数导入目录 importInbox");
  }
  if (adapterMode === "DURR_APPROVED_ADAPTER" && !values.approvedAdapterCommand) {
    throw new Error("DURR_APPROVED_ADAPTER 模式必须配置工厂批准的适配器程序 approvedAdapterCommand");
  }
  if (adapterMode !== "SIMULATOR" && !values.readbackFile) {
    throw new Error("非模拟模式必须配置上位机回读文件 readbackFile");
  }
  const listenPort = Number(values.listenPort || 9443);
  const localUiPort = Number(values.localUiPort || 19090);
  const maxPackageBytes = Number(values.maxPackageBytes || 5_242_880);
  if (!Number.isInteger(listenPort) || listenPort < 1 || listenPort > 65_535) {
    throw new Error("listenPort 必须是 1 至 65535 的整数");
  }
  if (!Number.isInteger(localUiPort) || localUiPort < 1 || localUiPort > 65_535) {
    throw new Error("localUiPort 必须是 1 至 65535 的整数");
  }
  if (listenPort === localUiPort) {
    throw new Error("listenPort 与 localUiPort 不能使用同一端口");
  }
  if (!Number.isSafeInteger(maxPackageBytes) || maxPackageBytes < 1_024 || maxPackageBytes > 20_971_520) {
    throw new Error("maxPackageBytes 必须是 1024 至 20971520 的整数");
  }
  return {
    configPath,
    agentId: values.agentId,
    listenHost: values.listenHost || "127.0.0.1",
    listenPort,
    localUiPort,
    certificateFile: resolvePath(baseDir, values.certificateFile),
    privateKeyFile: resolvePath(baseDir, values.privateKeyFile),
    trustedClientCaFile: resolvePath(baseDir, values.trustedClientCaFile),
    dataDirectory: resolvePath(baseDir, values.dataDirectory),
    adapterMode,
    importInbox: resolvePath(baseDir, values.importInbox),
    readbackFile: resolvePath(baseDir, values.readbackFile),
    approvedAdapterCommand: resolvePath(baseDir, values.approvedAdapterCommand),
    maxPackageBytes,
  };
}

function stableStringify(value) {
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function hash(value) {
  return crypto.createHash("sha256").update(Buffer.from(stableStringify(value), "utf8")).digest("hex");
}

function canonicalDecimal(value) {
  if (typeof value === "number" && !Number.isFinite(value)) throw new Error("参数值必须是有限数字");
  const source = String(value).trim();
  const match = source.match(/^([+-]?)(\d+)(?:\.(\d*))?(?:[eE]([+-]?\d+))?$/);
  if (!match) throw new Error("完整刷子表包含无法识别的参数值");
  const sign = match[1] === "-" ? "-" : "";
  const integer = match[2];
  const fraction = match[3] || "";
  const exponent = Number(match[4] || 0);
  const digits = `${integer}${fraction}`;
  const decimalPosition = integer.length + exponent;
  let expanded;
  if (decimalPosition <= 0) expanded = `0.${"0".repeat(-decimalPosition)}${digits}`;
  else if (decimalPosition >= digits.length) expanded = `${digits}${"0".repeat(decimalPosition - digits.length)}`;
  else expanded = `${digits.slice(0, decimalPosition)}.${digits.slice(decimalPosition)}`;
  const [whole, decimals = ""] = expanded.split(".");
  const normalizedWhole = whole.replace(/^0+(?=\d)/, "") || "0";
  const normalizedDecimals = decimals.replace(/0+$/, "");
  const normalized = normalizedDecimals ? `${normalizedWhole}.${normalizedDecimals}` : normalizedWhole;
  return /^0(?:\.0*)?$/.test(normalized) ? "0" : `${sign}${normalized}`;
}

function normalizeCompleteTable(value) {
  if (!value || typeof value !== "object" || !Array.isArray(value.brushes)) throw new Error("完整刷子表结构不合法");
  const table = JSON.parse(JSON.stringify(value));
  for (const brush of table.brushes) {
    if (!brush || !Array.isArray(brush.parameters)) throw new Error("完整刷子表缺少刷子参数");
    for (const parameter of brush.parameters) parameter.value = canonicalDecimal(parameter.value);
  }
  return table;
}

function atomicWrite(filePath, content) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const temporary = `${filePath}.${process.pid}.${Date.now()}.tmp`;
  fs.writeFileSync(temporary, content, { flag: "wx" });
  fs.renameSync(temporary, filePath);
}

function safeReleaseNo(value) {
  const releaseNo = String(value || "");
  if (!/^[A-Za-z0-9_.-]{1,80}$/.test(releaseNo)) throw new Error("发布单编号不合法");
  return releaseNo;
}

function readJson(filePath) {
  if (!filePath || !fs.existsSync(filePath)) return null;
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function startAgent(config) {
  const stagedDirectory = path.join(config.dataDirectory, "staged");
  const confirmationDirectory = path.join(config.dataDirectory, "confirmed");
  const rejectedDirectory = path.join(config.dataDirectory, "rejected");
  const simulatorLiveFile = path.join(config.dataDirectory, "simulator-live.json");
  const auditFile = path.join(config.dataDirectory, "agent-audit.log");
  for (const directory of [config.dataDirectory, stagedDirectory, confirmationDirectory, rejectedDirectory]) {
    fs.mkdirSync(directory, { recursive: true });
  }
  const nonces = new Map();
  const localUiToken = crypto.randomBytes(32).toString("hex");

  function audit(event, releaseNo, result) {
    const line = JSON.stringify({ at: new Date().toISOString(), event, releaseNo: releaseNo || null, result });
    fs.appendFileSync(auditFile, `${line}\n`, "utf8");
  }

  function currentTable() {
    const table = config.adapterMode === "SIMULATOR" ? readJson(simulatorLiveFile) : readJson(config.readbackFile);
    return table ? normalizeCompleteTable(table) : null;
  }

  function stagedPath(releaseNo) { return path.join(stagedDirectory, `${safeReleaseNo(releaseNo)}.json`); }
  function confirmationPath(releaseNo) { return path.join(confirmationDirectory, `${safeReleaseNo(releaseNo)}.approved`); }
  function rejectionPath(releaseNo) { return path.join(rejectedDirectory, `${safeReleaseNo(releaseNo)}.rejected`); }

  function pruneNonces() {
    const cutoff = Date.now() - 10 * 60 * 1000;
    for (const [nonce, at] of nonces.entries()) if (at < cutoff) nonces.delete(nonce);
  }

  function validateEnvelope(envelope) {
    if (!envelope || envelope.protocol !== PROTOCOL) throw new Error("协议版本不匹配");
    if (envelope.agentId !== config.agentId) throw new Error("代理编号不匹配");
    if (!envelope.body || envelope.bodyHash !== hash(envelope.body)) throw new Error("消息完整性校验失败");
    const sentAt = Date.parse(envelope.sentAt);
    if (!Number.isFinite(sentAt) || Math.abs(Date.now() - sentAt) > 5 * 60 * 1000) throw new Error("消息时间超出允许范围");
    pruneNonces();
    if (!envelope.nonce || nonces.has(envelope.nonce)) throw new Error("检测到重复消息");
    nonces.set(envelope.nonce, Date.now());
  }

  function response(type, body, requestId) {
    return {
      protocol: PROTOCOL,
      messageId: crypto.randomUUID(),
      replyTo: requestId,
      sentAt: new Date().toISOString(),
      nonce: crypto.randomBytes(16).toString("hex"),
      agentId: config.agentId,
      type,
      body,
      bodyHash: hash(body),
    };
  }

  function applyRelease(releaseNo, staged) {
    const completeTable = staged.body.package.completeBrushTable;
    const expectedHash = staged.body.package.candidatePayloadHash;
    if (hash(completeTable) !== expectedHash) throw new Error("候选完整刷子表哈希不匹配");
    if (config.adapterMode === "SIMULATOR") {
      atomicWrite(simulatorLiveFile, JSON.stringify(completeTable, null, 2));
      return { applied: true, deliveryMode: "SIMULATOR", message: "模拟端已更新" };
    }
    if (config.adapterMode === "FILE_DROP") {
      if (!config.importInbox) throw new Error("未配置厂家认可的参数导入目录");
      const target = path.join(config.importInbox, `${releaseNo}.pqai.json`);
      if (fs.existsSync(target)) {
        if (hash(readJson(target)) !== hash(staged.body.package)) throw new Error("厂家导入目录已存在同名但内容不同的参数包");
      } else {
        atomicWrite(target, JSON.stringify(staged.body.package, null, 2));
      }
      const readback = currentTable();
      return {
        applied: Boolean(readback && hash(readback) === expectedHash),
        waitingReadback: !(readback && hash(readback) === expectedHash),
        deliveryMode: "FILE_DROP",
        message: readback && hash(readback) === expectedHash ? "厂家导入完成且回读一致" : "参数包已交付厂家导入目录，等待上位机导入并生成回读文件",
      };
    }
    if (!config.approvedAdapterCommand) throw new Error("未配置 Dürr/工厂认可的适配器程序");
    const { spawnSync } = require("node:child_process");
    const result = spawnSync(config.approvedAdapterCommand, ["apply", stagedPath(releaseNo)], {
      windowsHide: true,
      shell: false,
      timeout: 30_000,
      encoding: "utf8",
    });
    if (result.status !== 0) throw new Error("认可适配器执行失败，请在上位机检查适配器日志");
    const readback = currentTable();
    return {
      applied: Boolean(readback && hash(readback) === expectedHash),
      waitingReadback: !(readback && hash(readback) === expectedHash),
      deliveryMode: "DURR_APPROVED_ADAPTER",
      message: readback && hash(readback) === expectedHash ? "认可适配器执行完成且回读一致" : "认可适配器已执行，但回读尚未一致",
    };
  }

  function handle(envelope) {
    validateEnvelope(envelope);
    const body = envelope.body;
    if (envelope.type === "HELLO") {
      return response("HELLO_ACK", { agentVersion: VERSION, adapterMode: config.adapterMode, readOnly: true }, envelope.messageId);
    }
    if (envelope.type === "INVENTORY_REQUEST") {
      const table = currentTable();
      if (!table) throw new Error("尚无可回读的完整刷子表");
      return response("INVENTORY_RESPONSE", { completeBrushTable: table, payloadHash: hash(table), versionLabel: table.version || "REMOTE-LATEST", collectionRef: `PQRP:${new Date().toISOString()}` }, envelope.messageId);
    }
    if (envelope.type === "PREPARE_RELEASE") {
      const releaseNo = safeReleaseNo(body.releaseNo);
      if (!body.approvedBy || !body.approvedAt) throw new Error("发布包没有审批证据");
      if (!body.package || body.packageHash !== hash(body.package)) throw new Error("发布包完整性校验失败");
      const normalizedTable = normalizeCompleteTable(body.package.completeBrushTable);
      if (stableStringify(normalizedTable) !== stableStringify(body.package.completeBrushTable)) throw new Error("参数值必须使用规范十进制字符串");
      if (body.package.candidatePayloadHash !== hash(normalizedTable)) throw new Error("候选完整刷子表哈希不匹配");
      const target = stagedPath(releaseNo);
      if (fs.existsSync(target)) {
        const existing = readJson(target);
        if (existing.body.packageHash !== body.packageHash) throw new Error("同一发布单编号已暂存不同内容");
      } else {
        atomicWrite(target, JSON.stringify({ receivedAt: new Date().toISOString(), body }, null, 2));
      }
      audit("PREPARE_RELEASE", releaseNo, "STAGED_ONLY");
      return response("PREPARE_ACK", { accepted: true, localConfirmed: fs.existsSync(confirmationPath(releaseNo)), localRejected: fs.existsSync(rejectionPath(releaseNo)), message: "仅已暂存，尚未应用" }, envelope.messageId);
    }
    if (envelope.type === "RELEASE_STATUS_REQUEST") {
      const releaseNo = safeReleaseNo(body.releaseNo);
      return response("RELEASE_STATUS_RESPONSE", { staged: fs.existsSync(stagedPath(releaseNo)), localConfirmed: fs.existsSync(confirmationPath(releaseNo)), localRejected: fs.existsSync(rejectionPath(releaseNo)) }, envelope.messageId);
    }
    if (envelope.type === "COMMIT_RELEASE") {
      const releaseNo = safeReleaseNo(body.releaseNo);
      const file = stagedPath(releaseNo);
      if (!fs.existsSync(file)) throw new Error("找不到已暂存发布包");
      if (fs.existsSync(rejectionPath(releaseNo))) throw new Error("现场人员已拒绝该发布包");
      if (!fs.existsSync(confirmationPath(releaseNo))) throw new Error("现场人员尚未确认");
      const staged = readJson(file);
      if (staged.body.packageHash !== body.packageHash) throw new Error("提交哈希与暂存包不一致");
      const result = applyRelease(releaseNo, staged);
      audit("COMMIT_RELEASE", releaseNo, result.applied ? "APPLIED" : "WAITING_READBACK");
      return response("COMMIT_ACK", result, envelope.messageId);
    }
    throw new Error("不支持的消息类型");
  }

  const tlsOptions = {
    cert: fs.readFileSync(config.certificateFile),
    key: fs.readFileSync(config.privateKeyFile),
    ca: fs.readFileSync(config.trustedClientCaFile),
    requestCert: true,
    rejectUnauthorized: true,
    minVersion: "TLSv1.2",
  };

  const tlsServer = tls.createServer(tlsOptions, (socket) => {
    let buffer = Buffer.alloc(0);
    socket.setTimeout(15_000);
    socket.on("data", (chunk) => {
      buffer = Buffer.concat([buffer, chunk]);
      if (buffer.length < 4) return;
      const size = buffer.readUInt32BE(0);
      if (size <= 0 || size > config.maxPackageBytes) { socket.destroy(); return; }
      if (buffer.length < size + 4) return;
      let outgoing;
      try {
        const envelope = JSON.parse(buffer.subarray(4, size + 4).toString("utf8"));
        outgoing = handle(envelope);
      } catch (error) {
        outgoing = response("ERROR", { message: error instanceof Error ? error.message : "请求处理失败" }, null);
      }
      const encoded = Buffer.from(stableStringify(outgoing), "utf8");
      const header = Buffer.alloc(4); header.writeUInt32BE(encoded.length);
      socket.end(Buffer.concat([header, encoded]));
    });
  });
  tlsServer.on("tlsClientError", (error) => audit("TLS_CLIENT_ERROR", null, error.code || "TLS_ERROR"));
  tlsServer.listen(config.listenPort, config.listenHost);

  function listStaged() {
    return fs.readdirSync(stagedDirectory).filter((name) => name.endsWith(".json")).map((name) => {
      const releaseNo = name.slice(0, -5);
      const item = readJson(path.join(stagedDirectory, name));
      return { releaseNo, receivedAt: item.receivedAt, approvedBy: item.body.approvedBy, locallyConfirmed: fs.existsSync(confirmationPath(releaseNo)), locallyRejected: fs.existsSync(rejectionPath(releaseNo)) };
    });
  }

  function html() {
    const rows = listStaged().map((item) => {
      const decided = item.locallyConfirmed || item.locallyRejected;
      const status = item.locallyConfirmed ? "已确认" : item.locallyRejected ? "已拒绝" : "待确认";
      const actions = decided ? "" : `<div class="actions"><form method="post" action="/releases/${encodeURIComponent(item.releaseNo)}/approve"><input type="hidden" name="token" value="${localUiToken}"><button>现场确认</button></form><form method="post" action="/releases/${encodeURIComponent(item.releaseNo)}/reject"><input type="hidden" name="token" value="${localUiToken}"><button class="reject">拒绝</button></form></div>`;
      return `<tr><td>${escapeHtml(item.releaseNo)}</td><td>${escapeHtml(item.receivedAt)}</td><td>${escapeHtml(item.approvedBy)}</td><td>${status}</td><td>${actions}</td></tr>`;
    }).join("");
    return `<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'"><title>PQ-AI 上位机代理</title><style>body{font-family:Arial,sans-serif;margin:32px;color:#17202a;background:#f5f7f8}main{max-width:1000px;margin:auto;background:white;border:1px solid #dfe5e8;border-radius:14px;padding:24px}h1{font-size:22px}p{color:#56636b;line-height:1.6}.safe{background:#edf8f5;border:1px solid #a9d8cc;padding:14px;border-radius:10px}table{width:100%;border-collapse:collapse;margin-top:18px}th,td{text-align:left;border-bottom:1px solid #e5e9eb;padding:10px}.actions{display:flex;gap:8px}.actions form{margin:0}button{background:#087c6b;color:white;border:0;border-radius:7px;padding:8px 12px;cursor:pointer}.reject{background:#a43e32}</style><main><h1>PQ-AI 上位机代理</h1><p class="safe">当前适配方式：${escapeHtml(config.adapterMode)}。云端上传只进入暂存区，必须在本机页面人工确认后才能提交。</p><p>代理编号：${escapeHtml(config.agentId)} · 通信监听：${escapeHtml(config.listenHost)}:${config.listenPort}</p><table><thead><tr><th>发布单</th><th>收到时间</th><th>云端审批人</th><th>本机状态</th><th>操作</th></tr></thead><tbody>${rows || '<tr><td colspan="5">暂无待确认发布包</td></tr>'}</tbody></table></main></html>`;
  }

  function escapeHtml(value) { return String(value || "").replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]); }

  const uiServer = http.createServer((request, response) => {
    if (request.socket.remoteAddress !== "127.0.0.1" && request.socket.remoteAddress !== "::1" && request.socket.remoteAddress !== "::ffff:127.0.0.1") { response.writeHead(403).end(); return; }
    if (request.method === "GET" && request.url === "/") { response.writeHead(200, { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" }).end(html()); return; }
    const match = request.method === "POST" && request.url.match(/^\/releases\/([A-Za-z0-9_.-]+)\/(approve|reject)$/);
    if (!match) { response.writeHead(404).end(); return; }
    let body = "";
    request.on("data", (chunk) => { body += chunk; if (body.length > 4096) request.destroy(); });
    request.on("end", () => {
      const token = new URLSearchParams(body).get("token");
      const suppliedToken = Buffer.from(token || "");
      const expectedToken = Buffer.from(localUiToken);
      if (suppliedToken.length !== expectedToken.length || !crypto.timingSafeEqual(suppliedToken, expectedToken)) { response.writeHead(403).end(); return; }
      const releaseNo = safeReleaseNo(match[1]);
      if (!fs.existsSync(stagedPath(releaseNo))) { response.writeHead(404).end(); return; }
      if (fs.existsSync(confirmationPath(releaseNo)) || fs.existsSync(rejectionPath(releaseNo))) { response.writeHead(409).end(); return; }
      if (match[2] === "approve") {
        atomicWrite(confirmationPath(releaseNo), `${new Date().toISOString()}\n`);
        audit("LOCAL_CONFIRM", releaseNo, "CONFIRMED");
      } else {
        atomicWrite(rejectionPath(releaseNo), `${new Date().toISOString()}\n`);
        audit("LOCAL_REJECT", releaseNo, "REJECTED");
      }
      response.writeHead(303, { Location: "/" }).end();
    });
  });
  uiServer.listen(config.localUiPort, "127.0.0.1");
  console.log(`PQ-AI 上位机代理 ${VERSION} 已启动`);
  console.log(`本机确认页面：http://127.0.0.1:${config.localUiPort}`);
}

try {
  startAgent(loadConfig());
} catch (error) {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
}
