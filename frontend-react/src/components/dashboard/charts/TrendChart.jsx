import { useMemo } from "react";
export default function TrendChart({
  rows,
  dateColumn,
  metricColumn,
  number,
  formatDate,
  shortDate,
}) {
  const points = useMemo(() => {
    return rows
      .map((row) => {
        const value = Number(row?.[metricColumn]);
        const rawDate = row?.[dateColumn];

        const time = new Date(
          /^\d{4}-\d{2}-\d{2}$/.test(String(rawDate || ""))
            ? `${rawDate}T00:00:00`
            : String(rawDate || "").replace(" ", "T")
        ).getTime();

        if (!Number.isFinite(value) || !Number.isFinite(time)) {
          return null;
        }

        return { value, time, rawDate };
      })
      .filter(Boolean)
      .sort((a, b) => a.time - b.time);
  }, [rows, dateColumn, metricColumn]);

  if (points.length < 2) {
    return (
      <div className="chart-empty">
        Not enough time-series data to draw this chart.
      </div>
    );
  }

  const width = 900;
  const height = 330;
  const padX = 44;
  const padY = 30;
  const min = Math.min(...points.map((point) => point.value));
  const max = Math.max(...points.map((point) => point.value));
  const range = max - min || 1;

  const coordinates = points.map((point, index) => {
    const x =
      padX +
      (index / (points.length - 1)) *
        (width - padX * 2);
    const y =
      height -
      padY -
      ((point.value - min) / range) *
        (height - padY * 2);

    return { ...point, x, y };
  });

  const line = coordinates
    .map(
      (point, index) =>
        `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`
    )
    .join(" ");

  const area = `${line} L ${coordinates.at(-1).x} ${
    height - padY
  } L ${coordinates[0].x} ${height - padY} Z`;

  const labelIndexes = new Set([
    0,
    Math.floor((points.length - 1) / 3),
    Math.floor(((points.length - 1) * 2) / 3),
    points.length - 1,
  ]);

  return (
    <div className="chart-shell">
      <div className="chart-topline">
        <div>
          <span>TIME SERIES</span>
          <strong>{metricColumn}</strong>
        </div>
        <small>{points.length} plotted points</small>
      </div>

      <div className="chart-canvas">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label={`${metricColumn} trend chart`}
        >
          <defs>
            <linearGradient
              id="insightArea"
              x1="0"
              y1="0"
              x2="0"
              y2="1"
            >
              <stop
                offset="0%"
                stopColor="rgba(214,174,78,0.28)"
              />
              <stop
                offset="100%"
                stopColor="rgba(214,174,78,0)"
              />
            </linearGradient>
          </defs>

          {[0, 1, 2, 3].map((step) => {
            const y =
              padY +
              (step / 3) * (height - padY * 2);

            return (
              <line
                key={step}
                x1={padX}
                x2={width - padX}
                y1={y}
                y2={y}
                className="chart-gridline"
              />
            );
          })}

          <path
            d={area}
            fill="url(#insightArea)"
            className="chart-area"
          />
          <path
            d={line}
            className="chart-line"
            fill="none"
          />

          {coordinates.map((point, index) => (
            <circle
              key={`${point.time}-${index}`}
              cx={point.x}
              cy={point.y}
              r={index === coordinates.length - 1 ? 5 : 3}
              className="chart-point"
            >
              <title>
                {`${formatDate(point.rawDate)} · ${number(point.value)}`}
              </title>
            </circle>
          ))}

          {coordinates.map((point, index) => {
            if (!labelIndexes.has(index)) return null;

            return (
              <text
                key={`label-${index}`}
                x={point.x}
                y={height - 8}
                textAnchor={
                  index === 0
                    ? "start"
                    : index === coordinates.length - 1
                    ? "end"
                    : "middle"
                }
                className="chart-axis-label"
              >
                {shortDate(point.rawDate)}
              </text>
            );
          })}
        </svg>
      </div>

      <div className="chart-range">
        <span>Min {number(min)}</span>
        <span>Max {number(max)}</span>
      </div>
    </div>
  );
}
