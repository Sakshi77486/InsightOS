export default function ObjectPreview({
  data,
  depth = 0,
  label,
}) {
  if (
    data === null ||
    data === undefined ||
    typeof data === "string" ||
    typeof data === "number" ||
    typeof data === "boolean"
  ) {
    return (
      <span className="inline-value">
        {data === null || data === undefined
          ? "—"
          : String(data)}
      </span>
    );
  }

  if (Array.isArray(data)) {
    if (!data.length) {
      return <span className="muted">No data.</span>;
    }

    const objectRows = data.filter(
      (item) =>
        item &&
        typeof item === "object" &&
        !Array.isArray(item)
    );

    if (objectRows.length) {
      const keys = [
        ...new Set(
          objectRows.flatMap((item) =>
            Object.keys(item)
          )
        ),
      ].slice(0, 8);

      return (
        <div className="data-table-wrap compact-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                {keys.map((key) => (
                  <th key={key}>{label(key)}</th>
                ))}
              </tr>
            </thead>

            <tbody>
              {data.slice(0, 25).map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {keys.map((key) => (
                    <td key={key}>
                      {row?.[key] &&
                      typeof row[key] === "object"
                        ? JSON.stringify(row[key])
                        : String(row?.[key] ?? "—")}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }

    return (
      <div className="simple-list">
        {data.slice(0, 25).map((item, index) => (
          <div
            className="simple-list-item"
            key={index}
          >
            {item && typeof item === "object"
              ? JSON.stringify(item)
              : String(item)}
          </div>
        ))}
      </div>
    );
  }

  const entries = Object.entries(data);

  if (!entries.length) {
    return <span className="muted">No data.</span>;
  }

  return (
    <div
      className={`object-grid depth-${Math.min(
        depth,
        3
      )}`}
    >
      {entries.map(([key, value]) => (
        <div className="object-item" key={key}>
          <span>{label(key)}</span>

          <div>
            {value && typeof value === "object" ? (
              <ObjectPreview
                data={value}
                depth={depth + 1}
                label={label}
              />
            ) : (
              <strong>
                {value === null ||
                value === undefined ||
                value === ""
                  ? "—"
                  : String(value)}
              </strong>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}