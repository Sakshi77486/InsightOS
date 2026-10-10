export default function ForecastChart({
  points,
  metricColumn,
  number,
  formatDate,
  shortDate,
}) {
  const cleanPoints = (points || [])
    .map((point) => ({
      date: point?.date,
      value: Number(point?.value),
    }))
    .filter(
      (point) =>
        point.date && Number.isFinite(point.value)
    );

  if (cleanPoints.length < 2) {
    return (
      <div className="chart-empty">
        Forecast chart will appear when future points are available.
      </div>
    );
  }

  const width = 900;
  const height = 300;
  const padX = 44;
  const padY = 30;
  const min = Math.min(...cleanPoints.map((point) => point.value));
  const max = Math.max(...cleanPoints.map((point) => point.value));
  const range = max - min || 1;

  const coordinates = cleanPoints.map((point, index) => ({
    ...point,
    x:
      padX +
      (index / (cleanPoints.length - 1)) *
        (width - padX * 2),
    y:
      height -
      padY -
      ((point.value - min) / range) *
        (height - padY * 2),
  }));

  const line = coordinates
    .map(
      (point, index) =>
        `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`
    )
    .join(" ");

  return (
    <div className="chart-shell">
      <div className="chart-topline">
        <div>
          <span>FORECAST</span>
          <strong>{metricColumn}</strong>
        </div>
        <small>{cleanPoints.length} future points</small>
      </div>

      <div className="chart-canvas">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label="Forecast chart"
        >
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
            d={line}
            className="chart-line forecast-line"
            fill="none"
          />

          {coordinates.map((point, index) => (
            <circle
              key={`${point.date}-${index}`}
              cx={point.x}
              cy={point.y}
              r="4"
              className="chart-point forecast-point"
            >
              <title>
                {`${formatDate(point.date)} · ${number(point.value)}`}
              </title>
            </circle>
          ))}

          {coordinates.map((point, index) => (
            <text
              key={`forecast-label-${index}`}
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
              {shortDate(point.date)}
            </text>
          ))}
        </svg>
      </div>
    </div>
  );
}
