import React, { useEffect, useMemo, useRef, useState } from 'react';
import ReactDOM from 'react-dom/client';
import {
  AlertCircle,
  Camera,
  CheckCircle2,
  FileImage,
  GitBranch,
  Home,
  Loader2,
  QrCode,
  RefreshCw,
  ScanLine,
  UploadCloud,
} from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  type Edge,
  type Node,
} from 'reactflow';
import 'reactflow/dist/style.css';
import './styles.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL
  ?? `${window.location.protocol}//${window.location.hostname}:8000/api`;
const MAX_UPLOAD_BYTES = 8 * 1024 * 1024;
const ACCEPTED_IMAGE_TYPES = new Set(['image/png', 'image/jpeg']);

type AppView = 'landing' | 'scan' | 'processing' | 'dashboard' | 'low-confidence' | 'error';
type UploadStatus = 'idle' | 'uploading' | 'accepted' | 'error';

type AppError = {
  title: string;
  message: string;
  canRetry: boolean;
};

type ScanPanel = {
  token: string;
  url: string;
  status: string;
  expiresAt: string;
};

type DiagramUpload = {
  session_token: string;
  file_name: string | null;
  width: number | null;
  height: number | null;
};

type DiagramElement = {
  element_key: string;
  element_type: string;
  label: string | null;
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: number | null;
  ocr_text: string | null;
};

type GraphEdge = {
  source_key: string;
  target_key: string;
  edge_type: string;
  label: string | null;
  confidence: number | null;
};

type ValidationIssue = {
  issue_code: string;
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
  title: string;
  description: string;
  element_key: string | null;
  evidence: string | null;
  fix_suggestion: string | null;
  what: string | null;
  where: string | null;
  why: string | null;
  fix: string | null;
};

type PreprocessingMetadata = {
  original_width: number;
  original_height: number;
  processed_width: number;
  processed_height: number;
};

type AnalysisResult = {
  analysis_id: number;
  status: string;
  diagram_type: string | null;
  classification_confidence: number | null;
  low_confidence: boolean;
  preprocessing: PreprocessingMetadata | null;
  classification_evidence: Record<string, number>;
  elements: DiagramElement[];
  edges: GraphEdge[];
  issues: ValidationIssue[];
};

type QueryResponse = {
  status: string;
  query_id: number | null;
  analysis_id: number | null;
  answer: string | null;
  evidence: Record<string, unknown> | null;
};

class ApiRequestError extends Error {
  status: number | null;

  constructor(message: string, status: number | null = null) {
    super(message);
    this.name = 'ApiRequestError';
    this.status = status;
  }
}

const processingStages = [
  'Image received',
  'Classifying diagram',
  'Extracting elements',
  'Building graph',
  'Validating structure',
  'Generating insights',
];

function confidenceLabel(value: number | null) {
  if (value === null || value === undefined) {
    return 'Unknown confidence';
  }
  return `${Math.round(value * 1000) / 10}% confidence`;
}

function severityRank(issue: ValidationIssue) {
  if (issue.severity === 'CRITICAL') return 0;
  if (issue.severity === 'WARNING') return 1;
  return 2;
}

function issueCountBySeverity(issues: ValidationIssue[], severity: ValidationIssue['severity']) {
  return issues.filter((issue) => issue.severity === severity).length;
}

function elementDisplayName(element: DiagramElement) {
  return element.label || element.ocr_text || element.element_key;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function extractErrorMessage(payload: unknown, fallback: string) {
  if (!isRecord(payload)) {
    return fallback;
  }
  const detail = payload.detail;
  if (typeof detail === 'string') {
    return detail;
  }
  if (isRecord(detail) && typeof detail.message === 'string') {
    return detail.message;
  }
  if (typeof payload.message === 'string') {
    return payload.message;
  }
  return fallback;
}

async function requestJson<T>(url: string, options: RequestInit = {}, fallback = 'Request failed.') {
  let response: Response;
  try {
    response = await fetch(url, options);
  } catch (error) {
    throw new ApiRequestError(
      error instanceof TypeError
        ? 'Cannot reach the VisuLogic backend. Check that the server is running on port 8000.'
        : fallback,
      null,
    );
  }

  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    throw new ApiRequestError(extractErrorMessage(payload, fallback), response.status);
  }

  return payload as T;
}

