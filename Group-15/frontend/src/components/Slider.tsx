import { useState } from 'react';

interface SliderProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  min: number;
  max: number;
  unit?: string;
  step?: number;
}

export default function Slider({ label, value, onChange, min, max, unit = 'px', step = 1 }: SliderProps) {
  const numericValue = parseFloat(value) || min;
  const [localValue, setLocalValue] = useState(numericValue);

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = parseFloat(e.target.value);
    setLocalValue(newValue);
    onChange(`${newValue}${unit}`);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    const parsed = parseFloat(newValue);
    if (!isNaN(parsed)) {
      setLocalValue(parsed);
      onChange(`${parsed}${unit}`);
    }
  };

  return (
    <div className="slider-control">
      <div className="slider-header">
        <label>{label}</label>
        <input
          type="number"
          className="slider-input"
          value={localValue}
          onChange={handleInputChange}
          min={min}
          max={max}
          step={step}
        />
        <span className="slider-unit">{unit}</span>
      </div>
      <input
        type="range"
        className="slider-range"
        value={localValue}
        onChange={handleSliderChange}
        min={min}
        max={max}
        step={step}
      />
    </div>
  );
}
