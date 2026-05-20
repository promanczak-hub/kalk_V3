import {
  Document,
  Page,
  Text,
  View,
  StyleSheet,
  Image,
  Font,
} from "@react-pdf/renderer";
import type { BrochureImage } from "./HeroSection";
import type { BrochureData, BrochureDimensions } from "./buildBrochureData";

// Helvetica (the @react-pdf default) lacks Polish glyphs (ł, ż, ś, ć, ę, ą…).
// LiberationSans is a metric-compatible font with full Latin Extended-A coverage.
Font.register({
  family: "LiberationSans",
  fonts: [
    { src: "/fonts/LiberationSans-Regular.ttf", fontWeight: "normal" },
    { src: "/fonts/LiberationSans-Bold.ttf", fontWeight: "bold" },
  ],
});

// ── Express Fleet Partner brand palette (from express.pl) ──
const BRAND = "#004687"; // Express corporate blue
const ACCENT = "#f79226"; // Express orange
const DARK = "#201c17"; // Express near-black text
const MEDIUM = "#475569"; // Slate-600
const LIGHT = "#94a3b8"; // Slate-400
const BG_LIGHT = "#f8fafc"; // Slate-50

const LOGO_SRC = "/express-logo.png";

const styles = StyleSheet.create({
  page: {
    paddingTop: 28,
    paddingBottom: 64,
    paddingHorizontal: 32,
    backgroundColor: "#ffffff",
    position: "relative",
    fontFamily: "LiberationSans",
  },
  stripe: {
    position: "absolute",
    top: 0,
    left: 0,
    bottom: 0,
    width: 6,
    backgroundColor: BRAND,
  },
  // ── Header ──
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    borderBottomWidth: 2,
    borderBottomColor: BRAND,
    paddingBottom: 10,
    marginBottom: 14,
  },
  headerLeft: { flexDirection: "column" },
  logo: { width: 120, height: 23, objectFit: "contain", marginBottom: 8 },
  brandName: {
    fontSize: 12,
    fontWeight: "bold",
    color: BRAND,
    letterSpacing: 2,
    textTransform: "uppercase",
  },
  modelName: { fontSize: 24, fontWeight: "bold", color: DARK, marginTop: 1 },
  editionName: { fontSize: 10, color: MEDIUM, marginTop: 2 },
  headerRight: { flexDirection: "column", alignItems: "flex-end", maxWidth: 200 },
  idRow: { flexDirection: "row", marginBottom: 2 },
  idLabel: { fontSize: 7, color: LIGHT, textTransform: "uppercase", letterSpacing: 0.5 },
  idValue: { fontSize: 9, color: DARK, fontWeight: "bold", marginLeft: 4 },
  // ── Hero ──
  heroContainer: {
    width: "100%",
    height: 210,
    marginBottom: 14,
    backgroundColor: BG_LIGHT,
    borderRadius: 4,
    overflow: "hidden",
  },
  heroImage: { width: "100%", height: "100%", objectFit: "cover" },
  // ── Section ──
  sectionTitle: {
    fontSize: 11,
    fontWeight: "bold",
    color: "#ffffff",
    backgroundColor: BRAND,
    textTransform: "uppercase",
    letterSpacing: 1,
    paddingVertical: 4,
    paddingHorizontal: 8,
    marginTop: 14,
    marginBottom: 8,
    borderRadius: 2,
  },
  // ── Specs grid (2-col) ──
  specsGrid: { flexDirection: "row", flexWrap: "wrap" },
  specItem: {
    width: "50%",
    flexDirection: "row",
    alignItems: "flex-start",
    marginBottom: 7,
    paddingRight: 12,
  },
  specDot: {
    width: 5,
    height: 5,
    borderRadius: 3,
    backgroundColor: ACCENT,
    marginTop: 3,
    marginRight: 8,
  },
  specContent: { flex: 1 },
  specLabel: { fontSize: 8, color: LIGHT, textTransform: "uppercase", letterSpacing: 0.5 },
  specValue: { fontSize: 10, color: DARK, marginTop: 1 },
  // ── Equipment ──
  equipmentGrid: { flexDirection: "row", flexWrap: "wrap" },
  equipColumn: { width: "50%", paddingRight: 10 },
  equipItem: { flexDirection: "row", alignItems: "flex-start", marginBottom: 2 },
  equipBullet: { fontSize: 6, color: ACCENT, marginRight: 4, marginTop: 2 },
  equipText: { fontSize: 8, color: DARK, flex: 1 },
  // ── Notes ──
  notesBox: {
    marginTop: 14,
    padding: 10,
    backgroundColor: "#fff7ed",
    borderRadius: 4,
    borderLeftWidth: 3,
    borderLeftColor: ACCENT,
  },
  notesTitle: { fontSize: 9, fontWeight: "bold", color: ACCENT, marginBottom: 3 },
  notesContent: { fontSize: 8, color: MEDIUM, lineHeight: 1.4 },
  // ── Footer ──
  footer: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 10,
    paddingHorizontal: 32,
    borderTopWidth: 2,
    borderTopColor: BRAND,
  },
  footerText: { fontSize: 7, color: LIGHT, flex: 1 },
  footerAccent: { fontSize: 8, color: BRAND, fontWeight: "bold" },
});

