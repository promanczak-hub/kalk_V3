const fs = require('fs');

const path = 'd:/kalk_v3/frontend/src/VertexExtractor/components/VehicleTableParts/VehicleRowCard.tsx';
let content = fs.readFileSync(path, 'utf8');

// 1. Hook imports
content = content.replace(
  'import { useReferenceData } from "../../hooks/useReferenceData";',
  'import { useReferenceData } from "../../hooks/useReferenceData";\nimport { useVehicleOptionsManager } from "../../hooks/useVehicleOptionsManager";\nimport { useVehicleMetaManager } from "../../hooks/useVehicleMetaManager";\nimport { useVehiclePricingManager } from "../../hooks/useVehiclePricingManager";'
);

// 2. Constants
const constsRegex = /\/\/ Static lists sourced from DB[\s\S]*?];\n/;
content = content.replace(constsRegex, 'import { ALL_SAMAR_CLASSES, ALL_ENGINE_TYPES } from "../../constants/vehicleMappings";\n');

// 3. Options Manager
const optionsRegex = /\s*\/\/ Determine price domain from deterministic backend detection[\s\S]*?const handleSaveAllOptions = async \(\) => \{[\s\S]*?finally \{\n      setIsSavingServices\(false\);\n    \}\n  \};\n/;

const optionsReplacement = `
  const {
    customServiceOptions,
    customFactoryOptions,
    isSavingServices,
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
  } = useVehicleOptionsManager(vehicle, onRefresh);
`;

content = content.replace(optionsRegex, optionsReplacement);

// 4. Meta Manager
const metaRegex = /\s*const handleSamarCategoryChange = async \(newCategory: string\) => \{[\s\S]*?setIsMapping\(false\);\n    \}\n  \};\n/;

const metaReplacement = `
  const {
    isMapping,
    handleSamarCategoryChange,
    handleEngineCategoryChange,
    handleDriveTypeChange,
    handleBodyTypeChange,
    handleMapDataSilent,
  } = useVehicleMetaManager(vehicle, serverMappedData, localMappedData, setLocalMappedData);
`;

content = content.replace(metaRegex, metaReplacement);

// Remove the original isMapping
const isMappingRegex = /\s*const \[isMapping, setIsMapping\] = useState\(false\);\n/;
content = content.replace(isMappingRegex, '');

// 5. Pricing Manager
const pricingRegex = /\s*const \[discountMode, setDiscountMode\] = useState[\s\S]*?return \`\$\{val\.toFixed\(2\)\} PLN netto\`;\n  \};\n/;

const pricingReplacement = `
  const {
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
  });
`;

content = content.replace(pricingRegex, pricingReplacement);

fs.writeFileSync(path, content, 'utf8');
console.log("Rewritten VehicleRowCard.tsx");
