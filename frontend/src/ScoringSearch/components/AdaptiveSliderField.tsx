import React, { useState, useRef, useEffect } from 'react';
import { TextField, InputAdornment, Tooltip } from '@mui/material';
import SwapHorizIcon from '@mui/icons-material/SwapHoriz';

interface AdaptiveSliderFieldProps {
  label: string;
  value: number;
  onChange: (val: number) => void;
  min?: number;
  max?: number;
}

export const AdaptiveSliderField: React.FC<AdaptiveSliderFieldProps> = ({
  label, value, onChange, min = 0, max = 100
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [dragValue, setDragValue] = useState(value);
  const [inputValue, setInputValue] = useState(value.toString());
  
  const isPointerDownRef = useRef(false);
  const didDragRef = useRef(false);
  const accumulatorRef = useRef(0);
  const lastTimeRef = useRef(0);
  const lastXRef = useRef(0);
  const startXRef = useRef(0);

  useEffect(() => {
    if (!isDragging) {
      setDragValue(value);
      setInputValue(value.toString());
    }
  }, [value, isDragging]);

  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return; // Only left click
    isPointerDownRef.current = true;
    didDragRef.current = false;
    startXRef.current = e.clientX;
    lastXRef.current = e.clientX;
    lastTimeRef.current = e.timeStamp;
    accumulatorRef.current = 0;
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!isPointerDownRef.current) return;

    // Detect if we crossed the threshold to start actually dragging
    if (!didDragRef.current) {
      if (Math.abs(e.clientX - startXRef.current) > 3) {
        didDragRef.current = true;
        setIsDragging(true);
        e.currentTarget.setPointerCapture(e.pointerId);
        if (document.activeElement instanceof HTMLElement) {
            document.activeElement.blur();
        }
      } else {
        return;
      }
    }

    const deltaX = e.clientX - lastXRef.current;
    const deltaTime = e.timeStamp - lastTimeRef.current;
    
    // Prevent divide by zero on ultra-fast consecutive events
    if (deltaTime === 0 && Math.abs(deltaX) === 0) return;

    const velocity = deltaTime > 0 ? Math.abs(deltaX / deltaTime) : 0; 
    
    // The visual multiplier (GEAR)
    // velocity is in px / ms
    let multiplier = 0.1;
    if (velocity > 1.2) {
      multiplier = 0.6; // High gear (large steps)
    } else if (velocity > 0.4) {
      multiplier = 0.2; // Medium gear
    } else if (velocity < 0.1) {
      multiplier = 0.02; // Low gear (micro precision zoooooom)
    }

    accumulatorRef.current += deltaX * multiplier;

    // Flush accumulator to value
    if (Math.abs(accumulatorRef.current) >= 0.1) {
      setDragValue((prev) => {
        let next = prev + accumulatorRef.current;
        if (min !== undefined) next = Math.max(min, next);
        if (max !== undefined) next = Math.min(max, next);
        next = Math.round(next * 100) / 100;
        setInputValue(next.toString());
        return next;
      });
      accumulatorRef.current = 0;
    }

    lastXRef.current = e.clientX;
    lastTimeRef.current = e.timeStamp;
  };

  const handlePointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    if (isPointerDownRef.current) {
      isPointerDownRef.current = false;
      if (didDragRef.current) {
        setIsDragging(false);
        e.currentTarget.releasePointerCapture(e.pointerId);
        // Commit on drag end
        onChange(dragValue);
      }
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
  };

  const handleInputBlur = () => {
    if (!isDragging) {
      let parsed = parseFloat(inputValue);
      if (isNaN(parsed)) parsed = value;
      if (min !== undefined) parsed = Math.max(min, parsed);
      if (max !== undefined) parsed = Math.min(max, parsed);
      setInputValue(parsed.toString());
      onChange(parsed);
    }
  };

  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.currentTarget.blur();
    }
  };

  return (
    <Tooltip 
      title="Złap i przeciągaj w boki myszką by zmieniać. Prędkość myszki zmienia precyzję (Zwolnij by dostroić dokładnie). Kliknij by wyedytować z palca." 
      placement="top" 
      disableInteractive
      enterDelay={400}
    >
      <TextField
        label={label}
        size="small"
        value={inputValue}
        onChange={handleInputChange}
        onBlur={handleInputBlur}
        onKeyDown={handleInputKeyDown}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        sx={{
          flex: 1,
          '& .MuiInputBase-root': {
            cursor: isDragging ? 'ew-resize' : 'text',
            userSelect: isDragging ? 'none' : 'auto',
            transition: 'background-color 0.2s',
            bgcolor: isDragging ? '#eff6ff' : 'transparent', 
            boxShadow: isDragging ? 'inset 0 0 0 1px #3b82f6' : 'none',
            // Prevents android/iOS pull to refresh when scrubbing
            touchAction: 'none'
          }
        }}
        InputProps={{
          endAdornment: (
            <InputAdornment position="end" sx={{ cursor: 'ew-resize', pointerEvents: 'none' }}>
              <SwapHorizIcon fontSize="small" color={isDragging ? 'primary' : 'action'} />
            </InputAdornment>
          )
        }}
      />
    </Tooltip>
  );
};
