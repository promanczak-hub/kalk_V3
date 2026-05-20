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
import type { BrochureData, BrochureDimensions, BrochureEquipmentCategory } from "./buildBrochureData";

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
const DARK = "#201c17";
const MEDIUM = "#475569";
const LIGHT = "#94a3b8";
const HAIRLINE = "#e2e8f0";
const BG_LIGHT = "#f8fafc";

const LOGO_SRC = "/express-logo.png";

const styles = StyleSheet.create({
  page: {
    paddingTop: 78,
    paddingBottom: 54,
    paddingHorizontal: 36,
    backgroundColor: "#ffffff",
    fontFamily: "LiberationSans",
    fontSize: 9,
    color: DARK,
  },
  // ── Running header ──
  header: {
    position: "absolute",
    top: 24,
    left: 36,
    right: 36,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    paddingBottom: 8,
    borderBottomWidth: 1,
    borderBottomColor: HAIRLINE,
  },
  logo: { width: 104, height: 20, objectFit: "contain" },
  headerRight: { flexDirection: "column", alignItems: "flex-end" },
  headerLine: { flexDirection: "row", marginBottom: 1 },
  headerLabel: { fontSize: 7, color: LIGHT, textTransform: "uppercase", letterSpacing: 0.5 },
  headerValue: { fontSize: 8, color: DARK, fontWeight: "bold", marginLeft: 4 },
  // ── Running footer ──
  footer: {
    position: "absolute",
    bottom: 22,
    left: 36,
    right: 36,
    flexDirection: "row",
    alignItems: "center",
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: HAIRLINE,
  },
  footerText: { fontSize: 7, color: LIGHT, flex: 1 },
  footerPage: { fontSize: 7, color: BRAND, fontWeight: "bold" },
  // ── Title block ──
  brandLabel: { fontSize: 10, color: BRAND, fontWeight: "bold", letterSpacing: 2, textTransform: "uppercase" },
  modelName: { fontSize: 30, color: DARK, fontWeight: "bold", marginTop: 1 },
  edition: { fontSize: 13, color: MEDIUM, fontWeight: "bold", marginTop: 1 },
  engineLine: { fontSize: 10, color: MEDIUM, marginTop: 6 },
  emissionsLine: { fontSize: 8.5, color: LIGHT, marginTop: 2 },
  // ── Hero ──
  heroRow: { flexDirection: "row", marginTop: 14, height: 200, gap: 8 },
  heroBig: { flex: 1.7, backgroundColor: BG_LIGHT, borderRadius: 4, overflow: "hidden" },
  heroBigFull: { flex: 1, backgroundColor: BG_LIGHT, borderRadius: 4, overflow: "hidden" },
  heroSideCol: { flex: 1, flexDirection: "column", gap: 8 },
  heroSide: { flex: 1, backgroundColor: BG_LIGHT, borderRadius: 4, overflow: "hidden" },
  heroImg: { width: "100%", height: "100%", objectFit: "cover" },
  // ── Prices box ──
  priceBox: {
    marginTop: 18,
    borderWidth: 1,
    borderColor: HAIRLINE,
    borderRadius: 4,
    padding: 12,
  },
  priceHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 8,
  },
  priceTitle: { fontSize: 13, fontWeight: "bold", color: DARK },
  priceColHead: { fontSize: 9, color: LIGHT },
  priceLine: { flexDirection: "row", justifyContent: "space-between", marginBottom: 4 },
  priceLineLabel: { fontSize: 9.5, color: MEDIUM },
  priceLineValue: { fontSize: 9.5, color: DARK, fontWeight: "bold" },
  priceTotalRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: 6,
    paddingTop: 6,
    borderTopWidth: 1,
    borderTopColor: HAIRLINE,
  },
  priceTotalLabel: { fontSize: 10.5, color: DARK, fontWeight: "bold" },
  priceTotalValue: { fontSize: 11, color: ACCENT, fontWeight: "bold" },
  priceMarker: { fontSize: 7.5, color: LIGHT, marginTop: 6 },
  // ── Section ──
  sectionTitle: {
    fontSize: 11,
    fontWeight: "bold",
    color: DARK,
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginTop: 18,
    marginBottom: 8,
    paddingBottom: 4,
    borderBottomWidth: 1.5,
    borderBottomColor: BRAND,
  },
  // ── Equipment ──
  eqGrid: { flexDirection: "row" },
  eqCol: { flex: 1, paddingRight: 12 },
  eqText: { fontSize: 8.5, color: DARK, marginBottom: 3.5, lineHeight: 1.35 },
  priceRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 4,
    paddingBottom: 4,
    borderBottomWidth: 1,
    borderBottomColor: HAIRLINE,
  },
  priceRowLabel: { fontSize: 9, color: DARK, flex: 1, paddingRight: 10 },
  priceRowValue: { fontSize: 9, color: MEDIUM, fontWeight: "bold" },
  // ── Tech spec groups ──
  specGroup: { marginBottom: 10 },
  specGroupTitle: { fontSize: 9.5, fontWeight: "bold", color: BRAND, marginBottom: 4 },
  kvRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 2.5,
    paddingBottom: 2.5,
    borderBottomWidth: 1,
    borderBottomColor: HAIRLINE,
  },
  kvLabel: { fontSize: 8.5, color: MEDIUM, flex: 1, paddingRight: 10 },
  kvValue: { fontSize: 8.5, color: DARK, fontWeight: "bold" },
  // ── Notes ──
  notesBox: {
    marginTop: 16,
    padding: 10,
    backgroundColor: "#fff7ed",
    borderRadius: 4,
    borderLeftWidth: 3,
    borderLeftColor: ACCENT,
  },
  notesTitle: { fontSize: 9, fontWeight: "bold", color: ACCENT, marginBottom: 3 },
  notesContent: { fontSize: 8.5, color: MEDIUM, lineHeight: 1.4 },
});