function errorState(error: unknown, fallback: string): AppError {
  const message = error instanceof Error ? error.message : fallback;
  const canRetry = !(error instanceof ApiRequestError) || error.status === null || error.status >= 500;
  return {
    title: error instanceof ApiRequestError && error.status === 404
      ? 'This session is no longer available'
      : 'Something went wrong',
    message,
    canRetry,
  };
}

function validateUploadFile(file: File): string | null {
  if (!ACCEPTED_IMAGE_TYPES.has(file.type)) {
    return 'Please upload a PNG or JPEG image.';
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    return 'Please upload an image smaller than 8 MB.';
  }
  return null;
}

function DesktopApp() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [view, setView] = useState<AppView>('landing');
  const [isDragging, setIsDragging] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>('idle');
  const [uploadMessage, setUploadMessage] = useState('Upload a diagram to start');
  const [scanPanel, setScanPanel] = useState<ScanPanel | null>(null);
  const [scanStatus, setScanStatus] = useState('Waiting for photo...');
  const [activeSession, setActiveSession] = useState<string | null>(null);
  const [upload, setUpload] = useState<DiagramUpload | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [selectedIssueIndex, setSelectedIssueIndex] = useState(0);
  const [errorDetails, setErrorDetails] = useState<AppError | null>(null);

  const sortedIssues = useMemo(
    () => [...(analysis?.issues ?? [])].sort((first, second) => severityRank(first) - severityRank(second)),
    [analysis],
  );
  const selectedIssue = sortedIssues[selectedIssueIndex] ?? sortedIssues[0] ?? null;

  useEffect(() => {
    if (!scanPanel) {
      return;
    }

    const interval = window.setInterval(async () => {
      try {
        const payload = await requestJson<{ status: string }>(
          `${API_BASE_URL}/scan/${scanPanel.token}/status`,
          {},
          'Scan session expired.',
        );
        if (payload.status === 'PHONE_CONNECTED') {
          setScanStatus('Phone connected. Take a photo from your phone.');
        }
        if (payload.status === 'IMAGE_RECEIVED') {
          setScanStatus('Diagram received. Starting analysis...');
          setActiveSession(scanPanel.token);
          setUpload({
            session_token: scanPanel.token,
            file_name: 'Phone scan',
            width: null,
            height: null,
          });
          window.clearInterval(interval);
          void runAnalysis(scanPanel.token);
        }
      } catch {
        setScanStatus('Connection interrupted. Check that both devices can reach the backend.');
      }
    }, 1800);

    return () => window.clearInterval(interval);
  }, [scanPanel]);

  async function runAnalysis(sessionToken: string) {
    setView('processing');
    setAnalysis(null);
    setSelectedIssueIndex(0);
    setErrorDetails(null);

    try {
      const payload = await requestJson<AnalysisResult>(
        `${API_BASE_URL}/analysis/${sessionToken}`,
        { method: 'POST' },
        'Analysis failed.',
      );
      setAnalysis(payload);
      setView(payload.low_confidence ? 'low-confidence' : 'dashboard');
    } catch (error) {
      setErrorDetails(errorState(error, 'Something went wrong while analyzing your diagram.'));
      setView('error');
    }
  }

  async function uploadFile(file: File) {
    const validationMessage = validateUploadFile(file);
    if (validationMessage) {
      setUploadStatus('error');
      setUploadMessage(validationMessage);
      setErrorDetails({
        title: 'Unsupported upload',
        message: validationMessage,
        canRetry: false,
      });
      return;
    }

    setUploadStatus('uploading');
    setUploadMessage(`Uploading ${file.name}...`);
    setErrorDetails(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const payload = await requestJson<DiagramUpload>(
        `${API_BASE_URL}/upload`,
        {
          method: 'POST',
          body: formData,
        },
        'We could not upload this image.',
      );

      setScanPanel(null);
      setUploadStatus('accepted');
      setUpload(payload);
      setActiveSession(payload.session_token);
      setUploadMessage(
        `Diagram received: ${payload.file_name ?? 'uploaded image'} (${payload.width} x ${payload.height})`,
      );
      await runAnalysis(payload.session_token);
    } catch (error) {
      setUploadStatus('error');
      const details = errorState(error, 'Something went wrong while uploading.');
      setErrorDetails(details);
      setUploadMessage(details.message);
      setView('error');
    }
  }

  async function startPhoneScan() {
    setUploadStatus('idle');
    setUploadMessage('Upload a diagram to start');
    setScanStatus('Waiting for photo...');
    setErrorDetails(null);

    try {
      const payload = await requestJson<{ session_token: string; status: string; expires_at: string }>(
        `${API_BASE_URL}/scan/create`,
        { method: 'POST' },
        'Could not create scan session.',
      );
      const mobileUrl = `${window.location.origin}/mobile/scan/${payload.session_token}`;
      setScanPanel({
        token: payload.session_token,
        url: mobileUrl,
        status: payload.status,
        expiresAt: payload.expires_at,
      });
      setView('scan');
    } catch (error) {
      setUploadStatus('error');
      const details = errorState(error, 'Could not create scan session.');
      setErrorDetails(details);
      setUploadMessage(details.message);
      setView('error');
    }
  }

  function resetWorkflow() {
    setView('landing');
    setScanPanel(null);
    setActiveSession(null);
    setUpload(null);
    setAnalysis(null);
    setErrorDetails(null);
    setUploadStatus('idle');
    setUploadMessage('Upload a diagram to start');
    setSelectedIssueIndex(0);
  }

  function handleFiles(files: FileList | null) {
    const file = files?.[0];
    if (file) {
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      void uploadFile(file);
    }
  }

  return (
    <main className="app-shell">
      <nav className="topbar">
        <button className="brand-button" type="button" onClick={resetWorkflow}>
          <ScanLine size={22} aria-hidden="true" />
          <span>VisuLogic</span>
        </button>
        <div className="nav-actions">
          <button className="ghost-button" type="button" onClick={resetWorkflow}>
            <Home size={16} aria-hidden="true" />
            Home
          </button>
          <a href="#help">Help</a>
        </div>
      </nav>

      {view === 'landing' && (
        <>
          <LandingSection
            fileInputRef={fileInputRef}
            isDragging={isDragging}
            setIsDragging={setIsDragging}
            uploadStatus={uploadStatus}
            uploadMessage={uploadMessage}
            handleFiles={handleFiles}
            startPhoneScan={startPhoneScan}
          />
          <WorkflowPreview />
        </>
      )}

      {view === 'scan' && scanPanel && (
        <QrScanPanel scanPanel={scanPanel} scanStatus={scanStatus} onCancel={resetWorkflow} />
      )}

      {view === 'processing' && <ProcessingScreen upload={upload} />}

      {view === 'low-confidence' && analysis && (
        <LowConfidenceScreen
          analysis={analysis}
          onContinue={() => setView('dashboard')}
          onUploadAnother={resetWorkflow}
        />
      )}

      {view === 'dashboard' && analysis && (
        <Dashboard
          analysis={analysis}
          upload={upload}
          sessionToken={activeSession}
          issues={sortedIssues}
          selectedIssue={selectedIssue}
          selectedIssueIndex={selectedIssueIndex}
          setSelectedIssueIndex={setSelectedIssueIndex}
          onAnalyzeAnother={resetWorkflow}
        />
      )}

      {view === 'error' && (
        <ErrorState
          error={errorDetails}
          onTryAgain={() => activeSession ? void runAnalysis(activeSession) : setView('landing')}
          onHome={resetWorkflow}
        />
      )}
    </main>
  );
}

