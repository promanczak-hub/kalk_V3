// Mirror of backend `_is_package_name()` and `_PACKAGE_KEYWORDS` in
// core/feature_enrichment.py. Keep both sides in sync — frontend uses this to
// decide which factory_options rows get a sub-feature dropdown.
const PACKAGE_KEYWORDS = ['pakiet', 'pack', 'package', 'edition', 'paket'];

export const isPackageName = (name: string): boolean => {
  const lower = name.trim().toLowerCase();
  return PACKAGE_KEYWORDS.some((kw) => lower.includes(kw));
};