interface BrochurePDFProps {
  data: BrochureData;
  images: BrochureImage[];
  hiddenItems: Set<string>;
  notes: string;
  logoSrc?: string;
}

type KV = { label: string; value: string };

const join = (parts: (string | undefined | null)[], sep: string) =>
  parts.filter((p) => p && String(p).trim() !== "").join(sep);

const dim = (v: number | null | undefined, unit: string): string =>
  v !== null && v !== undefined ? `${v.toLocaleString("pl-PL")} ${unit}` : "";

const kv = (label: string, value: string): KV => ({ label, value });

function nonEmpty(rows: KV[]): KV[] {
  return rows.filter((r) => r.value && String(r.value).trim() !== "");
}

function SpecGroup({ title, rows }: { title: string; rows: KV[] }) {
  const visible = nonEmpty(rows);
  if (visible.length === 0) return null;
  return (
    <View style={styles.specGroup} wrap={false}>
      <Text style={styles.specGroupTitle}>{title}</Text>
      {visible.map((r, i) => (
        <View key={i} style={styles.kvRow}>
          <Text style={styles.kvLabel}>{r.label}</Text>
          <Text style={styles.kvValue}>{r.value}</Text>
        </View>
      ))}
    </View>
  );
}

function EquipmentSection({
  catIndex,
  category,
  hiddenItems,
}: {
  catIndex: number;
  category: BrochureEquipmentCategory;
  hiddenItems: Set<string>;
}) {
  const visible = category.items
    .map((it, i) => ({ it, i }))
    .filter(({ it, i }) => it.label && it.label.trim() !== "" && !hiddenItems.has(`${catIndex}-${i}`));
  if (visible.length === 0) return null;

  if (category.group === "standard") {
    const mid = Math.ceil(visible.length / 2);
    const cols = [visible.slice(0, mid), visible.slice(mid)];
    return (
      <View>
        <Text style={styles.sectionTitle}>{category.category_name}</Text>
        <View style={styles.eqGrid}>
          {cols.map((col, ci) => (
            <View key={ci} style={styles.eqCol}>
              {col.map(({ it, i }) => (
                <Text key={i} style={styles.eqText}>
                  {it.label}
                </Text>
              ))}
            </View>
          ))}
        </View>
      </View>
    );
  }

  return (
    <View>
      <Text style={styles.sectionTitle}>{category.category_name}</Text>
      {visible.map(({ it, i }) => (
        <View key={i} style={styles.priceRow} wrap={false}>
          <Text style={styles.priceRowLabel}>{it.label}</Text>
          {it.price ? <Text style={styles.priceRowValue}>{it.price}</Text> : null}
        </View>
      ))}
    </View>
  );
}

