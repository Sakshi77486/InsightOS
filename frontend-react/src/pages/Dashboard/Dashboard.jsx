import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";

import DatasetUploadSection from "../../components/dashboard/DatasetUploadSection";
import VisualizationSection from "../../components/dashboard/VisualizationSection";

import TrendChart from "../../components/dashboard/charts/TrendChart";
import ForecastChart from "../../components/dashboard/charts/ForecastChart";
import ObjectPreview from "../../components/dashboard/charts/ObjectPreview";

import "./Dashboard.css";

const API = "http://127.0.0.1:8000/api";

function number(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return "—";
  }

  const n = Number(value);

  if (!Number.isFinite(n)) {
    return String(value);
  }

  return n.toLocaleString(undefined, {
    maximumFractionDigits: 2,
  });
}

function formatDate(value) {
  if (!value) return "—";

  const raw = String(value).trim();

  const safeValue =
    /^\d{4}-\d{2}-\d{2}$/.test(raw)
      ? `${raw}T00:00:00`
      : raw.replace(" ", "T");

  const d = new Date(safeValue);

  if (Number.isNaN(d.getTime())) {
    return raw;
  }

  return d.toLocaleDateString(undefined, {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function shortDate(value) {
  if (!value) return "";

  const raw = String(value).trim();

  const safeValue =
    /^\d{4}-\d{2}-\d{2}$/.test(raw)
      ? `${raw}T00:00:00`
      : raw.replace(" ", "T");

  const d = new Date(safeValue);

  if (Number.isNaN(d.getTime())) {
    return raw;
  }

  return d.toLocaleDateString(undefined, {
    day: "2-digit",
    month: "short",
  });
}

function label(value) {
  return String(value ?? "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function unwrap(data, key) {
  if (!data) return {};

  if (
    key &&
    data[key] !== undefined
  ) {
    return data[key];
  }

  return data;
}

function normalizeList(value) {
  if (Array.isArray(value)) {
    return value;
  }

  if (
    !value ||
    typeof value !== "object"
  ) {
    return [];
  }

  for (const key of [
    "anomalies",
    "records",
    "items",
    "points",
    "rows",
    "data",
  ]) {
    if (Array.isArray(value[key])) {
      return value[key];
    }
  }

  return [];
}

function parseObject(value) {
  if (
    value &&
    typeof value === "object"
  ) {
    return value;
  }

  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);

      return parsed &&
        typeof parsed === "object"
        ? parsed
        : {};
    } catch {
      return {};
    }
  }

  return {};
}

function extractAiInsight(data) {
  if (!data) return "";

  if (typeof data === "string") {
    return data;
  }

  const direct =
    data.ai_insight ||
    data.aiInsight ||
    data.insight ||
    data.latest_insight;

  if (
    typeof direct === "string" &&
    direct.trim()
  ) {
    return direct;
  }

  const candidates = [
    data.ai?.insight,
    data.result?.ai_insight,
    data.result?.insight,
    data.result?.aiInsight,
    data.result?.ai?.insight,
    data.latest_run?.result?.ai_insight,
    data.latest_run?.result?.insight,
    data.latestRun?.result?.ai_insight,
    data.latestRun?.result?.insight,
    data.analysis?.ai_insight,
    data.analysis?.insight,
  ];

  return (
    candidates.find(
      (item) =>
        typeof item === "string" &&
        item.trim()
    ) || ""
  );
}

function getReportId(data) {
  if (!data) return null;

  const candidates = [
    data.report_id,
    data.reportId,
    data.report?.id,
    data.result?.report_id,
    data.result?.reportId,
    data.result?.report?.id,
    data.latest_report?.id,
    data.latestReport?.id,
  ];

  return (
    candidates.find(
      (value) =>
        value !== null &&
        value !== undefined
    ) || null
  );
}

function normalizeUploadedDataset(dataset) {
  if (
    !dataset ||
    typeof dataset !== "object"
  ) {
    return null;
  }

  return {
    ...dataset,
    id: dataset.id,
    name: dataset.name,

    rows:
      dataset.rows ??
      dataset.row_count ??
      0,

    columns:
      dataset.columns ??
      dataset.column_count ??
      0,

    format:
      dataset.format ??
      dataset.source_format ??
      "—",

    row_count:
      dataset.row_count ??
      dataset.rows ??
      0,

    column_count:
      dataset.column_count ??
      dataset.columns ??
      0,

    source_type:
      dataset.source_type ??
      "upload",

    source_format:
      dataset.source_format ??
      dataset.format ??
      "—",
  };
}

function getMetricAndDate(
  analytics,
  columns,
  rows
) {
  let dateColumn =
    analytics?.datetime_columns?.[0] ||
    null;

  let metricColumn =
    analytics?.numeric_columns?.[0] ||
    null;

  if (
    !dateColumn &&
    rows.length
  ) {
    dateColumn =
      columns.find((column) => {
        const sample = rows
          .slice(0, 12)
          .map(
            (row) => row?.[column]
          )
          .filter(
            (value) =>
              value !== null &&
              value !== undefined &&
              value !== ""
          );

        if (sample.length < 2) {
          return false;
        }

        return (
          sample.filter(
            (value) =>
              !Number.isNaN(
                new Date(
                  String(value)
                ).getTime()
              )
          ).length >= 2
        );
      }) || null;
  }

  if (
    !metricColumn &&
    rows.length
  ) {
    metricColumn =
      columns.find((column) => {
        const values = rows
          .map((row) =>
            Number(
              row?.[column]
            )
          )
          .filter((value) =>
            Number.isFinite(value)
          );

        return values.length >= 4;
      }) || null;
  }

  return {
    dateColumn,
    metricColumn,
  };
}

function getStatistics(analytics) {
  return (
    analytics?.statistics ||
    analytics?.stats ||
    analytics?.numeric_statistics ||
    {}
  );
}

function getPrimaryStats(
  analytics,
  metricColumn
) {
  const statistics =
    getStatistics(analytics);

  if (
    !statistics ||
    typeof statistics !== "object"
  ) {
    return null;
  }

  if (
    metricColumn &&
    statistics[metricColumn]
  ) {
    return statistics[metricColumn];
  }

  const firstKey = Object.keys(
    statistics
  ).find(
    (key) =>
      statistics[key] &&
      typeof statistics[key] ===
        "object"
  );

  return firstKey
    ? statistics[firstKey]
    : null;
}

function getTrend(
  analytics,
  metricColumn
) {
  const trends =
    analytics?.trend ||
    analytics?.trends ||
    {};

  if (
    !trends ||
    typeof trends !== "object"
  ) {
    return {};
  }

  if (
    metricColumn &&
    trends[metricColumn]
  ) {
    return trends[metricColumn];
  }

  const firstKey = Object.keys(
    trends
  ).find(
    (key) =>
      trends[key] &&
      typeof trends[key] === "object"
  );

  return firstKey
    ? trends[firstKey]
    : trends;
}

function getPrimaryAnomalyMetric(
  item,
  metricColumn
) {
  const details = parseObject(
    item?.details
  );

  if (
    metricColumn &&
    details[metricColumn] &&
    typeof details[metricColumn] ===
      "object"
  ) {
    const data =
      details[metricColumn];

    return {
      metric: metricColumn,
      value: data.value,
      deviation:
        data.deviation_percentage,
      zScore: data.z_score,
      type: data.type,
    };
  }

  const entries =
    Object.entries(
      details
    ).filter(
      ([, value]) =>
        value &&
        typeof value === "object" &&
        Number.isFinite(
          Number(
            value.z_score
          )
        )
    );

  if (!entries.length) {
    return null;
  }

  entries.sort(
    (a, b) =>
      Math.abs(
        Number(
          b[1].z_score
        )
      ) -
      Math.abs(
        Number(
          a[1].z_score
        )
      )
  );

  const [
    metric,
    data,
  ] = entries[0];

  return {
    metric,
    value: data.value,
    deviation:
      data.deviation_percentage,
    zScore: data.z_score,
    type: data.type,
  };
}

function buildAnomalyRows(
  anomalies,
  metricColumn
) {
  return anomalies.map(
    (item, index) => {
      const record =
        parseObject(
          item?.record
        );

      const strongest =
        getPrimaryAnomalyMetric(
          item,
          metricColumn
        );

      const fallbackType =
        item?.type ||
        item?.anomaly_type ||
        (Number(
          strongest?.zScore
        ) < 0
          ? "low"
          : "high");

      return {
        id:
          item?.id ?? index,

        date:
          record.Date || "—",

        region:
          record.Region || "—",

        product:
          record.Product || "—",

        channel:
          record.Channel || "—",

        sales:
          record.Sales ?? "—",

        orders:
          record.Orders ?? "—",

        customers:
          record.Customers ?? "—",

        returns:
          record.Returns ?? "—",

        discount:
          record.Discount_Pct ??
          "—",

        profit:
          record.Profit ?? "—",

        metric:
          strongest?.metric ||
          metricColumn ||
          "—",

        value:
          strongest?.value ?? "—",

        type:
          strongest?.type ||
          fallbackType,

        deviation:
          Number.isFinite(
            Number(
              strongest?.deviation
            )
          )
            ? `${Number(
                strongest.deviation
              ).toFixed(2)}%`
            : "—",

        zScore:
          Number.isFinite(
            Number(
              strongest?.zScore
            )
          )
            ? Number(
                strongest.zScore
              ).toFixed(2)
            : "—",

        anomalyScore:
          Number.isFinite(
            Number(
              item?.anomaly_score
            )
          )
            ? Number(
                item.anomaly_score
              ).toFixed(4)
            : "—",
      };
    }
  );
}

function getAnomalyCounts(rows) {
  return rows.reduce(
    (counts, row) => {
      const type =
        String(
          row.type || ""
        ).toLowerCase();

      if (type === "low") {
        counts.low += 1;
      }

      if (type === "high") {
        counts.high += 1;
      }

      return counts;
    },
    {
      low: 0,
      high: 0,
    }
  );
}

export default function Dashboard() {
  const {
    projectId,
  } = useParams();

  const navigate =
    useNavigate();

  const fileInputRef =
    useRef(null);

  const [
    project,
    setProject,
  ] = useState(null);

  const [
    overview,
    setOverview,
  ] = useState(null);

  const [
    datasets,
    setDatasets,
  ] = useState([]);

  const [
    activeDataset,
    setActiveDataset,
  ] = useState(null);

  const [
    analytics,
    setAnalytics,
  ] = useState({});

  const [
    profile,
    setProfile,
  ] = useState([]);

  const [
    anomalies,
    setAnomalies,
  ] = useState([]);

  const [
    previewColumns,
    setPreviewColumns,
  ] = useState([]);

  const [
    previewRows,
    setPreviewRows,
  ] = useState([]);

  const [
    aiInsight,
    setAiInsight,
  ] = useState("");

  const [
    reportId,
    setReportId,
  ] = useState(null);

  const [
    visualizations,
    setVisualizations,
  ] = useState([]);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    detailsLoading,
    setDetailsLoading,
  ] = useState(false);

  const [
    uploading,
    setUploading,
  ] = useState(false);

  const [
    processingStep,
    setProcessingStep,
  ] = useState("");

  const [
    error,
    setError,
  ] = useState("");

  const [
    uploadError,
    setUploadError,
  ] = useState("");

  const [
    question,
    setQuestion,
  ] = useState("");

  const [
    chatMessages,
    setChatMessages,
  ] = useState([]);

  const [
    chatLoading,
    setChatLoading,
  ] = useState(false);

  const token =
    localStorage.getItem(
      "access_token"
    );

  const kpis =
    overview?.kpis || {};

  const forecast =
    overview?.forecast || {};

  const dataset =
    activeDataset ||
    overview?.dataset ||
    null;

  const growth =
    kpis.growth_pct;

  const growthText =
    growth === null ||
    growth === undefined
      ? "—"
      : `${growth > 0 ? "+" : ""}${growth}%`;

  const normalizedAnomalies =
    useMemo(
      () =>
        normalizeList(
          anomalies
        ),
      [anomalies]
    );

  const {
    dateColumn,
    metricColumn,
  } = useMemo(
    () =>
      getMetricAndDate(
        analytics,
        previewColumns,
        previewRows
      ),
    [
      analytics,
      previewColumns,
      previewRows,
    ]
  );

  const primaryStats =
    useMemo(
      () =>
        getPrimaryStats(
          analytics,
          metricColumn
        ),
      [
        analytics,
        metricColumn,
      ]
    );

  const trend =
    useMemo(
      () =>
        getTrend(
          analytics,
          metricColumn
        ),
      [
        analytics,
        metricColumn,
      ]
    );

  const anomalyRows =
    useMemo(
      () =>
        buildAnomalyRows(
          normalizedAnomalies,
          metricColumn
        ),
      [
        normalizedAnomalies,
        metricColumn,
      ]
    );

  const anomalyCounts =
    useMemo(
      () =>
        getAnomalyCounts(
          anomalyRows
        ),
      [anomalyRows]
    );

  const qualityScore =
    useMemo(() => {
      const records =
        Number(
          kpis.records || 0
        );

      const missing =
        Number(
          kpis.missing_values ||
            0
        );

      const duplicate =
        Number(
          kpis.duplicate_rows ||
            0
        );

      if (!records) {
        return null;
      }

      const missingRate =
        Math.min(
          100,
          (missing / records) *
            100
        );

      const duplicateRate =
        Math.min(
          100,
          (duplicate /
            records) *
            100
        );

      return Math.max(
        0,
        100 -
          missingRate *
            0.6 -
          duplicateRate *
            0.4
      );
    }, [kpis]);

  async function requestJSON(
    url,
    options = {}
  ) {
    const response =
      await fetch(
        url,
        {
          ...options,
          headers: {
            Authorization: `Bearer ${token}`,
            ...(options.headers ||
              {}),
          },
        }
      );

    const data =
      await response
        .json()
        .catch(
          () => ({})
        );

    if (
      response.status ===
      401
    ) {
      localStorage.removeItem(
        "access_token"
      );

      localStorage.removeItem(
        "user"
      );

      navigate("/login", {
        replace: true,
      });

      throw new Error(
        "Session expired."
      );
    }

    if (!response.ok) {
      throw new Error(
        data.detail ||
          data.message ||
          "Request failed."
      );
    }

    return data;
  }

  async function loadDatasetDetails(
    datasetId
  ) {
    if (!datasetId) {
      return;
    }

    setDetailsLoading(
      true
    );

    try {
      const results =
        await Promise.allSettled(
          [
            requestJSON(
              `${API}/datasets/${datasetId}/analytics`
            ),
            requestJSON(
              `${API}/datasets/${datasetId}/columns`
            ),
            requestJSON(
              `${API}/datasets/${datasetId}/anomalies`
            ),
            requestJSON(
              `${API}/datasets/${datasetId}/preview?limit=100`
            ),
            requestJSON(
              `${API}/datasets/${datasetId}/ai-insight/latest`
            ),
            requestJSON(
              `${API}/datasets/${datasetId}/latest-report`
            ),
            requestJSON(
              `${API}/datasets/${datasetId}/visualizations/auto`
            ),
          ]
        );

      const [
        analyticsResult,
        profileResult,
        anomaliesResult,
        previewResult,
        aiResult,
        reportResult,
        visualizationsResult,
      ] = results;

      if (
        analyticsResult.status ===
        "fulfilled"
      ) {
        setAnalytics(
          unwrap(
            analyticsResult.value,
            "analytics"
          )
        );
      }

      if (
        profileResult.status ===
        "fulfilled"
      ) {
        setProfile(
          unwrap(
            profileResult.value,
            "columns"
          )
        );
      }

      if (
        anomaliesResult.status ===
        "fulfilled"
      ) {
        setAnomalies(
          anomaliesResult.value
        );
      }

      if (
        previewResult.status ===
        "fulfilled"
      ) {
        const preview =
          previewResult.value;

        setPreviewColumns(
          Array.isArray(
            preview.columns
          )
            ? preview.columns
            : []
        );

        setPreviewRows(
          Array.isArray(
            preview.rows
          )
            ? preview.rows
            : []
        );
      }

      if (
        aiResult.status ===
        "fulfilled"
      ) {
        const insight =
          extractAiInsight(
            aiResult.value
          );

        if (insight) {
          setAiInsight(
            insight
          );
        }
      }

      if (
        reportResult.status ===
        "fulfilled"
      ) {
        const id =
          getReportId(
            reportResult.value
          );

        if (id) {
          setReportId(id);
        }
      }

      if (
        visualizationsResult.status ===
        "fulfilled"
      ) {
        const items =
          visualizationsResult
            .value
            ?.visualizations;

        setVisualizations(
          Array.isArray(items)
            ? items
            : []
        );
      } else {
        setVisualizations([]);
      }
    } finally {
      setDetailsLoading(
        false
      );
    }
  }

  async function loadDashboard() {
    try {
      setLoading(true);
      setError("");

      const [
        projectData,
        overviewData,
        datasetsData,
      ] = await Promise.all([
        requestJSON(
          `${API}/projects/${projectId}`
        ),
        requestJSON(
          `${API}/projects/${projectId}/overview`
        ),
        requestJSON(
          `${API}/projects/${projectId}/datasets`
        ),
      ]);

      setProject(
        projectData
      );

      const list =
        Array.isArray(
          datasetsData
        )
          ? datasetsData
          : datasetsData?.datasets ||
            [];

      const normalizedList =
        list
          .map(
            normalizeUploadedDataset
          )
          .filter(
            (item) =>
              item?.id
          );

      setDatasets(
        normalizedList
      );

      const overviewDataset =
        normalizeUploadedDataset(
          overviewData?.dataset
        );

      const activeId =
        overviewDataset?.id ||
        normalizedList[0]
          ?.id ||
        null;

      const selectedDataset =
        overviewDataset ||
        normalizedList.find(
          (item) =>
            item.id ===
            activeId
        ) ||
        null;

      setActiveDataset(
        selectedDataset
      );

      setOverview({
        ...(overviewData ||
          {}),
        dataset:
          selectedDataset,
      });

      if (activeId) {
        await loadDatasetDetails(
          activeId
        );
      } else {
        setAnalytics({});
        setProfile([]);
        setAnomalies([]);
        setPreviewColumns([]);
        setPreviewRows([]);
        setAiInsight("");
        setReportId(null);
        setVisualizations([]);
      }
    } catch (err) {
      setError(
        err.message ||
          "Unable to load dashboard."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!token) {
      navigate("/login", {
        replace: true,
      });
      return;
    }

    loadDashboard();

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function pollAnalysisRun(
    projectIdValue,
    runId,
    datasetId
  ) {
    const maxAttempts = 150;

    for (
      let attempt = 0;
      attempt < maxAttempts;
      attempt += 1
    ) {
      try {
        const statusData =
          await requestJSON(
            `${API}/projects/${projectIdValue}/runs/${runId}`
          );

        const result =
          statusData?.result ||
          {};

        if (
          result.analytics
        ) {
          setAnalytics(
            result.analytics
          );
        }

        if (
          result.anomalies
        ) {
          setAnomalies(
            result.anomalies
          );
        }

        if (
          result.forecast
        ) {
          setOverview(
            (previous) => ({
              ...(previous ||
                {}),
              forecast:
                result.forecast,
            })
          );
        }

        const insight =
          extractAiInsight(
            result
          );

        if (insight) {
          setAiInsight(
            insight
          );
        }

        const completedReportId =
          getReportId(
            result
          );

        if (
          completedReportId
        ) {
          setReportId(
            completedReportId
          );
        }

        if (
          statusData.status ===
          "completed"
        ) {
          setProcessingStep(
            "Refreshing AI and report results..."
          );

          await loadDatasetDetails(
            datasetId
          );

          setProcessingStep(
            ""
          );

          return;
        }

        if (
          statusData.status ===
          "failed"
        ) {
          setUploadError(
            result.error ||
              "Background AI/report processing failed."
          );

          setProcessingStep(
            ""
          );

          return;
        }
      } catch (err) {
        console.error(
          "Analysis status error:",
          err
        );
      }

      await new Promise(
        (resolve) =>
          setTimeout(
            resolve,
            2000
          )
      );
    }

    setProcessingStep("");

    setUploadError(
      "Analysis is still running in the background. Refresh later to see the completed AI insight and report."
    );
  }

  async function handleDatasetUpload(
    event
  ) {
    const file =
      event.target.files?.[0];

    event.target.value = "";

    if (!file) return;

    setUploading(true);
    setUploadError("");
    setAiInsight("");
    setReportId(null);
    setAnalytics({});
    setAnomalies([]);
    setProfile([]);
    setPreviewColumns([]);
    setPreviewRows([]);
    setVisualizations([]);

    setProcessingStep(
      "Uploading dataset..."
    );

    try {
      const formData =
        new FormData();

      formData.append(
        "file",
        file
      );

      const uploadData =
        await requestJSON(
          `${API}/datasets/upload?project_id=${projectId}`,
          {
            method: "POST",
            body: formData,
          }
        );

      const uploadedDataset =
        normalizeUploadedDataset(
          uploadData?.dataset
        );

      const datasetId =
        uploadedDataset?.id ||
        uploadData?.dataset_id;

      if (!datasetId) {
        throw new Error(
          "Upload succeeded but no dataset ID was returned."
        );
      }

      const activeUploadedDataset =
        uploadedDataset || {
          id: datasetId,
          name: file.name,
          rows: 0,
          columns: 0,
          format:
            file.name
              .split(".")
              .pop()
              ?.toUpperCase() ||
            "—",
          row_count: 0,
          column_count: 0,
          source_type:
            "upload",
          source_format:
            file.name
              .split(".")
              .pop()
              ?.toUpperCase() ||
            "—",
        };

      setActiveDataset(
        activeUploadedDataset
      );

      setOverview(
        (previous) => ({
          ...(previous || {}),
          dataset:
            activeUploadedDataset,
        })
      );

      setDatasets(
        (previous) => [
          activeUploadedDataset,
          ...previous.filter(
            (item) =>
              item.id !==
              datasetId
          ),
        ]
      );

      setProcessingStep(
        "Running analytics..."
      );

      const analysisData =
        await requestJSON(
          `${API}/projects/${projectId}/auto-analyze/${datasetId}`,
          {
            method: "POST",
          }
        );

      const result =
        analysisData?.result ||
        {};

      const runId =
        analysisData?.run_id;

      if (
        result.analytics
      ) {
        setAnalytics(
          result.analytics
        );
      }

      if (
        result.anomalies
      ) {
        setAnomalies(
          result.anomalies
        );
      }

      if (
        result.forecast
      ) {
        setOverview(
          (previous) => ({
            ...(previous ||
              {}),
            dataset:
              activeUploadedDataset,
            forecast:
              result.forecast,
          })
        );
      }

      try {
        const latestOverview =
          await requestJSON(
            `${API}/projects/${projectId}/overview`
          );

        setOverview(
          (previous) => ({
            ...(latestOverview ||
              {}),
            dataset:
              activeUploadedDataset,
            forecast:
              latestOverview?.forecast ||
              previous?.forecast ||
              result.forecast ||
              {},
          })
        );
      } catch (
        overviewError
      ) {
        console.error(
          "Overview refresh error:",
          overviewError
        );
      }

      setProcessingStep("");
      setUploading(false);

      if (runId) {
        void pollAnalysisRun(
          projectId,
          runId,
          datasetId
        );
      }
    } catch (err) {
      setUploadError(
        err.message ||
          "Dataset processing failed."
      );

      setProcessingStep("");
      setUploading(false);
    }
  }

  async function handleChatSubmit(
    event
  ) {
    event.preventDefault();

    const text =
      question.trim();

    const activeDatasetId =
      dataset?.id ||
      datasets[0]?.id;

    if (
      !text ||
      !activeDatasetId ||
      chatLoading
    ) {
      return;
    }

    setQuestion("");

    setChatMessages(
      (previous) => [
        ...previous,
        {
          role: "user",
          text,
        },
      ]
    );

    setChatLoading(true);

    try {
      const data =
        await requestJSON(
          `${API}/datasets/${activeDatasetId}/chat?question=${encodeURIComponent(text)}`,
          {
            method: "POST",
          }
        );

      setChatMessages(
        (previous) => [
          ...previous,
          {
            role: "assistant",
            text:
              data.answer ||
              "No answer was returned.",
          },
        ]
      );
    } catch (err) {
      setChatMessages(
        (previous) => [
          ...previous,
          {
            role: "assistant",
            text:
              err.message ||
              "Unable to answer this question.",
          },
        ]
      );
    } finally {
      setChatLoading(false);
    }
  }

  function logout() {
    localStorage.removeItem(
      "access_token"
    );

    localStorage.removeItem(
      "user"
    );

    navigate("/login", {
      replace: true,
    });
  }

  if (loading) {
    return (
      <main className="dashboard-page">
        <div className="dashboard-loading">
          Loading analytics workspace...
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="dashboard-page">
        <header className="dashboard-header">
          <Link
            to="/projects"
            className="dashboard-brand"
          >
            Insight<span>OS</span>
          </Link>

          <button onClick={logout}>
            Logout
          </button>
        </header>

        <section className="dashboard-error">
          <span>
            PROJECT ERROR
          </span>

          <h1>
            Unable to load this project
          </h1>

          <p>{error}</p>

          <Link to="/projects">
            ← Back to projects
          </Link>
        </section>
      </main>
    );
  }

  const primaryMetric =
    metricColumn ||
    kpis.metric_label ||
    "Primary metric";

  const firstValue =
    trend.first_value;

  const lastValue =
    trend.last_value;

  const datasetRows =
    dataset?.rows ??
    dataset?.row_count ??
    kpis.records ??
    0;

  const datasetColumns =
    dataset?.columns ??
    dataset?.column_count ??
    kpis.columns ??
    0;

  const datasetFormat =
    dataset?.format ??
    dataset?.source_format ??
    "—";

  return (
    <main className="dashboard-page">
      <header className="dashboard-header">
        <Link
          to="/projects"
          className="dashboard-brand"
        >
          Insight<span>OS</span>
        </Link>

        <div className="dashboard-header-actions">
          <Link to="/projects">
            Projects
          </Link>

          <button onClick={logout}>
            Logout
          </button>
        </div>
      </header>

      <section className="dashboard-content">
        <div className="dashboard-breadcrumb">
          <Link to="/projects">
            Projects
          </Link>

          <span>/</span>

          <strong>
            {project?.name}
          </strong>
        </div>

        <section className="dashboard-hero">
          <div>
            <span className="dashboard-eyebrow">
              ANALYTICS WORKSPACE
            </span>

            <h1>
              {project?.name}
            </h1>

            <p>
              {project?.description ||
                "One integrated workspace for your dataset, analytics, anomalies, forecast, AI insights and reports."}
            </p>
          </div>

          <div className="dashboard-status">
            <span />
            {project?.status ||
              "active"}
          </div>
        </section>

        <DatasetUploadSection
          dataset={dataset}
          uploading={uploading}
          processingStep={
            processingStep
          }
          uploadError={
            uploadError
          }
          handleDatasetUpload={
            handleDatasetUpload
          }
        />

        {dataset && (
          <>
            <section className="dashboard-dataset-banner">
              <div>
                <span>
                  ACTIVE DATASET
                </span>

                <strong>
                  {dataset.name ||
                    "No dataset connected"}
                </strong>
              </div>

              <div className="dataset-banner-meta">
                <span>
                  {number(
                    datasetRows
                  )}{" "}
                  rows
                </span>

                <span>
                  {number(
                    datasetColumns
                  )}{" "}
                  columns
                </span>

                <span>
                  {datasetFormat}
                </span>
              </div>
            </section>

            <section className="dashboard-stats dashboard-stats-primary">
              <article className="stat-card stat-featured">
                <span>
                  {kpis.metric_label ||
                    "PRIMARY METRIC"}
                </span>

                <strong>
                  {number(
                    kpis.total_value
                  )}
                </strong>

                <small>
                  Automatically calculated
                </small>
              </article>

              <article className="stat-card">
                <span>
                  GROWTH
                </span>

                <strong>
                  {growthText}
                </strong>

                <small>
                  Earliest → latest period
                </small>
              </article>

              <article className="stat-card">
                <span>
                  AVERAGE
                </span>

                <strong>
                  {number(
                    kpis.average_value
                  )}
                </strong>

                <small>
                  Average primary metric
                </small>
              </article>

              <article className="stat-card">
                <span>
                  RECORDS
                </span>

                <strong>
                  {number(
                    kpis.records
                  )}
                </strong>

                <small>
                  Rows in active dataset
                </small>
              </article>
            </section>

            <section className="dashboard-mini-stats">
              <article>
                <span>
                  COLUMNS
                </span>

                <strong>
                  {number(
                    kpis.columns
                  )}
                </strong>
              </article>

              <article>
                <span>
                  MISSING VALUES
                </span>

                <strong>
                  {number(
                    kpis.missing_values
                  )}
                </strong>
              </article>

              <article>
                <span>
                  DUPLICATES
                </span>

                <strong>
                  {number(
                    kpis.duplicate_rows
                  )}
                </strong>
              </article>

              <article>
                <span>
                  NEXT FORECAST
                </span>

                <strong>
                  {number(
                    kpis.next_forecast
                  )}
                </strong>
              </article>

              <article>
                <span>
                  DATA QUALITY
                </span>

                <strong>
                  {qualityScore ===
                  null
                    ? "—"
                    : `${number(
                        qualityScore
                      )}%`}
                </strong>
              </article>
            </section>

            <section className="integrated-section visual-overview-section">
              <div className="dashboard-section-heading">
                <div>
                  <span>
                    VISUAL OVERVIEW
                  </span>

                  <h2>
                    What the data is doing
                  </h2>
                </div>

                <small>
                  {visualizations.length
                    ? `${visualizations.length} automatic visualizations`
                    : "Waiting for automatic analysis"}
                </small>
              </div>

              <VisualizationSection
                visualizations={
                  visualizations
                }
                number={number}
              />

              <div className="overview-signal-grid">
                <div className="signal-card">
                  <div className="signal-card-head">
                    <span>
                      CORE SIGNAL
                    </span>

                    <strong>
                      {primaryMetric}
                    </strong>
                  </div>

                  <div className="signal-row">
                    <span>
                      First value
                    </span>

                    <strong>
                      {number(
                        firstValue
                      )}
                    </strong>
                  </div>

                  <div className="signal-row">
                    <span>
                      Last value
                    </span>

                    <strong>
                      {number(
                        lastValue
                      )}
                    </strong>
                  </div>

                  <div className="signal-row">
                    <span>
                      Direction
                    </span>

                    <strong className="signal-direction">
                      {trend.direction ||
                        "—"}
                    </strong>
                  </div>

                  <div className="signal-row">
                    <span>
                      Period growth
                    </span>

                    <strong>
                      {trend.period_growth_percentage ===
                      undefined
                        ? "—"
                        : `${number(
                            trend.period_growth_percentage
                          )}%`}
                    </strong>
                  </div>

                  <div className="signal-row">
                    <span>
                      Moving average
                    </span>

                    <strong>
                      {number(
                        trend.moving_average_current
                      )}
                    </strong>
                  </div>
                </div>
              </div>

              {dateColumn &&
                metricColumn &&
                previewRows.length >
                  1 && (
                  <div className="integrated-chart-block">
                    <TrendChart
                      rows={
                        previewRows
                      }
                      dateColumn={
                        dateColumn
                      }
                      metricColumn={
                        metricColumn
                      }
                      number={
                        number
                      }
                      formatDate={
                        formatDate
                      }
                      shortDate={
                        shortDate
                      }
                    />
                  </div>
                )}
            </section>

            <section className="integrated-section">
              <div className="dashboard-section-heading">
                <div>
                  <span>
                    DATASET
                  </span>

                  <h2>
                    Actual uploaded data
                  </h2>
                </div>

                <small>
                  {previewRows.length
                    ? `Showing ${previewRows.length} rows · ${previewColumns.length} columns`
                    : ""}
                </small>
              </div>

              {detailsLoading ? (
                <div className="dashboard-empty">
                  Loading dataset details...
                </div>
              ) : previewRows.length ===
                0 ? (
                <div className="dashboard-empty">
                  Dataset preview is not available yet.
                </div>
              ) : (
                <div className="data-table-wrap large-table-wrap">
                  <table className="data-table data-table-large">
                    <thead>
                      <tr>
                        <th className="row-number-cell">
                          #
                        </th>

                        {previewColumns.map(
                          (column) => (
                            <th
                              key={
                                column
                              }
                            >
                              {column}
                            </th>
                          )
                        )}
                      </tr>
                    </thead>

                    <tbody>
                      {previewRows.map(
                        (
                          row,
                          rowIndex
                        ) => (
                          <tr
                            key={
                              rowIndex
                            }
                          >
                            <td className="row-number-cell">
                              {rowIndex +
                                1}
                            </td>

                            {previewColumns.map(
                              (
                                column
                              ) => {
                                const isDate =
                                  column ===
                                  dateColumn;

                                const value =
                                  row[
                                    column
                                  ];

                                return (
                                  <td
                                    key={
                                      column
                                    }
                                    className={
                                      isDate
                                        ? "date-cell"
                                        : ""
                                    }
                                  >
                                    {value ===
                                      null ||
                                    value ===
                                      undefined ||
                                    value ===
                                      ""
                                      ? "—"
                                      : isDate
                                      ? formatDate(
                                          value
                                        )
                                      : String(
                                          value
                                        )}
                                  </td>
                                );
                              }
                            )}
                          </tr>
                        )
                      )}
                    </tbody>
                  </table>

                  <p className="table-note">
                    Preview shows the first{" "}
                    {
                      previewRows.length
                    }{" "}
                    records. All KPI and analysis calculations use the complete uploaded dataset.
                  </p>
                </div>
              )}
            </section>

            <section className="integrated-section">
              <div className="dashboard-section-heading">
                <div>
                  <span>
                    ANALYTICS
                  </span>

                  <h2>
                    Automatic statistical analysis
                  </h2>
                </div>
              </div>

              <div className="analysis-layout">
                <div className="analysis-card">
                  <span>
                    NUMERIC COLUMNS
                  </span>

                  <strong>
                    {(
                      analytics.numeric_columns ||
                      []
                    ).join(", ") ||
                      "None detected"}
                  </strong>
                </div>

                <div className="analysis-card">
                  <span>
                    CATEGORICAL COLUMNS
                  </span>

                  <strong>
                    {(
                      analytics.categorical_columns ||
                      []
                    ).join(", ") ||
                      "None detected"}
                  </strong>
                </div>

                <div className="analysis-card">
                  <span>
                    DATE COLUMNS
                  </span>

                  <strong>
                    {(
                      analytics.datetime_columns ||
                      []
                    ).join(", ") ||
                      "None detected"}
                  </strong>
                </div>
              </div>

              <div className="stat-matrix">
                <div className="stat-matrix-title">
                  <span>
                    STATISTICS
                  </span>

                  <strong>
                    {metricColumn ||
                      "Primary metric"}
                  </strong>
                </div>

                {[
                  [
                    "Count",
                    primaryStats?.count,
                  ],
                  [
                    "Sum",
                    primaryStats?.sum,
                  ],
                  [
                    "Mean",
                    primaryStats?.mean,
                  ],
                  [
                    "Median",
                    primaryStats?.median,
                  ],
                  [
                    "Minimum",
                    primaryStats?.min ??
                      primaryStats?.minimum,
                  ],
                  [
                    "Maximum",
                    primaryStats?.max ??
                      primaryStats?.maximum,
                  ],
                  [
                    "Standard deviation",
                    primaryStats?.std ??
                      primaryStats?.standard_deviation,
                  ],
                  [
                    "Variance",
                    primaryStats?.variance,
                  ],
                  [
                    "Range",
                    primaryStats?.range,
                  ],
                  [
                    "Coefficient of variation",
                    primaryStats?.coefficient_of_variation,
                  ],
                ].map(
                  ([name, value]) => (
                    <div
                      className="stat-matrix-item"
                      key={name}
                    >
                      <span>
                        {name}
                      </span>

                      <strong>
                        {value ===
                          undefined ||
                        value ===
                          null
                          ? "—"
                          : number(
                              value
                            )}
                      </strong>
                    </div>
                  )
                )}
              </div>

              <div className="analysis-detail">
                <div className="detail-columns">
                  <div>
                    <span className="detail-label">
                      CATEGORICAL SUMMARY
                    </span>

                    <ObjectPreview
                      data={
                        analytics.categorical_summary ||
                        analytics.categorical ||
                        {}
                      }
                      label={
                        label
                      }
                    />
                  </div>

                  <div>
                    <span className="detail-label">
                      CORRELATIONS
                    </span>

                    <ObjectPreview
                      data={
                        analytics.correlations ||
                        {}
                      }
                      label={
                        label
                      }
                    />
                  </div>
                </div>
              </div>
            </section>

            <section className="integrated-section">
              <div className="dashboard-section-heading">
                <div>
                  <span>
                    DATA QUALITY
                  </span>

                  <h2>
                    Column intelligence
                  </h2>
                </div>
              </div>

              {profile.length ===
              0 ? (
                <div className="dashboard-empty">
                  Column profile is not available.
                </div>
              ) : (
                <div className="data-table-wrap">
                  <table className="data-table quality-table">
                    <thead>
                      <tr>
                        <th>
                          Column
                        </th>

                        <th>
                          Detected type
                        </th>

                        <th>
                          Missing
                        </th>

                        <th>
                          Unique
                        </th>

                        <th>
                          Nullable
                        </th>
                      </tr>
                    </thead>

                    <tbody>
                      {profile.map(
                        (
                          column,
                          index
                        ) => (
                          <tr
                            key={`${column.column}-${index}`}
                          >
                            <td className="strong-cell">
                              {
                                column.column
                              }
                            </td>

                            <td>
                              <span className="type-pill">
                                {column.detected_type ||
                                  column.data_type ||
                                  "—"}
                              </span>
                            </td>

                            <td>
                              {number(
                                column.missing_count
                              )}
                            </td>

                            <td>
                              {number(
                                column.unique_count
                              )}
                            </td>

                            <td>
                              {column.missing_count >
                              0
                                ? "Yes"
                                : "No"}
                            </td>
                          </tr>
                        )
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section className="integrated-section">
              <div className="dashboard-section-heading">
                <div>
                  <span>
                    AUTOMATIC FORECAST
                  </span>

                  <h2>
                    Future trend
                  </h2>
                </div>

                <small>
                  {forecast.available
                    ? "Model-generated future values"
                    : "Waiting for a usable time-series"}
                </small>
              </div>

              {!forecast.available ? (
                <div className="dashboard-empty">
                  <h3>
                    Forecast not available
                  </h3>

                  <p>
                    {forecast.reason ||
                      "The dataset does not contain enough usable time-series information."}
                  </p>
                </div>
              ) : (
                <div className="forecast-panel">
                  <div className="forecast-summary">
                    <div>
                      <span>
                        METRIC
                      </span>

                      <strong>
                        {
                          forecast.metric_column
                        }
                      </strong>
                    </div>

                    <div>
                      <span>
                        DATE
                      </span>

                      <strong>
                        {
                          forecast.date_column
                        }
                      </strong>
                    </div>

                    <div>
                      <span>
                        METHOD
                      </span>

                      <strong>
                        Trend forecast
                      </strong>
                    </div>
                  </div>

                  <ForecastChart
                    points={
                      forecast.points ||
                      []
                    }
                    metricColumn={
                      forecast.metric_column
                    }
                    number={
                      number
                    }
                    formatDate={
                      formatDate
                    }
                    shortDate={
                      shortDate
                    }
                  />

                  <div className="forecast-table-wrap">
                    <table className="data-table forecast-data-table">
                      <thead>
                        <tr>
                          <th>
                            Forecast date
                          </th>

                          <th>
                            Predicted value
                          </th>
                        </tr>
                      </thead>

                      <tbody>
                        {(
                          forecast.points ||
                          []
                        ).map(
                          (
                            point,
                            index
                          ) => (
                            <tr
                              key={`${point.date}-${index}`}
                            >
                              <td className="date-cell">
                                {formatDate(
                                  point.date
                                )}
                              </td>

                              <td className="forecast-value">
                                {number(
                                  point.value
                                )}
                              </td>
                            </tr>
                          )
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </section>

            <section className="integrated-section">
              <div className="dashboard-section-heading">
                <div>
                  <span>
                    ANOMALIES
                  </span>

                  <h2>
                    Statistically unusual records
                  </h2>
                </div>

                <strong className="section-count">
                  {
                    normalizedAnomalies.length
                  }
                </strong>
              </div>

              {normalizedAnomalies.length ===
              0 ? (
                <div className="dashboard-empty">
                  <h3>
                    No unusual records detected
                  </h3>

                  <p>
                    The current anomaly engine did not identify statistically unusual records.
                  </p>
                </div>
              ) : (
                <div className="anomaly-layout">
                  <div className="anomaly-summary">
                    <div className="anomaly-total">
                      <span>
                        TOTAL ANOMALIES
                      </span>

                      <strong>
                        {number(
                          normalizedAnomalies.length
                        )}
                      </strong>
                    </div>

                    <div className="anomaly-bars">
                      <div className="anomaly-bar-row">
                        <span>
                          Low
                        </span>

                        <div className="anomaly-bar-track">
                          <div
                            className="anomaly-bar-fill"
                            style={{
                              width: `${
                                normalizedAnomalies.length
                                  ? (anomalyCounts.low /
                                      normalizedAnomalies.length) *
                                    100
                                  : 0
                              }%`,
                            }}
                          />
                        </div>

                        <strong>
                          {
                            anomalyCounts.low
                          }
                        </strong>
                      </div>

                      <div className="anomaly-bar-row">
                        <span>
                          High
                        </span>

                        <div className="anomaly-bar-track">
                          <div
                            className="anomaly-bar-fill"
                            style={{
                              width: `${
                                normalizedAnomalies.length
                                  ? (anomalyCounts.high /
                                      normalizedAnomalies.length) *
                                    100
                                  : 0
                              }%`,
                            }}
                          />
                        </div>

                        <strong>
                          {
                            anomalyCounts.high
                          }
                        </strong>
                      </div>
                    </div>
                  </div>

                  <div className="anomaly-table-wrap">
                    <div className="data-table-wrap large-table-wrap">
                      <table className="data-table anomaly-data-table">
                        <thead>
                          <tr>
                            <th>
                              Date
                            </th>
                            <th>
                              Region
                            </th>
                            <th>
                              Product
                            </th>
                            <th>
                              Channel
                            </th>
                            <th>
                              Sales
                            </th>
                            <th>
                              Orders
                            </th>
                            <th>
                              Customers
                            </th>
                            <th>
                              Returns
                            </th>
                            <th>
                              Discount %
                            </th>
                            <th>
                              Profit
                            </th>
                            <th>
                              Metric
                            </th>
                            <th>
                              Type
                            </th>
                            <th>
                              Z-Score
                            </th>
                            <th>
                              Anomaly Score
                            </th>
                          </tr>
                        </thead>

                        <tbody>
                          {anomalyRows.map(
                            (row) => (
                              <tr
                                key={
                                  row.id
                                }
                              >
                                <td className="date-cell">
                                  {formatDate(
                                    row.date
                                  )}
                                </td>

                                <td>
                                  {
                                    row.region
                                  }
                                </td>

                                <td>
                                  {
                                    row.product
                                  }
                                </td>

                                <td>
                                  {
                                    row.channel
                                  }
                                </td>

                                <td>
                                  {number(
                                    row.sales
                                  )}
                                </td>

                                <td>
                                  {number(
                                    row.orders
                                  )}
                                </td>

                                <td>
                                  {number(
                                    row.customers
                                  )}
                                </td>

                                <td>
                                  {number(
                                    row.returns
                                  )}
                                </td>

                                <td>
                                  {number(
                                    row.discount
                                  )}
                                </td>

                                <td>
                                  {number(
                                    row.profit
                                  )}
                                </td>

                                <td>
                                  {label(
                                    row.metric
                                  )}
                                </td>

                                <td>
                                  <span
                                    className={`anomaly-badge ${String(
                                      row.type
                                    ).toLowerCase()}`}
                                  >
                                    {
                                      row.type
                                    }
                                  </span>
                                </td>

                                <td>
                                  {
                                    row.zScore
                                  }
                                </td>

                                <td>
                                  {
                                    row.anomalyScore
                                  }
                                </td>
                              </tr>
                            )
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}
            </section>

            <section className="integrated-section ai-section">
              <div className="dashboard-section-heading">
                <div>
                  <span>
                    INSIGHTOS AI
                  </span>

                  <h2>
                    Executive insights
                  </h2>
                </div>

                <span className="ai-model">
                  Ollama · qwen2.5-coder:7b
                </span>
              </div>

              {aiInsight ? (
                <div className="ai-insight-card">
                  <div className="ai-insight-content">
                    <ReactMarkdown>
                      {
                        aiInsight
                      }
                    </ReactMarkdown>
                  </div>
                </div>
              ) : (
                <div className="dashboard-empty">
                  <h3>
                    AI insight is not available yet
                  </h3>

                  <p>
                    Run the automatic analysis pipeline after uploading a dataset.
                  </p>
                </div>
              )}
            </section>

            <section className="integrated-section">
              <div className="dashboard-section-heading">
                <div>
                  <span>
                    REPORT
                  </span>

                  <h2>
                    Complete analysis report
                  </h2>
                </div>
              </div>

              {reportId ? (
                <div className="report-inline-card">
                  <div>
                    <strong>
                      InsightOS analysis report
                    </strong>

                    <span>
                      KPIs, data quality, analytics, anomalies, forecast and AI insights.
                    </span>
                  </div>

                  <a
                    className="report-inline-button"
                    href={`${API}/reports/${reportId}/download`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Download PDF
                  </a>
                </div>
              ) : (
                <div className="dashboard-empty">
                  Report will appear here after automatic processing.
                </div>
              )}
            </section>

            <section className="integrated-section ai-section chat-section">
              <div className="dashboard-section-heading">
                <div>
                  <span>
                    INSIGHTOS AI
                  </span>

                  <h2>
                    Ask your dataset
                  </h2>
                </div>
              </div>

              <div className="chat-box">
                <div className="chat-messages">
                  {chatMessages.length ===
                  0 ? (
                    <div className="chat-empty">
                      Ask a question about the active dataset. Answers are generated from the verified dataset analytics.
                    </div>
                  ) : (
                    chatMessages.map(
                      (
                        message,
                        index
                      ) => (
                        <div
                          key={
                            index
                          }
                          className={`chat-message ${
                            message.role ===
                            "user"
                              ? "chat-user"
                              : "chat-assistant"
                          }`}
                        >
                          <span>
                            {message.role ===
                            "user"
                              ? "You"
                              : "InsightOS AI"}
                          </span>

                          <p>
                            {
                              message.text
                            }
                          </p>
                        </div>
                      )
                    )
                  )}
                </div>

                <form
                  className="chat-form"
                  onSubmit={
                    handleChatSubmit
                  }
                >
                  <input
                    value={
                      question
                    }
                    onChange={(
                      event
                    ) =>
                      setQuestion(
                        event.target
                          .value
                      )
                    }
                    placeholder="Ask about sales, trends, anomalies, forecast..."
                    disabled={
                      chatLoading ||
                      !dataset?.id
                    }
                  />

                  <button
                    type="submit"
                    disabled={
                      chatLoading ||
                      !question.trim() ||
                      !dataset?.id
                    }
                  >
                    {chatLoading
                      ? "Thinking..."
                      : "Ask"}
                  </button>
                </form>
              </div>
            </section>

            <section className="integrated-section">
              <div className="dashboard-section-heading">
                <div>
                  <span>
                    CONNECTED DATA
                  </span>

                  <h2>
                    Project datasets
                  </h2>
                </div>
              </div>

              <div className="dataset-list">
                {datasets.length ===
                0 ? (
                  <div className="dashboard-empty">
                    No datasets connected yet.
                  </div>
                ) : (
                  datasets.map(
                    (item) => (
                      <article
                        className="dataset-row"
                        key={
                          item.id
                        }
                      >
                        <div>
                          <strong>
                            {
                              item.name
                            }
                          </strong>

                          <span>
                            {
                              item.source_type
                            }{" "}
                            ·{" "}
                            {
                              item.source_format
                            }
                          </span>
                        </div>

                        <div className="dataset-meta">
                          <span>
                            {number(
                              item.row_count ??
                                item.rows
                            )}{" "}
                            rows
                          </span>

                          <span>
                            {number(
                              item.column_count ??
                                item.columns
                            )}{" "}
                            columns
                          </span>
                        </div>
                      </article>
                    )
                  )
                )}
              </div>
            </section>
          </>
        )}
      </section>
    </main>
  );
}