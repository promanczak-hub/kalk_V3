const fs = require('fs');
const path = require('path');

const filePath = path.join(__dirname, 'src/VertexExtractor/components/VehicleTableParts/VehicleRowCard.tsx');
let content = fs.readFileSync(filePath, 'utf8');

// Normalize newlines to \n for easier manipulation
let normalized = content.replace(/\r\n/g, '\n');

// The marker strings
const optionsStart = "  // Determine price domain from deterministic backend detection";
const optionsEnd = "    } finally {\n      setIsSavingServices(false);\n    }\n  };\n";

let idx1 = normalized.indexOf(optionsStart);
let idx2 = normalized.indexOf(optionsEnd, idx1);

if (idx1 !== -1 && idx2 !== -1) {
  const replacementOptions = `  const {
    customServiceOptions,
    customFactoryOptions,
    isSavingServices,
    homologationResult,
    handleUpdateServiceOptionName,
    handleUpdateServiceOptionPrice,
    handleUpdateServiceOptionIncludeInWr,
    handleRemoveServiceOption,
    handleAddManualServiceOption,
    handleUpdateFactoryOptionName,
    handleUpdateFactoryOptionPrice,
    handleUpdateFactoryOptionNoDiscount,
    handleRemoveFactoryOption,
    handleAddManualFactoryOption,
    handleRestoreAllOptions,
    handleSaveAllOptions,
  } = useVehicleOptionsManager(vehicle, onRefresh);\n`;

  normalized = normalized.slice(0, idx1) + replacementOptions + normalized.slice(idx2 + optionsEnd.length);
  console.log("Options replaced.");
} else {
  console.log("Could not find options block.");
}

// Meta manager block
const metaStart = "  const [isMapping, setIsMapping] = useState(false);";
const metaEnd = "    } finally {\n      setIsMapping(false);\n    }\n  };\n";

let idx3 = normalized.indexOf(metaStart);
let idx4 = normalized.indexOf(metaEnd, idx3);

if (idx3 !== -1 && idx4 !== -1) {
    const replacementMeta = `  const {
    isMapping,
    handleSamarCategoryChange,
    handleEngineCategoryChange,
    handleDriveTypeChange,
    handleBodyTypeChange,
    handleMapDataSilent,
  } = useVehicleMetaManager(
    vehicle,
    serverMappedData,
    localMappedData,
    setLocalMappedData
  );\n`;

    normalized = normalized.slice(0, idx3) + replacementMeta + normalized.slice(idx4 + metaEnd.length);
    console.log("Meta replaced.");
} else {
    console.log("Could not find meta block.");
}

// Pricing manager block
const pricingStart = "  const [discountMode, setDiscountMode] = useState<\"offer\" | \"suggested\" | \"custom\">(() => {";
const pricingEnd = "      return `${val.toFixed(2)} PLN netto`;\n  };\n";

let idx5 = normalized.indexOf(pricingStart);
let idx6 = normalized.indexOf(pricingEnd, idx5);

if (idx5 !== -1 && idx6 !== -1) {
    const replacementPricing = `  const {
    discountMode,
    setDiscountMode,
    customDiscountPctRaw,
    setCustomDiscountPctRaw,
    aiExtractedBasePrice,
    aiBasePriceDeltaPln,
    requireManualPriceReview,
    calculationBlockReason,
    dynamicTotalOptionsPrice,
    totalCatalogPriceNet,
    discountableOptionsTotal,
    nonDiscountableOptionsTotal,
    customServiceOptionsPriceTotal,
    isDealerOffer,
    offerDiscountPercentage,
    suggestedDiscountPct,
    suggestedDiscountConfidence,
    activeDiscountPct,
    activeFinalPriceNet,
    formatCalculatedPrice,
    AI_PRICE_ALERT_THRESHOLD_PLN,
  } = useVehiclePricingManager({
    vehicle,
    catalogBasePriceNet,
    customFactoryOptions,
    customServiceOptions,
  });\n`;

    normalized = normalized.slice(0, idx5) + replacementPricing + normalized.slice(idx6 + pricingEnd.length);
    console.log("Pricing replaced.");
} else {
    console.log("Could not find pricing block.");
}

// Convert back to CRLF before writing
const finalContent = normalized.replace(/\n/g, '\r\n');
fs.writeFileSync(filePath, finalContent, 'utf8');
console.log("File saved successfully.");