function dimensionRows(d: BrochureDimensions): KV[] {
  return [
    kv("Długość", dim(d.length_mm, "mm")),
    kv("Szerokość", dim(d.width_mm, "mm")),
    kv("Wysokość", dim(d.height_mm, "mm")),
    kv("Rozstaw osi", dim(d.wheelbase_mm, "mm")),
    kv("Poj. ładunkowa", dim(d.cargo_volume_m3, "m³")),
    kv("Długość paki", dim(d.cargo_length_mm, "mm")),
    kv("Szerokość paki", dim(d.cargo_width_mm, "mm")),
    kv("Wysokość paki", dim(d.cargo_height_mm, "mm")),
  ];
}

function massRows(d: BrochureDimensions): KV[] {
  return [
    kv("Masa własna", dim(d.curb_weight_kg, "kg")),
    kv("DMC", dim(d.gross_vehicle_weight_kg, "kg")),
    kv("Ładowność", dim(d.payload_kg, "kg")),
    kv("Zbiornik paliwa", dim(d.fuel_tank_capacity_l, "l")),
  ];
}

export function BrochurePDFDocument({ data, images, hiddenItems, notes, logoSrc = LOGO_SRC }: BrochurePDFProps) {
  const vn = data.vehicle_name;
  const mainImage = images.find((i) => i.isMain) || images[0];
  const sideImages = images.filter((i) => i !== mainImage).slice(0, 2);

  const identifiers = [
    { label: "Nr oferty", value: data.offer_number },
    { label: "Konfiguracja", value: data.configuration_code },
    { label: "VIN", value: data.vin },
  ].filter((x) => x.value && x.value.trim() !== "");

  const today = new Date().toLocaleDateString("pl-PL");

  const engineLine = join([vn.engine, data.transmission, data.drive_type], "  •  ");
  const emissionsLine = data.emissions ? `Emisja / zużycie (WLTP): ${data.emissions}` : "";

  const engineRows = nonEmpty([
    kv("Silnik", vn.engine),
    kv("Pojemność silnika", data.engine_capacity ? `${data.engine_capacity} l` : ""),
    kv("Moc", vn.horsepower ? `${vn.horsepower} KM` : ""),
    kv("Moc (kW)", data.power_kw ? `${data.power_kw} kW` : ""),
    kv("Skrzynia biegów", data.transmission),
    kv("Napęd", data.drive_type),
    kv("Paliwo", data.fuel),
  ]);
  const dimRows = nonEmpty(dimensionRows(data.dimensions));
  const mRows = nonEmpty(massRows(data.dimensions));
  const bodyRows = nonEmpty([
    kv("Typ nadwozia", vn.body_type),
    kv("Liczba miejsc", data.number_of_seats),
    kv("Koła", data.wheels ? `${data.wheels}"` : ""),
    kv("Kolor nadwozia", data.exterior_color),
  ]);
  const emissionRows = nonEmpty([kv("Emisja / zużycie (WLTP)", data.emissions)]);
  const hasTech =
    engineRows.length + dimRows.length + mRows.length + bodyRows.length + emissionRows.length > 0;

  const p = data.prices;
  const hasPrices = Boolean(p.base || p.options || p.totalCatalog);
  const priceMarker = `Ceny katalogowe${p.domain ? ` (${p.domain})` : ""} — bez rabatów i cen specjalnych${
    p.domain ? "" : "; sprawdź netto/brutto w ofercie"
  }.`;

  return (
    <Document>
      <Page size="A4" style={styles.page}>
        {/* ── Running header ── */}
        <View style={styles.header} fixed>
          <Image src={logoSrc} style={styles.logo} />
          <View style={styles.headerRight}>
            {identifiers.map((id, i) => (
              <View key={i} style={styles.headerLine}>
                <Text style={styles.headerLabel}>{id.label}:</Text>
                <Text style={styles.headerValue}>{id.value}</Text>
              </View>
            ))}
            <View style={styles.headerLine}>
              <Text style={styles.headerLabel}>Data:</Text>
              <Text style={styles.headerValue}>{today}</Text>
            </View>
          </View>
        </View>

        {/* ── Title block ── */}
        {vn.brand ? <Text style={styles.brandLabel}>{vn.brand}</Text> : null}
        <Text style={styles.modelName}>{vn.model || "Model"}</Text>
        {vn.edition ? <Text style={styles.edition}>{vn.edition}</Text> : null}
        {engineLine ? <Text style={styles.engineLine}>{engineLine}</Text> : null}
        {emissionsLine ? <Text style={styles.emissionsLine}>{emissionsLine}</Text> : null}

        {/* ── Hero grid ── */}
        {mainImage ? (
          <View style={styles.heroRow}>
            <View style={sideImages.length > 0 ? styles.heroBig : styles.heroBigFull}>
              <Image src={mainImage.url} style={styles.heroImg} />
            </View>
            {sideImages.length > 0 ? (
              <View style={styles.heroSideCol}>
                {sideImages.map((img) => (
                  <View key={img.id} style={styles.heroSide}>
                    <Image src={img.url} style={styles.heroImg} />
                  </View>
                ))}
              </View>
            ) : null}
          </View>
        ) : null}

        {/* ── Prices (catalog) ── */}
        {hasPrices ? (
          <View style={styles.priceBox} wrap={false}>
            <View style={styles.priceHeader}>
              <Text style={styles.priceTitle}>Ceny katalogowe</Text>
              <Text style={styles.priceColHead}>Cena</Text>
            </View>
            {p.base ? (
              <View style={styles.priceLine}>
                <Text style={styles.priceLineLabel}>Cena katalogowa pojazdu</Text>
                <Text style={styles.priceLineValue}>{p.base}</Text>
              </View>
            ) : null}
            {p.options ? (
              <View style={styles.priceLine}>
                <Text style={styles.priceLineLabel}>Wyposażenie opcjonalne i usługi</Text>
                <Text style={styles.priceLineValue}>{p.options}</Text>
              </View>
            ) : null}
            {p.totalCatalog ? (
              <View style={styles.priceTotalRow}>
                <Text style={styles.priceTotalLabel}>Razem (katalog)</Text>
                <Text style={styles.priceTotalValue}>{p.totalCatalog}</Text>
              </View>
            ) : null}
            <Text style={styles.priceMarker}>{priceMarker}</Text>
          </View>
        ) : null}

        {/* ── Equipment (3 grupy) ── */}
        {data.equipment_categories.map((cat, i) => (
          <EquipmentSection key={i} catIndex={i} category={cat} hiddenItems={hiddenItems} />
        ))}

        {/* ── Dane techniczne ── */}
        {hasTech ? (
          <View>
            <Text style={styles.sectionTitle}>Dane techniczne</Text>
            <SpecGroup title="Silnik i napęd" rows={engineRows} />
            <SpecGroup title="Wymiary" rows={dimRows} />
            <SpecGroup title="Masy" rows={mRows} />
            <SpecGroup title="Nadwozie" rows={bodyRows} />
            <SpecGroup title="Emisje i spalanie" rows={emissionRows} />
          </View>
        ) : null}

        {/* ── Adnotacja ── */}
        {notes && notes.trim() !== "" ? (
          <View style={styles.notesBox} wrap={false}>
            <Text style={styles.notesTitle}>Adnotacja</Text>
            <Text style={styles.notesContent}>{notes}</Text>
          </View>
        ) : null}

        {/* ── Running footer ── */}
        <View style={styles.footer} fixed>
          <Text style={styles.footerText}>
            Express Fleet Partner — dokument informacyjny, nie stanowi oferty w rozumieniu art. 66 KC.
          </Text>
          <Text
            style={styles.footerPage}
            render={({ pageNumber, totalPages }) => `${pageNumber} / ${totalPages}`}
            fixed
          />
        </View>
      </Page>
    </Document>
  );
}
