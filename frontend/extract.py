import os

os.makedirs("d:/kalk_v3/frontend/src/components/Calculator", exist_ok=True)

with open(
    "d:/kalk_v3/frontend/src/CalculatorPanel_HEAD.tsx", "r", encoding="utf-16"
) as f:
    text = f.read()


def get_block(start_marker, end_marker):
    s = text.find(start_marker)
    e = text.find(end_marker)
    if s == -1 or e == -1:
        return ""
    start_pos = text.rfind("\n", 0, s)
    end_box_idx = text.rfind("</Box>", 0, e) + 6
    if "<Accordion" in text[start_pos:s]:  # sometimes we want to include the <Accordion
        start_pos = text.rfind(
            "<Accordion", 0, s
        )  # actually, start_pos can be right before the comment
    return text[start_pos:end_box_idx]


# VehicleDataSection
vdata = get_block("{/* Wizytówka */}", "{/* Opcje fabryczne i serwisowe */}")
# OptionsTablesSection
opt_tables = get_block("{/* Opcje fabryczne i serwisowe */}", "{/* Opcje dodatkowe */}")
# AdditionalOptionsSection
add_options = get_block(
    "{/* Opcje dodatkowe */}", "{/* Wynik kalkulacji - szczegóły */}"
)
# CalculationSummarySection
calc_summary = get_block("{/* Wynik kalkulacji - szczegóły */}", "{/* Parser Modal */}")

templates = {
    "VehicleDataSection.tsx": """import React from 'react';
import {
  Accordion, AccordionSummary, AccordionDetails, Typography, Box, Grid, TextField, Select, MenuItem, Checkbox
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import type { V1DataOption } from "../../types";

interface Props {
  data: V1DataOption;
  expanded: string | false;
  handleChange: (panel: string) => (event: React.SyntheticEvent, isExpanded: boolean) => void;
  handleUpdate: (field: keyof V1DataOption, value: any) => void;
  handleUpdateNetto: (val: number) => void;
  handleUpdateBrutto: (val: number) => void;
  handleChangeTypRabatu: (val: string) => void;
  handleUpdateRabat: (val: number) => void;
}

export const VehicleDataSection: React.FC<Props> = ({
  data, expanded, handleChange, handleUpdate, handleUpdateNetto, handleUpdateBrutto, handleChangeTypRabatu, handleUpdateRabat
}) => {
  return (
    <>
{CONTENT}
    </>
  );
};
""",
    "OptionsTablesSection.tsx": """import React from 'react';
import {
  Accordion, AccordionSummary, AccordionDetails, Typography, Box, Button, Table, TableHead, TableRow, TableCell, TableBody, Checkbox, TextField
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import type { V1DataOption } from "../../types";

interface Props {
  data: V1DataOption;
  handleUpdateFactoryOption: (id: number, field: string, value: any) => void;
  handleAddFactoryOption: () => void;
  handleRemoveFactoryOption: (id: number) => void;
  handleUpdateServiceOption: (id: number, field: string, value: any) => void;
  handleAddServiceOption: () => void;
  handleRemoveServiceOption: (id: number) => void;
}

export const OptionsTablesSection: React.FC<Props> = ({
  data, handleUpdateFactoryOption, handleAddFactoryOption, handleRemoveFactoryOption, handleUpdateServiceOption, handleAddServiceOption, handleRemoveServiceOption
}) => {
  return (
    <>
{CONTENT}
    </>
  );
};
""",
    "AdditionalOptionsSection.tsx": """import React from 'react';
import {
  Accordion, AccordionSummary, AccordionDetails, Typography, Checkbox, Box, Grid
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import type { V1DataOption } from "../../types";

interface Props {
  data: V1DataOption;
  handleUpdate: (field: keyof V1DataOption, value: any) => void;
}

export const AdditionalOptionsSection: React.FC<Props> = ({
  data, handleUpdate
}) => {
  return (
    <>
{CONTENT}
    </>
  );
};
""",
    "CalculationSummarySection.tsx": """import React from 'react';
import {
  Accordion, AccordionSummary, AccordionDetails, Typography, Box, Grid
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import type { V1DataOption } from "../../types";

interface Props {
  data: V1DataOption;
  expanded: string | false;
  handleChange: (panel: string) => (event: React.SyntheticEvent, isExpanded: boolean) => void;
}

export const CalculationSummarySection: React.FC<Props> = ({
  data, expanded, handleChange
}) => {
  return (
    <>
{CONTENT}
    </>
  );
};
""",
}


def save_file(name, content):
    val = templates[name].replace("{CONTENT}", content)
    with open(
        f"d:/kalk_v3/frontend/src/components/Calculator/{name}", "w", encoding="utf-8"
    ) as f:
        f.write(val)


save_file("VehicleDataSection.tsx", vdata)
save_file("OptionsTablesSection.tsx", opt_tables)
save_file("AdditionalOptionsSection.tsx", add_options)
save_file("CalculationSummarySection.tsx", calc_summary)
print("EXTRACTED")
