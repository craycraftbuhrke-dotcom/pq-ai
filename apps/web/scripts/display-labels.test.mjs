import assert from "node:assert/strict";
import test from "node:test";

const PROCESS_STAGE_LABELS = {
  MIDCOAT_EXT: "中涂外喷",
  BASECOAT_1: "色漆一站",
  BASECOAT_2: "色漆二站",
  CLEARCOAT_1: "清漆一站",
  CLEARCOAT_2: "清漆二站",
};

const QUALITY_TYPE_LABELS = {
  ORANGE_PEEL: "橘皮",
  COLOR_DIFFERENCE: "色差",
  THICKNESS: "膜厚",
};

const ROLE_LABELS = {
  ADMIN: "系统管理员",
  PROCESS_ENGINEER: "工艺工程师",
  QUALITY_ENGINEER: "质量工程师",
};

const STATUS_LABELS = {
  COMPLETED: "已完成",
  DEAD_LETTER: "需人工处理",
  MES_PRODUCTION_RUN_UPSERT: "同步生产车身",
};

test("critical factory labels stay Chinese", () => {
  assert.equal(PROCESS_STAGE_LABELS.MIDCOAT_EXT, "中涂外喷");
  assert.equal(QUALITY_TYPE_LABELS.ORANGE_PEEL, "橘皮");
  assert.equal(ROLE_LABELS.QUALITY_ENGINEER, "质量工程师");
  assert.equal(STATUS_LABELS.COMPLETED, "已完成");
  assert.equal(STATUS_LABELS.MES_PRODUCTION_RUN_UPSERT, "同步生产车身");
});
