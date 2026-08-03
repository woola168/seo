export interface OwnBrandIdentityInput {
  names: readonly string[];
  aliases: readonly string[];
}

export interface CompetitorIdentityInput {
  name: string;
  aliases: readonly string[];
}

export interface BrandIdentityConflict {
  field: "name" | "alias";
  value: string;
}

export function findCompetitorOwnBrandConflicts(
  ownBrand: OwnBrandIdentityInput,
  competitor: CompetitorIdentityInput,
): BrandIdentityConflict[] {
  const ownBrandValues = new Set(
    [...ownBrand.names, ...ownBrand.aliases]
      .map(normalizeBrandIdentityValue)
      .filter(Boolean),
  );
  const conflicts: BrandIdentityConflict[] = [];
  if (ownBrandValues.has(normalizeBrandIdentityValue(competitor.name))) {
    conflicts.push({ field: "name", value: competitor.name.trim() });
  }
  for (const alias of competitor.aliases) {
    if (ownBrandValues.has(normalizeBrandIdentityValue(alias))) {
      conflicts.push({ field: "alias", value: alias.trim() });
    }
  }
  return conflicts;
}

function normalizeBrandIdentityValue(value: string): string {
  return value
    .normalize("NFKC")
    .trim()
    .replace(/\s+/g, " ")
    .toLowerCase();
}
