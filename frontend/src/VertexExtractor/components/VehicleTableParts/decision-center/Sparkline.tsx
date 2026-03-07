/**
 * Sparkline — minimalistyczny SVG wykres liniowy.
 * Renderuje trend z tablicy wartości numerycznych.
 */

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  strokeColor?: string;
  fillColor?: string;
}

export function Sparkline({
  data,
  width = 64,
  height = 24,
  strokeColor = "rgba(255,255,255,0.8)",
  fillColor = "rgba(255,255,255,0.1)",
}: SparklineProps) {
  if (data.length < 2) return null;

  const padding = 2;
  const w = width - padding * 2;
  const h = height - padding * 2;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const points = data.map((v, i) => {
    const x = padding + (i / (data.length - 1)) * w;
    const y = padding + h - ((v - min) / range) * h;
    return `${x},${y}`;
  });

  const polyline = points.join(" ");

  // Fill area (polygon closing to bottom)
  const firstX = padding;
  const lastX = padding + w;
  const bottomY = padding + h;
  const fillPolygon = `${firstX},${bottomY} ${polyline} ${lastX},${bottomY}`;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="inline-block align-middle ml-2"
    >
      {/* Fill area */}
      <polygon points={fillPolygon} fill={fillColor} />
      {/* Line */}
      <polyline
        points={polyline}
        fill="none"
        stroke={strokeColor}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* End dot */}
      {data.length > 0 && (
        <circle
          cx={padding + w}
          cy={padding + h - ((data[data.length - 1] - min) / range) * h}
          r="2"
          fill={strokeColor}
        />
      )}
    </svg>
  );
}
