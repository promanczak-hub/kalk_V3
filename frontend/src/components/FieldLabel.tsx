import React from 'react';
import { Typography } from "@mui/material";

interface FieldLabelProps {
  label: string;
  mock?: boolean;
}

export const FieldLabel: React.FC<FieldLabelProps> = ({
  label,
  mock = false,
}) => (
  <Typography
    align="right"
    variant="body2"
    sx={{ pr: 2, fontSize: "0.8rem", color: "#333" }}
  >
    {label}{" "}
    {mock && <span style={{ color: "red", fontWeight: "bold" }}>!</span>}
  </Typography>
);
