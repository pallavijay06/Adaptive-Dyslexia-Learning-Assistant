import { useCallback, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDocument } from '../contexts/DocumentContext';
import { uploadService } from '../services/uploadService';

const ACCEPTED_TYPES = ['.pdf', '.ppt', '.pptx', '.doc', '.docx'];
const ACCEPTED_MIME = [
  'application/pdf',
  'application/vnd.ms-powerpoint',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
];

function isAccepted(file) {
  if (ACCEPTED_MIME.includes(file.type)) return true;
  const ext = '.' + file.name.split('.').pop().toLowerCase();
  return ACCEPTED_TYPES.includes(ext);
}

export default function UploadRoute() {
  const navigate = useNavigate();
  const { setActiveDocument } = useDocument();
  const fileInputRef = useRef(null);

  const [selectedFile, setSelectedFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [error, setError] = useState('');

  const selectFile = (file) => {
    if (!isAccepted(file)) {
      setError(`Unsupported file type. Please upload: ${ACCEPTED_TYPES.join(', ')}`);
      return;
    }
    setError('');
    setSelectedFile(file);
    setUploadResult(null);
  };

  const handleFileInput = (e) => {
    const file = e.target.files?.[0];
    if (file) selectFile(file);
  };

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) selectFile(file);
  }, []);

  const handleDragOver = (e) => { e.preventDefault(); setDragging(true); };
  const handleDragLeave = () => setDragging(false);

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setError('');
    try {
      const data = await uploadService.uploadDocument(selectedFile);
      setActiveDocument({ ...data.document, document_id: data.document_id });
      setUploadResult(data);
    } catch (err) {
      setError(err.message || 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  // ── Success screen ────────────────────────────────────────────────────────
  if (uploadResult) {
    const doc = uploadResult.document;
    return (
      <div className="upload-success-page">
        <section className="card upload-success-card" aria-labelledby="upload-success-heading">
          <div className="upload-success-icon" aria-hidden="true">✓</div>
          <h2 id="upload-success-heading">Document ready</h2>
          <p className="upload-success-sub">Your document has been processed successfully.</p>

          <dl className="upload-meta-list">
            <div>
              <dt>File name</dt>
              <dd>{uploadResult.filename}</dd>
            </div>
            <div>
              <dt>File type</dt>
              <dd>{doc.file_type?.toUpperCase()}</dd>
            </div>
            <div>
              <dt>Characters extracted</dt>
              <dd>{uploadResult.characters_extracted?.toLocaleString()}</dd>
            </div>
            <div>
              <dt>Uploaded</dt>
              <dd>{new Date(doc.upload_time).toLocaleString()}</dd>
            </div>
          </dl>

          <div className="upload-success-actions">
            <button
              type="button"
              className="button button-secondary"
              onClick={() => navigate('/dashboard')}
            >
              Return to Dashboard
            </button>
            <button
              type="button"
              className="button button-primary"
              onClick={() => navigate('/learning-selection')}
            >
              Continue
            </button>
          </div>
        </section>
      </div>
    );
  }

  // ── Upload form ───────────────────────────────────────────────────────────
  return (
    <div className="upload-page">
      <section className="card upload-card" aria-labelledby="upload-heading">
        <h2 id="upload-heading">Upload Learning Material</h2>
        <p className="upload-sub">
          Supported formats: {ACCEPTED_TYPES.join(', ')}
        </p>

        {/* Drag & Drop zone */}
        <div
          className={`drop-zone${dragging ? ' drop-zone--active' : ''}${selectedFile ? ' drop-zone--selected' : ''}`}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          aria-label="Drop a file here or click to browse"
          onKeyDown={(e) => e.key === 'Enter' && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_TYPES.join(',')}
            onChange={handleFileInput}
            style={{ display: 'none' }}
            aria-hidden="true"
          />
          {selectedFile ? (
            <div className="drop-zone-file">
              <span className="drop-zone-icon" aria-hidden="true">📄</span>
              <span className="drop-zone-filename">{selectedFile.name}</span>
              <span className="drop-zone-size">
                {(selectedFile.size / 1024).toFixed(1)} KB
              </span>
            </div>
          ) : (
            <div className="drop-zone-prompt">
              <span className="drop-zone-icon" aria-hidden="true">📂</span>
              <span>Drag &amp; drop your file here</span>
              <span className="drop-zone-or">or click to browse</span>
            </div>
          )}
        </div>

        {error && (
          <p className="upload-error" role="alert">{error}</p>
        )}

        <div className="upload-actions">
          <button
            type="button"
            className="button button-secondary"
            onClick={() => navigate('/dashboard')}
            disabled={uploading}
          >
            Cancel
          </button>
          <button
            type="button"
            className="button button-primary"
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
            aria-busy={uploading}
          >
            {uploading ? 'Processing…' : 'Upload'}
          </button>
        </div>

        {uploading && (
          <p className="upload-loading" role="status" aria-live="polite">
            Uploading and processing your document…
          </p>
        )}
      </section>
    </div>
  );
}