interface BrochurePDFProps {
  data: BrochureData;
  images: BrochureImage[];
  hiddenItems: Set<string>;
  notes: string;
  logoSrc?: string;
}

const fmt = (v: number | null | undefined, unit: string): string | null =>
  v !== null && v !== undefined ? `${v} ${unit}` : null;

// One spec row only if value is non-empty.
type Spec = { label: string; value: string };
const spec = (label: string, value: string | null | undefined): Spec | null =>
  value && String(value).trim() !== "" ? { label, value: String(value) } : null;

function SpecSection({ title, specs }: { title: string; specs: (Spec | null)[] }) {
  const visible = specs.filter((s): s is Spec => s !== null);
  if (visible.length === 0) return null;
  return (
    <View wrap={false}>
      <Text style={styles.sectionTitle}>{title}</Text>
      <View style={styles.specsGrid}>
        {visible.map((s, i) => (
          <View key={i} style={styles.specItem}>
            <View style={styles.specDot} />
            <View style={styles.specContent}>
              <Text style={styles.specLabel}>{s.label}</Text>
              <Text style={styles.specValue}>{s.value}</Text>
            </View>
          </View>
        ))}
      </View>
    </View>
  );
}

function dimensionSpecs(d: BrochureDimensions): (Spec | null)[] {
  return [
    spec("Długość", fmt(d.length_mm, "mm")),
    spec("Szerokość", fmt(d.width_mm, "mm")),
    spec("Wysokość", fmt(d.height_mm, "mm")),
    spec("Rozstaw osi", fmt(d.wheelbase_mm, "mm")),
    spec("Masa własna", fmt(d.curb_weight_kg, "kg")),
    spec("DMC", fmt(d.gross_vehicle_weight_kg, "kg")),
    spec("Ładowność", fmt(d.payload_kg, "kg")),
    spec("Zbiornik paliwa", fmt(d.fuel_tank_capacity_l, "l")),
    spec("Poj. ładunkowa", fmt(d.cargo_volume_m3, "m³")),
    spec("Długość paki", fmt(d.cargo_length_mm, "mm")),
    spec("Szerokość paki", fmt(d.cargo_width_mm, "mm")),
    spec("Wysokość paki", fmt(d.cargo_height_mm, "mm")),
  ];
}

function EquipmentSection({
  catIndex,
  category,
  hiddenItems,
}: {
  catIndex: number;
  category: BrochureData["equipment_categories"][number];
  hiddenItems: Set<string>;
}) {
  const visible = category.items
    .map((item, itemIdx) => ({ item, itemIdx }))
    .filter(
      ({ item, itemIdx }) =>
        item && String(item).trim() !== "" && !hiddenItems.has(`${catIndex}-${itemIdx}`),
    );
  if (visible.length === 0) return null;

  const mid = Math.ceil(visible.length / 2);
  const columns = [visible.slice(0, mid), visible.slice(mid)];

  return (
    <View>
      <Text style={styles.sectionTitle}>{category.category_name}</Text>
      <View style={styles.equipmentGrid}>
        {columns.map((col, ci) => (
          <View key={ci} style={styles.equipColumn}>
            {col.map(({ item, itemIdx }) => (
              <View key={itemIdx} style={styles.equipItem} wrap={false}>
                <Text style={styles.equipBullet}>●</Text>
                <Text style={styles.equipText}>{String(item)}</Text>
              </View>
            ))}
          </View>
        ))}
      </View>
    </View>
  );
}

