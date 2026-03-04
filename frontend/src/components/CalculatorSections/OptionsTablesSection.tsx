import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { ListPlus } from "lucide-react";
import type { V1DataOption } from "../../types";
import FactoryOptionsManager from "../OptionsManager/FactoryOptionsManager";
import ServiceOptionsManager from "../OptionsManager/ServiceOptionsManager";

interface OptionsTablesSectionProps {
  data: V1DataOption;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  handleUpdateFactoryOption: (id: number, field: string, value: any) => void;
  handleAddFactoryOption: () => void;
  handleRemoveFactoryOption: (id: number) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  handleUpdateServiceOption: (id: number, field: string, value: any) => void;
  handleAddServiceOption: () => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  handleAddExtractedServiceOption: (extracted: any) => void;
  handleRemoveServiceOption: (id: number) => void;
}

export default function OptionsTablesSection({
  data,
  handleUpdateFactoryOption,
  handleAddFactoryOption,
  handleRemoveFactoryOption,
  handleUpdateServiceOption,
  handleAddServiceOption,
  handleAddExtractedServiceOption,
  handleRemoveServiceOption,
}: OptionsTablesSectionProps) {
  return (
    <Accordion
      sx={{
        borderRadius: "8px !important",
        overflow: "hidden",
        boxShadow: "0 4px 12px rgba(0,0,0,0.05)",
        "&:before": { display: "none" },
      }}
    >
      <AccordionSummary
        expandIcon={<ExpandMoreIcon />}
        sx={{
          bgcolor: "rgba(30, 58, 138, 0.03)",
          borderBottom: "1px solid rgba(0,0,0,0.06)",
        }}
      >
        <Typography
          variant="h6"
          sx={{ display: "flex", alignItems: "center", gap: 1 }}
        >
          <ListPlus size={20} color="#1e3a8a" />
          Opcje i Akcesoria
        </Typography>
      </AccordionSummary>
      <AccordionDetails sx={{ p: 0 }}>
        <FactoryOptionsManager
          options={data.OpcjeFabryczne}
          onUpdate={handleUpdateFactoryOption}
          onAdd={handleAddFactoryOption}
          onRemove={handleRemoveFactoryOption}
        />
        <ServiceOptionsManager
          options={data.OpcjeSerwisowe}
          onUpdate={handleUpdateServiceOption}
          onAdd={handleAddServiceOption}
          onAddExtracted={handleAddExtractedServiceOption}
          onRemove={handleRemoveServiceOption}
        />
      </AccordionDetails>
    </Accordion>
  );
}