function LandingSection({
  fileInputRef,
  isDragging,
  setIsDragging,
  uploadStatus,
  uploadMessage,
  handleFiles,
  startPhoneScan,
}: {
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  isDragging: boolean;
  setIsDragging: (value: boolean) => void;
  uploadStatus: UploadStatus;
  uploadMessage: string;
  handleFiles: (files: FileList | null) => void;
  startPhoneScan: () => Promise<void>;
}) {
  return (
    <section className="landing">
      <div className="hero-copy">
        <p className="eyebrow">Flowcharts - DFDs - Technical diagrams</p>
        <h1>From Pixels to Logic</h1>
        <p>
          Upload a diagram or scan it from your phone. VisuLogic turns visible
          diagram evidence into a graph, validates the structure, and explains
          findings with traceable highlights.
        </p>
      </div>

      <div
        className={`upload-zone ${isDragging ? 'dragging' : ''} ${uploadStatus}`}
        role="button"
        tabIndex={0}
        onClick={() => fileInputRef.current?.click()}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            fileInputRef.current?.click();
          }
        }}
        onDragEnter={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setIsDragging(false);
          handleFiles(event.dataTransfer.files);
        }}
      >
        {uploadStatus === 'accepted' ? (
          <CheckCircle2 size={42} aria-hidden="true" />
        ) : uploadStatus === 'error' ? (
          <AlertCircle size={42} aria-hidden="true" />
        ) : (
          <UploadCloud size={42} aria-hidden="true" />
        )}
        <h2>{uploadMessage}</h2>
        <p>PNG, JPG, or JPEG up to the configured processing limit.</p>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg"
          className="file-input"
          onChange={(event) => handleFiles(event.target.files)}
        />
        <div className="actions">
          <button
            className="primary-button"
            type="button"
            disabled={uploadStatus === 'uploading'}
            onClick={(event) => {
              event.stopPropagation();
              fileInputRef.current?.click();
            }}
          >
            {uploadStatus === 'uploading' ? (
              <Loader2 className="button-spinner" size={18} aria-hidden="true" />
            ) : (
              <FileImage size={18} aria-hidden="true" />
            )}
            {uploadStatus === 'uploading' ? 'Uploading...' : 'Upload File'}
          </button>
          <button
            className="secondary-button"
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              void startPhoneScan();
            }}
          >
            <Camera size={18} aria-hidden="true" />
            Scan with Phone
          </button>
        </div>
      </div>
    </section>
  );
}

