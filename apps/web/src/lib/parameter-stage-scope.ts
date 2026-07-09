/** 按喷涂工序过滤参数定义：中涂程序只出现中涂相关参数。 */

const STAGE_PREFIX: Record<string, string> = {
  MIDCOAT_EXT: "midcoat",
  BASECOAT_1: "basecoat_1",
  BASECOAT_2: "basecoat_2",
  CLEARCOAT_1: "clearcoat_1",
  CLEARCOAT_2: "clearcoat_2",
};

const FAMILY_PREFIX: Record<string, string> = {
  MIDCOAT_EXT: "midcoat",
  BASECOAT_1: "basecoat",
  BASECOAT_2: "basecoat",
  CLEARCOAT_1: "clearcoat",
  CLEARCOAT_2: "clearcoat",
};

export type StageScopedDefinition = {
  id: string;
  code: string;
  name: string;
  unit: string;
  hard_min?: number | null;
  hard_max?: number | null;
  is_recommendable: boolean;
};

export function definitionsForProcessStage<T extends StageScopedDefinition>(
  definitions: T[],
  processStage: string | null | undefined,
): T[] {
  if (!processStage) return [];
  const stagePrefix = STAGE_PREFIX[processStage];
  const familyPrefix = FAMILY_PREFIX[processStage];
  if (!stagePrefix || !familyPrefix) return [];

  return definitions.filter((definition) => {
    const code = definition.code;
    if (code.startsWith(`${stagePrefix}_`)) return true;
    // 同涂层体系共享的几何/材料参数（如 midcoat_gun_distance）
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
