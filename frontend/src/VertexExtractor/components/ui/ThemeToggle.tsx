import { motion, AnimatePresence } from "framer-motion";
import { Box, Tooltip } from "@mui/material";

interface ThemeToggleProps {
  mode: "light" | "dark";
  onToggle: () => void;
}

export function ThemeToggle({ mode, onToggle }: ThemeToggleProps) {
  const isLight = mode === "light";

  return (
    <Tooltip title={isLight ? "Zgaś światło (Tryb Ciemny)" : "Zapal światło (Tryb Jasny)"}>
      <Box
        onClick={onToggle}
        sx={{
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          width: 48,
          height: 48,
          position: "relative",
          userSelect: "none",
          "&:hover .candle-body": {
            filter: "brightness(1.1)",
          },
        }}
      >
        <svg
          width="32"
          height="40"
          viewBox="0 0 32 40"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Candlestick Base */}
          <rect x="8" y="34" width="16" height="4" rx="2" fill={isLight ? "#94a3b8" : "#475569"} />
          
          {/* Candle Wax Body */}
          <motion.rect
            className="candle-body"
            x="11"
            y="18"
            width="10"
            height="18"
            rx="1"
            initial={false}
            animate={{
              fill: isLight ? "#f1f5f9" : "#334155",
            }}
            transition={{ duration: 0.3 }}
          />

          {/* Wick */}
          <rect x="15" y="15" width="2" height="4" fill="#1e293b" />

          {/* Flame */}
          <AnimatePresence>
            {isLight && (
              <motion.g
                initial={{ scale: 0, opacity: 0, y: 5 }}
                animate={{ scale: 1, opacity: 1, y: 0 }}
                exit={{ scale: 0, opacity: 0, y: 5 }}
                transition={{ type: "spring", stiffness: 300, damping: 20 }}
              >
                {/* Glow */}
                <motion.circle
                  cx="16"
                  cy="12"
                  r="8"
                  fill="url(#flame-glow)"
                  animate={{
                    scale: [1, 1.2, 1],
                    opacity: [0.3, 0.5, 0.3],
                  }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
                {/* Core Flame */}
                <motion.path
                  d="M16 4C16 4 11 10 11 13C11 15.7614 13.2386 18 16 18C18.7614 18 21 15.7614 21 13C21 10 16 4 16 4Z"
                  fill="#fbbf24"
                  animate={{
                    scaleY: [1, 1.1, 1],
                    rotate: [-2, 2, -2],
                  }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                />
                {/* Inner Flame */}
                <path
                  d="M16 8C16 8 13.5 11.5 13.5 13.5C13.5 14.8807 14.6193 16 16 16C17.3807 16 18.5 14.8807 18.5 13.5C18.5 11.5 16 8 16 8Z"
                  fill="#f59e0b"
                />
              </motion.g>
            )}
          </AnimatePresence>

          <defs>
            <radialGradient id="flame-glow" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(16 12) rotate(90) scale(12)">
              <stop stopColor="#fcd34d" stopOpacity="0.8" />
              <stop offset="1" stopColor="#fcd34d" stopOpacity="0" />
            </radialGradient>
          </defs>
        </svg>

        {/* Ambient Light Effect in Header */}
        {isLight && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            style={{
              position: "absolute",
              top: "50%",
              left: "50%",
              width: "100px",
              height: "100px",
              background: "radial-gradient(circle, rgba(251, 191, 36, 0.15) 0%, rgba(251, 191, 36, 0) 70%)",
              borderRadius: "50%",
              transform: "translate(-50%, -50%)",
              pointerEvents: "none",
              zIndex: -1,
            }}
          />
        )}
      </Box>
    </Tooltip>
  );
}