function QrScanPanel({
  scanPanel,
  scanStatus,
  onCancel,
}: {
  scanPanel: ScanPanel;
  scanStatus: string;
  onCancel: () => void;
}) {
  return (
    <section className="focused-panel-wrap">
      <div className="qr-panel">
        <QrCode size={34} aria-hidden="true" />
        <h2>Scan this QR code using your phone</h2>
        <div className="qr-box">
          <QRCodeSVG value={scanPanel.url} size={204} level="M" includeMargin />
        </div>
        <p className="pulse-status">{scanStatus}</p>
        <p className="session-meta">Expires at {new Date(scanPanel.expiresAt).toLocaleTimeString()}</p>
        <button className="secondary-button" type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </section>
  );
}

function ProcessingScreen({ upload }: { upload: DiagramUpload | null }) {
  const [activeStage, setActiveStage] = useState(0);

  useEffect(() => {
    const interval = window.setInterval(() => {
      setActiveStage((stage) => Math.min(stage + 1, processingStages.length - 1));
    }, 850);
    return () => window.clearInterval(interval);
  }, []);

  return (
    <section className="processing-screen view-enter">
      <div className="processing-header">
        <Loader2 size={28} aria-hidden="true" />
        <div>
          <h1>Analyzing diagram</h1>
          <p>{upload?.file_name ?? 'Diagram received'}</p>
        </div>
      </div>
      <div className="progress-track" aria-hidden="true">
        <span style={{ width: `${((activeStage + 1) / processingStages.length) * 100}%` }} />
      </div>
      <ol className="processing-list" aria-live="polite">
        {processingStages.map((stage, index) => (
          <li
            key={stage}
            className={index < activeStage ? 'complete' : index === activeStage ? 'active' : ''}
          >
            <span>{index < activeStage ? <CheckCircle2 size={17} aria-hidden="true" /> : index + 1}</span>
            {stage}
          </li>
        ))}
      </ol>
    </section>
  );
}

