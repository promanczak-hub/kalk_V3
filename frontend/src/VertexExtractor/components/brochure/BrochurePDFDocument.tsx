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

// ── Roboto – full Polish glyph support ──
Font.register({
  family: "Roboto",
  fonts: [
    {
      src: "https://cdnjs.cloudflare.com/ajax/libs/pdfmake/0.2.12/fonts/Roboto/Roboto-Regular.ttf",
      fontWeight: "normal",
    },
    {
      src: "https://cdnjs.cloudflare.com/ajax/libs/pdfmake/0.2.12/fonts/Roboto/Roboto-Medium.ttf",
      fontWeight: "medium",
    },
    {
      src: "https://cdnjs.cloudflare.com/ajax/libs/pdfmake/0.2.12/fonts/Roboto/Roboto-Bold.ttf",
      fontWeight: "bold",
    },
    {
      src: "https://cdnjs.cloudflare.com/ajax/libs/pdfmake/0.2.12/fonts/Roboto/Roboto-Italic.ttf",
      fontStyle: "italic",
    },
  ],
});

const ACCENT = "#2563eb"; // Blue-600
const DARK = "#0f172a"; // Slate-900
const MEDIUM = "#475569"; // Slate-600
const LIGHT = "#94a3b8"; // Slate-400
const BG_LIGHT = "#f8fafc"; // Slate-50

const styles = StyleSheet.create({
  page: {
    padding: 0,
    backgroundColor: "#ffffff",
    fontFamily: "Roboto",
    position: "relative",
  },
  // ── Blue left stripe ──
  stripe: {
    position: "absolute",
    top: 0,
    left: 0,
    bottom: 0,
    width: 6,
    backgroundColor: ACCENT,
  },
  content: {
    paddingLeft: 30,
    paddingRight: 30,
    paddingTop: 30,
    paddingBottom: 60,
  },
  // ── Header ──
  brandName: {
    fontSize: 13,
    fontWeight: "bold",
    color: ACCENT,
    letterSpacing: 2,
    textTransform: "uppercase",
  },
  modelName: {
    fontSize: 28,
    fontWeight: "bold",
    color: DARK,
    marginTop: 2,
  },
  editionName: {
    fontSize: 11,
    color: MEDIUM,
    marginTop: 2,
  },
  // ── Hero Image ──
  heroContainer: {
    width: "100%",
    height: 200,
    marginTop: 16,
    marginBottom: 16,
    backgroundColor: BG_LIGHT,
    borderRadius: 4,
    overflow: "hidden",
  },
  heroImage: {
    width: "100%",
    height: "100%",
    objectFit: "cover",
  },
  // ── Section titles ──
  sectionTitle: {
    fontSize: 11,
    fontWeight: "bold",
    color: DARK,
    textTransform: "uppercase",
    letterSpacing: 1,
    marginBottom: 8,
    marginTop: 18,
    paddingBottom: 4,
    borderBottomWidth: 1,
    borderBottomColor: "#e2e8f0",
  },
  // ── Specs grid ──
  specsGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
  },
  specItem: {
    width: "50%",
    flexDirection: "row",
    alignItems: "flex-start",
    marginBottom: 8,
    paddingRight: 12,
  },
  specDot: {
    width: 5,
    height: 5,
    borderRadius: 3,
    backgroundColor: ACCENT,
    marginTop: 4,
    marginRight: 8,
  },
  specContent: {
    flex: 1,
  },
  specLabel: {
    fontSize: 8,
    color: LIGHT,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  specValue: {
    fontSize: 10,
    color: DARK,
    marginTop: 1,
  },
  // ── Equipment ──
  equipmentGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
  },
  equipCategory: {
    width: "50%",
    marginBottom: 10,
    paddingRight: 10,
  },
  equipCategoryTitle: {
    fontSize: 9,
    fontWeight: "bold",
    color: MEDIUM,
    marginBottom: 4,
  },
  equipItem: {
    flexDirection: "row",
    alignItems: "flex-start",
    marginBottom: 2,
  },
  equipBullet: {
    fontSize: 6,
    color: ACCENT,
    marginRight: 4,
    marginTop: 2,
  },
  equipText: {
    fontSize: 8,
    color: DARK,
    flex: 1,
  },
  // ── Notes ──
  notesBox: {
    marginTop: 14,
    padding: 10,
    backgroundColor: "#eff6ff",
    borderRadius: 4,
    borderLeftWidth: 3,
    borderLeftColor: ACCENT,
  },
  notesTitle: {
    fontSize: 9,
    fontWeight: "bold",
    color: ACCENT,
    marginBottom: 3,
  },
  notesContent: {
    fontSize: 8,
    color: MEDIUM,
    lineHeight: 1.4,
  },
  // ── Footer ──
  footer: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 10,
    paddingLeft: 30,
    paddingRight: 30,
    borderTopWidth: 2,
    borderTopColor: ACCENT,
  },
  footerText: {
    fontSize: 7,
    color: LIGHT,
    flex: 1,
  },
  footerAccent: {
    fontSize: 7,
    color: ACCENT,
    fontWeight: "bold",
  },
});

