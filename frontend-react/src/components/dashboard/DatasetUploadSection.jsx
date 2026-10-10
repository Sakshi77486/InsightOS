import { useRef } from "react";

export default function DatasetUploadSection({
  dataset,
  uploading,
  processingStep,
  uploadError,
  handleDatasetUpload,
}) {
  const fileInputRef = useRef(null);

  return (
    <section className="dashboard-upload">
      <div>
        <span className="dashboard-eyebrow">
          DATA SOURCE
        </span>

        <h2>
          {dataset
            ? "Replace or analyze another dataset"
            : "Upload your first dataset"}
        </h2>

        <p>
          Upload CSV, XLSX, XLS or JSON. InsightOS
          automatically processes the complete dataset
          pipeline.
        </p>
      </div>

      <label className="upload-button">
        {uploading
          ? "Processing..."
          : dataset
          ? "Replace dataset"
          : "Upload dataset"}

        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx,.xls,.json"
          onChange={handleDatasetUpload}
          disabled={uploading}
          hidden
        />
      </label>

      {uploading && (
        <div className="dashboard-processing">
          <span className="processing-dot" />
          {processingStep}
        </div>
      )}

      {uploadError && (
        <div className="dashboard-upload-error">
          {uploadError}
        </div>
      )}
    </section>
  );
}