function LowConfidenceScreen({
  analysis,
  onContinue,
  onUploadAnother,
}: {
  analysis: AnalysisResult;
  onContinue: () => void;
  onUploadAnother: () => void;
}) {
  return (
    <section className="state-screen warning-state view-enter">
      <AlertCircle size={36} aria-hidden="true" />
      <h1>Classification may be inaccurate</h1>
      <p>
        VisuLogic detected {analysis.diagram_type ?? 'an unknown diagram'} with{' '}
        {confidenceLabel(analysis.classification_confidence)}.
      </p>
      <div className="actions">
        <button className="primary-button" type="button" onClick={onContinue}>
          Continue Anyway
        </button>
        <button className="secondary-button" type="button" onClick={onUploadAnother}>
          Upload Another Image
        </button>
      </div>
    </section>
  );
}

function ErrorState({
  error,
  onTryAgain,
  onHome,
}: {
  error: AppError | null;
  onTryAgain: () => void;
  onHome: () => void;
}) {
  return (
    <section className="state-screen error-state view-enter">
      <AlertCircle size={36} aria-hidden="true" />
      <h1>{error?.title ?? 'Something went wrong'}</h1>
      <p>{error?.message ?? 'Something went wrong while analyzing your diagram.'}</p>
      <div className="actions">
        {error?.canRetry !== false && (
          <button className="primary-button" type="button" onClick={onTryAgain}>
            <RefreshCw size={17} aria-hidden="true" />
            Try Again
          </button>
        )}
        <button className="secondary-button" type="button" onClick={onHome}>
          Back to Home
        </button>
      </div>
    </section>
  );
}