interface BrochurePDFProps {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any;
  images: BrochureImage[];
  hiddenItems: Set<string>;
  notes: string;
}

export function BrochurePDFDocument({
  data,
  images,
  hiddenItems,
  notes,
}: BrochurePDFProps) {
  const mainImage = images.find((i) => i.isMain) || images[0];
  const vn = data.vehicle_name || {};

  // Build specs array from available data
  const specs: { label: string; value: string }[] = [
    { label: "Silnik / Napęd", value: vn.engine || "-" },
    { label: "Typ nadwozia", value: vn.body_type || "-" },
    { label: "Moc", value: vn.horsepower ? `${vn.horsepower} KM` : "-" },
    { label: "Skrzynia biegów", value: data.transmission || "-" },
  ];

  // Split equipment into two-column layout
  const categories = data.equipment_categories || [];

  return (
    <Document>
      <Page size="A4" style={styles.page}>
        {/* Blue left stripe */}
        <View style={styles.stripe} fixed />

        <View style={styles.content}>
          {/* ── HEADER ── */}
          <Text style={styles.brandName}>{vn.brand || "Marka"}</Text>
          <Text style={styles.modelName}>{vn.model || "Model"}</Text>
          {vn.edition && <Text style={styles.editionName}>{vn.edition}</Text>}

          {/* ── HERO IMAGE ── */}
          {mainImage ? (
            <View style={styles.heroContainer}>
              <Image src={mainImage.url} style={styles.heroImage} />
            </View>
          ) : (
            <View style={styles.heroContainer} />
          )}

          {/* ── SPECYFIKACJA ── */}
          <Text style={styles.sectionTitle}>Specyfikacja</Text>
          <View style={styles.specsGrid}>
            {specs.map((spec, i) => (
              <View key={i} style={styles.specItem}>
                <View style={styles.specDot} />
                <View style={styles.specContent}>
                  <Text style={styles.specLabel}>{spec.label}</Text>
                  <Text style={styles.specValue}>{spec.value}</Text>
                </View>
              </View>
            ))}
          </View>

          {/* ── WYPOSAŻENIE ── */}
          {categories.length > 0 && (
            <>
              <Text style={styles.sectionTitle}>Wyposażenie</Text>
              <View style={styles.equipmentGrid}>
                {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                {categories.map((cat: any, cIdx: number) => {
                  const visibleItems = cat.items?.filter(
                    (_: string, iIdx: number) =>
                      !hiddenItems.has(`${cIdx}-${iIdx}`)
                  );
                  if (!visibleItems || visibleItems.length === 0) return null;
                  return (
                    <View key={cIdx} style={styles.equipCategory}>
                      <Text style={styles.equipCategoryTitle}>
                        {cat.category_name}
                      </Text>
                      {visibleItems.map((item: string, idx: number) => (
                        <View key={idx} style={styles.equipItem}>
                          <Text style={styles.equipBullet}>●</Text>
                          <Text style={styles.equipText}>{item}</Text>
                        </View>
                      ))}
                    </View>
                  );
                })}
              </View>
            </>
          )}

          {/* ── NOTATKI ── */}
          {notes && notes.trim() !== "" && (
            <View style={styles.notesBox}>
              <Text style={styles.notesTitle}>Dodatkowe informacje</Text>
              <Text style={styles.notesContent}>{notes}</Text>
            </View>
          )}
        </View>

        {/* ── FOOTER ── */}
        <View style={styles.footer} fixed>
          <Text style={styles.footerText}>
            Wygenerowano automatycznie — dokument ma charakter informacyjny i
            nie stanowi oferty w rozumieniu KC.
          </Text>
          <Text style={styles.footerAccent}>KALKULATOR</Text>
        </View>
      </Page>
    </Document>
  );
}