export function BrochurePDFDocument({ data, images, hiddenItems, notes, logoSrc = LOGO_SRC }: BrochurePDFProps) {
  const mainImage = images.find((i) => i.isMain) || images[0];
  const vn = data.vehicle_name;

  const identifiers = [
    { label: "Nr oferty", value: data.offer_number },
    { label: "Konfiguracja", value: data.configuration_code },
    { label: "VIN", value: data.vin },
  ].filter((x) => x.value && x.value.trim() !== "");

  const techSpecs: (Spec | null)[] = [
    spec("Silnik / Napęd", vn.engine),
    spec("Moc", vn.horsepower ? `${vn.horsepower} KM` : null),
    spec("Skrzynia biegów", data.transmission),
    spec("Napęd", data.drive_type),
    spec("Paliwo", data.fuel),
    spec("Typ nadwozia", vn.body_type),
    spec("Koła", data.wheels ? `${data.wheels}"` : null),
    spec("Liczba miejsc", data.number_of_seats),
    spec("Kolor", data.exterior_color),
  ];

  return (
    <Document>
      <Page size="A4" style={styles.page}>
        <View style={styles.stripe} fixed />

        {/* ── HEADER (logo + identyfikatory) ── */}
        <View style={styles.header}>
          <View style={styles.headerLeft}>
            <Image src={logoSrc} style={styles.logo} />
            <Text style={styles.brandName}>{vn.brand || "Marka"}</Text>
            <Text style={styles.modelName}>{vn.model || "Model"}</Text>
            {vn.edition ? <Text style={styles.editionName}>{vn.edition}</Text> : null}
          </View>
          {identifiers.length > 0 ? (
            <View style={styles.headerRight}>
              {identifiers.map((id, i) => (
                <View key={i} style={styles.idRow}>
                  <Text style={styles.idLabel}>{id.label}:</Text>
                  <Text style={styles.idValue}>{id.value}</Text>
                </View>
              ))}
            </View>
          ) : null}
        </View>

        {/* ── HERO ── */}
        {mainImage ? (
          <View style={styles.heroContainer}>
            <Image src={mainImage.url} style={styles.heroImage} />
          </View>
        ) : null}

        {/* ── DANE TECHNICZNE ── */}
        <SpecSection title="Dane techniczne" specs={techSpecs} />

        {/* ── MASY I WYMIARY ── */}
        <SpecSection title="Masy i wymiary" specs={dimensionSpecs(data.dimensions)} />

        {/* ── SPALANIE I EMISJE ── */}
        <SpecSection title="Spalanie i emisje" specs={[spec("Emisja / zużycie (WLTP)", data.emissions)]} />

        {/* ── WYPOSAŻENIE (3 grupy, każda jako osobna sekcja) ── */}
        {data.equipment_categories.map((cat, i) => (
          <EquipmentSection key={i} catIndex={i} category={cat} hiddenItems={hiddenItems} />
        ))}

        {/* ── ADNOTACJA ── */}
        {notes && notes.trim() !== "" ? (
          <View style={styles.notesBox} wrap={false}>
            <Text style={styles.notesTitle}>Adnotacja</Text>
            <Text style={styles.notesContent}>{notes}</Text>
          </View>
        ) : null}

        {/* ── FOOTER ── */}
        <View style={styles.footer} fixed>
          <Text style={styles.footerText}>
            Express Fleet Partner — dokument ma charakter informacyjny i nie stanowi oferty
            w rozumieniu art. 66 KC.
          </Text>
          <Text
            style={styles.footerAccent}
            render={({ pageNumber, totalPages }) => `${pageNumber} / ${totalPages}`}
            fixed
          />
        </View>
      </Page>
    </Document>
  );
}