function Dashboard({
  analysis,
  upload,
  sessionToken,
  issues,
  selectedIssue,
  selectedIssueIndex,
  setSelectedIssueIndex,
  onAnalyzeAnother,
}: {
  analysis: AnalysisResult;
  upload: DiagramUpload | null;
  sessionToken: string | null;
  issues: ValidationIssue[];
  selectedIssue: ValidationIssue | null;
  selectedIssueIndex: number;
  setSelectedIssueIndex: (index: number) => void;
  onAnalyzeAnother: () => void;
}) {
  const [queryText, setQueryText] = useState('');
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null);
  const [queryError, setQueryError] = useState('');
  const [isQuerying, setIsQuerying] = useState(false);
  const issueElementKeys = useMemo(
    () => new Set(issues.map((issue) => issue.element_key).filter((key): key is string => Boolean(key))),
    [issues],
  );

  const graphNodes = useMemo<Node[]>(
    () => analysis.elements.map((element) => {
      const hasSelectedIssue = selectedIssue?.element_key === element.element_key;
      const hasAnyIssue = issueElementKeys.has(element.element_key);
      return {
        id: element.element_key,
        position: { x: element.x, y: element.y },
        data: {
          label: (
            <div className="flow-node-content">
              <strong>{elementDisplayName(element)}</strong>
              <span>{element.element_type}</span>
            </div>
          ),
        },
        className: [
          'flow-node',
          hasAnyIssue ? 'has-issue' : '',
          hasSelectedIssue ? 'selected-issue' : '',
        ].filter(Boolean).join(' '),
      };
    }),
    [analysis.elements, issueElementKeys, selectedIssue],
  );

  const graphEdges = useMemo<Edge[]>(
    () => analysis.edges.map((edge, index) => ({
      id: `${edge.source_key}-${edge.target_key}-${index}`,
      source: edge.source_key,
      target: edge.target_key,
      label: edge.label ?? edge.edge_type,
      markerEnd: { type: MarkerType.ArrowClosed },
      className: 'flow-edge',
      animated: edge.confidence !== null && edge.confidence < 0.55,
    })),
    [analysis.edges],
  );

  const selectedElement = selectedIssue?.element_key
    ? analysis.elements.find((element) => element.element_key === selectedIssue.element_key)
    : null;
  const evidenceEntries = Object.entries(analysis.classification_evidence ?? {});
  const criticalCount = issueCountBySeverity(issues, 'CRITICAL');
  const warningCount = issueCountBySeverity(issues, 'WARNING');
  const infoCount = issueCountBySeverity(issues, 'INFO');

  async function submitQuery(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!sessionToken || !queryText.trim()) {
      return;
    }

    setIsQuerying(true);
    setQueryError('');
    try {
      const payload = await requestJson<QueryResponse>(
        `${API_BASE_URL}/query/${sessionToken}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: queryText.trim() }),
        },
        'The query could not be answered.',
      );
      setQueryResult(payload);
    } catch (error) {
      setQueryError(error instanceof Error ? error.message : 'The query could not be answered.');
    } finally {
      setIsQuerying(false);
    }
  }

  return (
    <section className="dashboard view-enter">
      <header className="dashboard-header">
        <div>
          <p className="eyebrow">Current Analysis</p>
          <h1>{analysis.diagram_type ?? 'Unknown diagram'}</h1>
          <p>{confidenceLabel(analysis.classification_confidence)}</p>
        </div>
        <button className="secondary-button" type="button" onClick={onAnalyzeAnother}>
          Analyze Another
        </button>
      </header>

      <div className="metric-strip" aria-label="Analysis summary">
        <div className="metric-tile">
          <span>Elements</span>
          <strong>{analysis.elements.length}</strong>
        </div>
        <div className="metric-tile">
          <span>Edges</span>
          <strong>{analysis.edges.length}</strong>
        </div>
        <div className="metric-tile critical">
          <span>Critical</span>
          <strong>{criticalCount}</strong>
        </div>
        <div className="metric-tile warning">
          <span>Warnings</span>
          <strong>{warningCount}</strong>
        </div>
        <div className="metric-tile info">
          <span>Info</span>
          <strong>{infoCount}</strong>
        </div>
      </div>

      <div className="dashboard-grid">
        <div className="viewer-panel">
          <div className="viewer-toolbar">
            <span>{upload?.file_name ?? 'Uploaded diagram'}</span>
            <span>
              {analysis.elements.length} nodes / {analysis.edges.length} edges
            </span>
          </div>
          <div className="diagram-canvas-shell" aria-label="Interactive analysis graph">
            {graphNodes.length > 0 ? (
              <ReactFlow
                nodes={graphNodes}
                edges={graphEdges}
                fitView
                fitViewOptions={{ padding: 0.2 }}
                nodesDraggable={false}
                nodesConnectable={false}
                elementsSelectable={false}
              >
                <Background color="#cbd5e1" gap={28} />
                <Controls showInteractive={false} />
                <MiniMap pannable zoomable nodeStrokeWidth={3} />
              </ReactFlow>
            ) : (
              <div className="empty-graph">
                <AlertCircle size={22} aria-hidden="true" />
                No elements were extracted from this diagram.
              </div>
            )}
          </div>
        </div>

        <aside className="issues-panel dashboard-issues">
          <h2>Issues</h2>
          {issues.length === 0 ? (
            <div className="success-message">
              <CheckCircle2 size={20} aria-hidden="true" />
              No supported structural issues detected.
            </div>
          ) : (
            <div className="issue-list">
              {issues.map((issue, index) => (
                <button
                  key={`${issue.issue_code}-${index}`}
                  className={index === selectedIssueIndex ? 'issue-row active' : 'issue-row'}
                  type="button"
                  onClick={() => setSelectedIssueIndex(index)}
                >
                  <span className={`severity-dot ${issue.severity.toLowerCase()}`} />
                  <span>
                    <strong>{issue.title}</strong>
                    <small>{issue.element_key ?? 'Diagram-wide'}</small>
                  </span>
                </button>
              ))}
            </div>
          )}
        </aside>
      </div>

      <div className="dashboard-bottom">
        <section className="explanation-panel">
          <h2>Explanation</h2>
          {selectedIssue ? (
            <dl>
              <dt>WHAT</dt>
              <dd>{selectedIssue.what ?? selectedIssue.title}</dd>
              <dt>WHERE</dt>
              <dd>{selectedIssue.where ?? selectedIssue.element_key ?? 'Diagram-wide'}</dd>
              <dt>WHY</dt>
              <dd>{selectedIssue.why ?? selectedIssue.description}</dd>
              <dt>FIX</dt>
              <dd>{selectedIssue.fix ?? selectedIssue.fix_suggestion}</dd>
            </dl>
          ) : (
            <p>No supported structural issues detected.</p>
          )}
        </section>
        <section className="metadata-panel">
          <div>
            <h2>Evidence</h2>
            {evidenceEntries.length > 0 ? (
              <ul className="evidence-list">
                {evidenceEntries.map(([key, value]) => (
                  <li key={key}>
                    <span>{key.replaceAll('_', ' ')}</span>
                    <strong>{value}</strong>
                  </li>
                ))}
              </ul>
            ) : (
              <p>No classification evidence was returned.</p>
            )}
          </div>
          <div>
            <h2>Selection</h2>
            {selectedElement ? (
              <dl>
                <dt>Element</dt>
                <dd>{elementDisplayName(selectedElement)}</dd>
                <dt>Type</dt>
                <dd>{selectedElement.element_type}</dd>
                <dt>Confidence</dt>
                <dd>{confidenceLabel(selectedElement.confidence)}</dd>
              </dl>
            ) : (
              <p>{analysis.preprocessing
                ? `Processed ${analysis.preprocessing.original_width} x ${analysis.preprocessing.original_height} into ${analysis.preprocessing.processed_width} x ${analysis.preprocessing.processed_height}.`
                : 'Select an issue to inspect its detected element.'}</p>
            )}
          </div>
        </section>
        <section className="what-if-panel">
          <form className="what-if-shell" onSubmit={submitQuery}>
            <GitBranch size={20} aria-hidden="true" />
            <input
              value={queryText}
              placeholder="Ask a question about this diagram..."
              disabled={!sessionToken || isQuerying}
              onChange={(event) => setQueryText(event.target.value)}
            />
            <button className="primary-button" type="submit" disabled={!sessionToken || !queryText.trim() || isQuerying}>
              {isQuerying && <Loader2 className="button-spinner" size={16} aria-hidden="true" />}
              {isQuerying ? 'Asking...' : 'Ask'}
            </button>
          </form>
          {(queryResult?.answer || queryError) && (
            <div className={queryError ? 'query-answer error' : 'query-answer'} aria-live="polite">
              {queryError || queryResult?.answer}
            </div>
          )}
        </section>
      </div>
    </section>
  );
}

function WorkflowPreview() {
  return (
    <section className="dashboard-preview view-enter" aria-label="Analysis workflow preview">
      <div className="analysis-canvas">
        <div className="diagram-placeholder">
          <span className="node start">Start</span>
          <span className="node process">Process</span>
          <span className="node decision">Decision</span>
          <span className="node end">End</span>
          <span className="connector one" />
          <span className="connector two" />
          <span className="connector three" />
        </div>
      </div>
      <aside className="issues-panel">
        <h2>Processing</h2>
        <ol>
          {processingStages.map((stage, index) => (
            <li key={stage} className={index === 0 ? 'active' : ''}>
              <span>{index + 1}</span>
              {stage}
            </li>
          ))}
        </ol>
      </aside>
    </section>
  );
}

function MobileScanApp({ token }: { token: string }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fallbackInputRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState('Open your camera to scan your diagram.');
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const [capturedBlob, setCapturedBlob] = useState<Blob | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  async function openCamera() {
    try {
      await requestJson(`${API_BASE_URL}/scan/${token}/connect`, { method: 'POST' }, 'Could not connect this phone.');
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' } },
        audio: false,
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setStatus('Position the diagram clearly, then capture.');
    } catch {
      setStatus('Camera or backend access is required. Try again or upload from this phone.');
    }
  }

  function useFallbackPhoto(file: File | undefined) {
    if (!file) return;
    const validationMessage = validateUploadFile(file);
    if (validationMessage) {
      setStatus(validationMessage);
      return;
    }
    setCapturedBlob(file);
    setPhotoUrl(URL.createObjectURL(file));
    setStatus('Preview your photo before sending.');
  }

  function capturePhoto() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    const context = canvas.getContext('2d');
    context?.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (!blob) {
        setStatus('We could not capture this photo.');
        return;
      }
      setCapturedBlob(blob);
      setPhotoUrl(URL.createObjectURL(blob));
      setStatus('Preview your photo before sending.');
    }, 'image/jpeg', 0.92);
  }

  async function uploadPhoto() {
    if (!capturedBlob) return;
    setIsUploading(true);
    setStatus('Uploading your diagram...');

    const file = new File([capturedBlob], 'phone-scan.jpg', { type: capturedBlob.type || 'image/jpeg' });
    const formData = new FormData();
    formData.append('file', file);

    try {
      await requestJson(
        `${API_BASE_URL}/scan/${token}/upload`,
        {
          method: 'POST',
          body: formData,
        },
        'Upload failed.',
      );
      setStatus('Diagram sent successfully. Return to your laptop.');
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Upload failed. Check that both devices are on the same network.');
    } finally {
      setIsUploading(false);
    }
  }

  function retake() {
    if (photoUrl) URL.revokeObjectURL(photoUrl);
    setPhotoUrl(null);
    setCapturedBlob(null);
    setStatus('Position the diagram clearly, then capture.');
  }

  return (
    <main className="mobile-shell view-enter">
      <div className="mobile-brand">
        <ScanLine size={22} aria-hidden="true" />
        <span>VisuLogic</span>
      </div>
      <h1>Scan your diagram</h1>
      <p>{status}</p>
      {photoUrl ? (
        <img className="photo-preview" src={photoUrl} alt="Captured diagram preview" />
      ) : (
        <video ref={videoRef} className="camera-preview" playsInline muted />
      )}
      <canvas ref={canvasRef} hidden />
      <input
        ref={fallbackInputRef}
        type="file"
        accept="image/png,image/jpeg"
        capture="environment"
        className="file-input"
        onChange={(event) => useFallbackPhoto(event.target.files?.[0])}
      />
      <div className="mobile-actions">
        {!photoUrl && (
          <>
            <button className="secondary-button" type="button" onClick={openCamera}>
              Open Camera
            </button>
            <button className="primary-button" type="button" onClick={capturePhoto}>
              Capture
            </button>
            <button
              className="secondary-button wide-action"
              type="button"
              onClick={() => fallbackInputRef.current?.click()}
            >
              Upload Photo Instead
            </button>
          </>
        )}
        {photoUrl && (
          <>
            <button className="secondary-button" type="button" onClick={retake}>
              Retake
            </button>
            <button className="primary-button" type="button" disabled={isUploading} onClick={uploadPhoto}>
              {isUploading && <Loader2 className="button-spinner" size={16} aria-hidden="true" />}
              {isUploading ? 'Uploading...' : 'Use Photo'}
            </button>
          </>
        )}
      </div>
    </main>
  );
}

function Router() {
  const match = window.location.pathname.match(/^\/mobile\/scan\/([^/]+)$/);
  if (match) {
    return <MobileScanApp token={match[1]} />;
  }
  return <DesktopApp />;
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Router />
  </React.StrictMode>,
);
