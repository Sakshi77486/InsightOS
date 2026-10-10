export default function AutoVisualization({ visualization, number }) {
  const chart = visualization?.data || {};
  const type = visualization?.type;

  if (!visualization) return null;

  if (type === "heatmap") {
    const columns = Array.isArray(chart.columns)
      ? chart.columns
      : [];

    const values = Array.isArray(chart.values)
      ? chart.values
      : [];

    if (!columns.length || !values.length) {
      return (
        <div className="auto-chart-empty">
          Correlation requires at least two numeric columns.
        </div>
      );
    }

    const getCellClass = (value) => {
      const n = Number(value);

      if (!Number.isFinite(n)) {
        return "heatmap-cell heatmap-neutral";
      }

      if (n >= 0.7) {
        return "heatmap-cell heatmap-strong-positive";
      }
      if (n >= 0.3) {
        return "heatmap-cell heatmap-positive";
      }
      if (n <= -0.7) {
        return "heatmap-cell heatmap-strong-negative";
      }
      if (n <= -0.3) {
        return "heatmap-cell heatmap-negative";
      }

      return "heatmap-cell heatmap-neutral";
    };

    return (
      <div className="auto-chart-card">
        <div className="auto-chart-header">
          <div>
            <span>AUTOMATIC VISUALIZATION</span>
            <h3>{visualization.title}</h3>
          </div>
          <small>Correlation matrix</small>
        </div>

        <div className="heatmap-wrap">
          <table className="heatmap-table">
            <thead>
              <tr>
                <th></th>
                {columns.map((column) => (
                  <th key={column}>{column}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {values.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  <th>{columns[rowIndex]}</th>
                  {row.map((value, columnIndex) => (
                    <td
                      key={columnIndex}
                      className={getCellClass(value)}
                    >
                      {Number.isFinite(Number(value))
                        ? Number(value).toFixed(2)
                        : "—"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  const xValues = Array.isArray(chart.x) ? chart.x : [];
  const yValues = Array.isArray(chart.y) ? chart.y : [];

  if (type === "histogram") {
    const values = xValues
      .map(Number)
      .filter(Number.isFinite);

    if (!values.length) {
      return (
        <div className="auto-chart-empty">
          Histogram requires numeric values.
        </div>
      );
    }

    const min = Math.min(...values);
    const max = Math.max(...values);
    const bucketCount = Math.min(
      12,
      Math.max(5, Math.ceil(Math.sqrt(values.length)))
    );
    const range = max - min || 1;
    const bucketSize = range / bucketCount;

    const buckets = Array.from(
      { length: bucketCount },
      (_, index) => ({
        start: min + index * bucketSize,
        end: min + (index + 1) * bucketSize,
        count: 0,
      })
    );

    values.forEach((value) => {
      let index = Math.floor((value - min) / bucketSize);
      if (index >= bucketCount) index = bucketCount - 1;
      buckets[index].count += 1;
    });

    const maxCount = Math.max(
      ...buckets.map((bucket) => bucket.count),
      1
    );

    return (
      <div className="auto-chart-card">
        <div className="auto-chart-header">
          <div>
            <span>AUTOMATIC VISUALIZATION</span>
            <h3>{visualization.title}</h3>
          </div>
          <small>{values.length} values</small>
        </div>

        <div className="histogram-chart">
          {buckets.map((bucket, index) => (
            <div className="histogram-column" key={index}>
              <div className="histogram-value">
                {bucket.count}
              </div>
              <div
                className="histogram-bar"
                style={{
                  height: `${Math.max(
                    8,
                    (bucket.count / maxCount) * 220
                  )}px`,
                }}
              />
              <span>{number(bucket.start)}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (type === "bar") {
    const points = xValues
      .map((xValue, index) => ({
        x: xValue,
        y: Number(yValues[index]),
      }))
      .filter((point) => Number.isFinite(point.y))
      .slice(0, 20);

    if (!points.length) {
      return (
        <div className="auto-chart-empty">
          Bar chart data is not available.
        </div>
      );
    }

    const maxValue = Math.max(
      ...points.map((point) => point.y),
      1
    );

    return (
      <div className="auto-chart-card">
        <div className="auto-chart-header">
          <div>
            <span>AUTOMATIC VISUALIZATION</span>
            <h3>{visualization.title}</h3>
          </div>
          <small>{points.length} categories</small>
        </div>

        <div className="auto-bar-chart">
          {points.map((point, index) => (
            <div
              className="auto-bar-item"
              key={`${point.x}-${index}`}
            >
              <span title={String(point.x)}>
                {point.x === null || point.x === undefined || point.x === ""
                  ? "Unknown"
                  : String(point.x)}
              </span>

              <div className="auto-bar-track">
                <div
                  className="auto-bar-fill"
                  style={{
                    width: `${Math.max(
                      2,
                      (point.y / maxValue) * 100
                    )}%`,
                  }}
                />
              </div>

              <div className="auto-bar-value">
                {number(point.y)}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (type === "line" || type === "scatter") {
    const points = xValues
      .map((xValue, index) => ({
        x: xValue,
        y: Number(yValues[index]),
      }))
      .filter((point) => Number.isFinite(point.y));

    if (!points.length) {
      return (
        <div className="auto-chart-empty">
          Visualization data is not available.
        </div>
      );
    }

    const numericY = points.map((point) => point.y);
    const minY = Math.min(...numericY);
    const maxY = Math.max(...numericY);
    const rangeY = maxY - minY || 1;

    const width = 900;
    const height = 320;
    const padX = 44;
    const padY = 30;

    const coordinates = points.map((point, index) => ({
      ...point,
      x:
        padX +
        (index / Math.max(points.length - 1, 1)) *
          (width - padX * 2),
      y:
        height -
        padY -
        ((point.y - minY) / rangeY) *
          (height - padY * 2),
    }));

    const line = coordinates
      .map(
        (point, index) =>
          `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`
      )
      .join(" ");

    const labelIndexes = new Set([
      0,
      Math.floor((points.length - 1) / 3),
      Math.floor(((points.length - 1) * 2) / 3),
      points.length - 1,
    ]);

    return (
      <div className="auto-chart-card">
        <div className="auto-chart-header">
          <div>
            <span>AUTOMATIC VISUALIZATION</span>
            <h3>{visualization.title}</h3>
          </div>
          <small>{points.length} points</small>
        </div>

        <div className="auto-chart-canvas">
          <svg
            viewBox={`0 0 ${width} ${height}`}
            role="img"
            aria-label={visualization.title}
          >
            {[0, 1, 2, 3].map((step) => {
              const gridY =
                padY +
                (step / 3) * (height - padY * 2);

              return (
                <line
                  key={step}
                  x1={padX}
                  x2={width - padX}
                  y1={gridY}
                  y2={gridY}
                  className="auto-chart-grid"
                />
              );
            })}

            {type === "line" && (
              <path
                d={line}
                className="auto-chart-line"
                fill="none"
              />
            )}

            {type === "scatter" &&
              coordinates.map((point, index) => (
                <circle
                  key={`scatter-${index}`}
                  cx={point.x}
                  cy={point.y}
                  r="4"
                  className="auto-chart-dot"
                >
                  <title>
                    {`${String(point.x)} · ${number(point.y)}`}
                  </title>
                </circle>
              ))}

            {type === "line" &&
              coordinates.map((point, index) => (
                <circle
                  key={`line-${index}`}
                  cx={point.x}
                  cy={point.y}
                  r={
                    index === coordinates.length - 1
                      ? 5
                      : 2.5
                  }
                  className="auto-chart-dot"
                >
                  <title>
                    {`${String(point.x)} · ${number(point.y)}`}
                  </title>
                </circle>
              ))}

            {coordinates.map((point, index) => {
              if (!labelIndexes.has(index)) return null;

              return (
                <text
                  key={`axis-${index}`}
                  x={point.x}
                  y={height - 8}
                  textAnchor={
                    index === 0
                      ? "start"
                      : index === coordinates.length - 1
                      ? "end"
                      : "middle"
                  }
                  className="auto-chart-axis"
                >
                  {String(point.x).slice(0, 16)}
                </text>
              );
            })}
          </svg>
        </div>

        <div className="auto-chart-range">
          <span>Min {number(minY)}</span>
          <span>Max {number(maxY)}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="auto-chart-empty">
      Unsupported visualization type.
    </div>
  );
}
