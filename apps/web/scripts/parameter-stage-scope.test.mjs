import assert from "node:assert/strict";
import test from "node:test";

const STAGE_PREFIX = {
  MIDCOAT_EXT: "midcoat",
  BASECOAT_1: "basecoat_1",
  BASECOAT_2: "basecoat_2",
  CLEARCOAT_1: "clearcoat_1",
  CLEARCOAT_2: "clearcoat_2",
};

const FAMILY_PREFIX = {
  MIDCOAT_EXT: "midcoat",
  BASECOAT_1: "basecoat",
  BASECOAT_2: "basecoat",
  CLEARCOAT_1: "clearcoat",
  CLEARCOAT_2: "clearcoat",
};

function definitionsForProcessStage(definitions, processStage) {
  if (!processStage) return [];
  const stagePrefix = STAGE_PREFIX[processStage];
  const familyPrefix = FAMILY_PREFIX[processStage];
  if (!stagePrefix || !familyPrefix) return [];

  return definitions.filter((definition) => {
    const code = definition.code;
    if (code.startsWith(`${stagePrefix}_`)) return true;
    if (
      code.startsWith(`${familyPrefix}_`) &&
      !code.startsWith("basecoat_1_") &&
      !code.startsWith("basecoat_2_") &&
      !code.startsWith("clearcoat_1_") &&
      !code.startsWith("clearcoat_2_")
    ) {
      return true;
    }
    if (processStage.startsWith("BASECOAT") && code === "basecoat_pass_ratio") return true;
    if (processStage.startsWith("CLEARCOAT") && code === "clearcoat_pass_ratio") return true;
    return false;
  });
}

const catalog = [
  { code: "midcoat_spray_flow" },
  { code: "midcoat_gun_distance" },
  { code: "basecoat_1_spray_flow" },
  { code: "basecoat_gun_distance" },
  { code: "basecoat_pass_ratio" },
  { code: "clearcoat_1_voltage" },
  { code: "clearcoat_pass_ratio" },
];

test("midcoat program only sees midcoat parameters", () => {
  const codes = definitionsForProcessStage(catalog, "MIDCOAT_EXT").map((item) => item.code).sort();
  assert.deepEqual(codes, ["midcoat_gun_distance", "midcoat_spray_flow"]);
});

test("basecoat_1 includes station params, family geometry, and pass ratio", () => {
  const codes = definitionsForProcessStage(catalog, "BASECOAT_1").map((item) => item.code).sort();
  assert.deepEqual(codes, ["basecoat_1_spray_flow", "basecoat_gun_distance", "basecoat_pass_ratio"]);
});

test("clearcoat_2 does not include basecoat or midcoat", () => {
  const codes = definitionsForProcessStage(catalog, "CLEARCOAT_2").map((item) => item.code);
  assert.ok(!codes.includes("midcoat_spray_flow"));
  assert.ok(!codes.includes("basecoat_1_spray_flow"));
  assert.deepEqual(codes, ["clearcoat_pass_ratio"]);
});
