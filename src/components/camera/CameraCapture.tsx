// ============================================================
// Lentis Gallery — Camera Capture Component
// ============================================================
// Premium phone-camera UI for guests. Features:
//   - 3:4 portrait camera frame with curved corners
//   - Phone-style controls: Gallery | Shutter | Flip Camera
//   - Photo/video mode toggle
//   - Auto-upload on capture
//   - Proper MediaStream lifecycle management
//   - Camera switching with smooth transition
// ============================================================

import { useCallback, useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  isCameraSupported,
  isSecureContext,
  checkCameraPermission,
  buildConstraints,
  capturePhotoFromVideo,
  stopStream,
  mapCameraError,
  type CameraError,
} from './camera.utils';

interface CameraCaptureProps {
  /** Called when a photo or video is captured and ready for upload. */
  onCapture: (file: File) => void;
  /** Called when device files are selected for upload. */
  onDeviceUpload?: (files: File[]) => void;
  /** Called when the user wants to view their gallery. */
  onOpenGallery: () => void;
  /** Media count badge for the gallery button. */
  mediaCount: number;
  /** Guest name displayed in the UI. */
  guestName: string;
}

type CameraState = 'idle' | 'starting' | 'ready' | 'error';
type CaptureMode = 'photo' | 'video';

export default function CameraCapture({
  onCapture,
  onDeviceUpload,
  onOpenGallery,
  mediaCount,
  guestName,
}: CameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const [state, setState] = useState<CameraState>('idle');
  const [facingMode, setFacingMode] = useState<'user' | 'environment'>('environment');
  const [error, setError] = useState<CameraError | null>(null);
  const [captureMode, setCaptureMode] = useState<CaptureMode>('photo');
  const [flashVisible, setFlashVisible] = useState(false);

  // Video recording state
  const [isRecording, setIsRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const recordingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Device file upload
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Cleanup: stop all tracks on unmount
  useEffect(() => {
    return () => {
      stopStream(streamRef.current);
      streamRef.current = null;
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
      }
    };
  }, []);

  // Check camera support and permission on mount
  useEffect(() => {
    async function init() {
      if (!isCameraSupported()) {
        setError({
          type: 'unavailable',
          message: 'Camera is not supported in this browser. You can still upload photos from your device.',
        });
        setState('error');
        return;
      }

      if (!isSecureContext()) {
        setError({
          type: 'https-required',
          message: 'Camera requires a secure connection (HTTPS). Please open this event using HTTPS.',
        });
        setState('error');
        return;
      }

      const perm = await checkCameraPermission();

      if (perm === 'denied') {
        setError({
          type: 'permission-denied',
          message: 'Camera permission was denied. Please allow camera access in your browser settings and try again.',
        });
        setState('error');
        return;
      }

      startCamera();
    }
    init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startCamera = useCallback(async (mode = facingMode) => {
    if (!isCameraSupported()) {
      setError({ type: 'unavailable', message: 'Camera not supported.' });
      setState('error');
      return;
    }

    // Stop any existing stream
    stopStream(streamRef.current);
    streamRef.current = null;

    setState('starting');
    setError(null);

    try {
      const constraints = buildConstraints(mode);
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      setState('ready');
    } catch (err) {
      const cameraError = mapCameraError(err);
      setError(cameraError);
      setState('error');
    }
  }, [facingMode]);

  const switchCamera = useCallback(async () => {
    const nextMode = facingMode === 'environment' ? 'user' : 'environment';
    setFacingMode(nextMode);
    await startCamera(nextMode);
  }, [facingMode, startCamera]);

  // ---- Flash effect for photo capture ----
  const triggerFlash = useCallback(() => {
    setFlashVisible(true);
    setTimeout(() => setFlashVisible(false), 150);
  }, []);

  // ---- Photo capture (auto-upload) ----
  const handleCapturePhoto = useCallback(async () => {
    const video = videoRef.current;
    if (!video) return;

    triggerFlash();

    const file = await capturePhotoFromVideo(video);
    if (!file) {
      setError({ type: 'unknown', message: 'Failed to capture photo. Please try again.' });
      return;
    }

    onCapture(file);
  }, [onCapture, triggerFlash]);

  // ---- Video recording ----
  const startRecording = useCallback(() => {
    const stream = streamRef.current;
    if (!stream) return;

    chunksRef.current = [];

    const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp9')
      ? 'video/webm;codecs=vp9'
      : MediaRecorder.isTypeSupported('video/webm;codecs=vp8')
        ? 'video/webm;codecs=vp8'
        : 'video/webm';

    try {
      const recorder = new MediaRecorder(stream, { mimeType });
      recorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeType });
        const file = new File([blob], `lentis-video-${Date.now()}.webm`, { type: mimeType });
        onCapture(file);
      };

      recorder.start(100);
      setIsRecording(true);
      setRecordingDuration(0);

      recordingTimerRef.current = setInterval(() => {
        setRecordingDuration((prev) => prev + 1);
      }, 1000);
    } catch {
      setError({ type: 'unknown', message: 'Video recording is not supported in this browser.' });
    }
  }, [onCapture]);

  const stopRecording = useCallback(() => {
    if (recorderRef.current && recorderRef.current.state === 'recording') {
      recorderRef.current.stop();
    }
    setIsRecording(false);
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
  }, []);

  const handleShutterPress = useCallback(() => {
    if (captureMode === 'photo') {
      handleCapturePhoto();
    } else {
      if (isRecording) {
        stopRecording();
      } else {
        startRecording();
      }
    }
  }, [captureMode, isRecording, handleCapturePhoto, startRecording, stopRecording]);

  const formatDuration = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  // ---- Render ----

  return (
    <div className="phone-camera">
      {/* Camera viewport — 3:4 frame with curved corners */}
      <div className="phone-camera__frame">
        {/* State overlays */}
        <AnimatePresence>
          {state === 'starting' && (
            <motion.div
              className="phone-camera__overlay"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <div className="phone-camera__spinner" />
              <p className="phone-camera__overlay-text">Opening camera…</p>
            </motion.div>
          )}

          {state === 'error' && error && (
            <motion.div
              className="phone-camera__overlay"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <div className="phone-camera__error-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z" />
                  <circle cx="12" cy="13" r="3" />
                  <line x1="2" y1="2" x2="22" y2="22" stroke="#c98a8a" strokeWidth="2" />
                </svg>
              </div>
              <p className="phone-camera__overlay-text">{error.message}</p>
              <button
                type="button"
                className="phone-camera__retry-btn"
                onClick={() => startCamera()}
              >
                Try Again
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Flash effect for photo capture */}
        <AnimatePresence>
          {flashVisible && (
            <motion.div
              className="phone-camera__flash"
              initial={{ opacity: 0.9 }}
              animate={{ opacity: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
            />
          )}
        </AnimatePresence>

        {/* Video element */}
        <video
          ref={videoRef}
          className="phone-camera__video"
          autoPlay
          playsInline
          muted
          aria-label="Live camera preview"
        />

        {/* Recording indicator */}
        <AnimatePresence>
          {isRecording && (
            <motion.div
              className="phone-camera__rec-badge"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
            >
              <span className="phone-camera__rec-dot" />
              <span className="phone-camera__rec-time">{formatDuration(recordingDuration)}</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Guest name tag */}
        <div className="phone-camera__name-tag">
          <span>{guestName}</span>
        </div>
      </div>

      {/* Mode toggle: PHOTO / VIDEO */}
      <div className="phone-camera__modes">
        <button
          type="button"
          className={`phone-camera__mode-btn ${captureMode === 'photo' ? 'is-active' : ''}`}
          onClick={() => { if (!isRecording) setCaptureMode('photo'); }}
          disabled={isRecording}
          aria-label="Photo mode"
        >
          PHOTO
        </button>
        <button
          type="button"
          className={`phone-camera__mode-btn ${captureMode === 'video' ? 'is-active' : ''}`}
          onClick={() => { if (!isRecording) setCaptureMode('video'); }}
          disabled={isRecording}
          aria-label="Video mode"
        >
          VIDEO
        </button>
      </div>

      {/* Hidden file input for device upload */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*,video/*"
        multiple
        className="phone-camera__file-input"
        onChange={(e) => {
          const files = e.target.files;
          if (files && files.length > 0 && onDeviceUpload) {
            onDeviceUpload(Array.from(files));
          }
          // Reset so the same file can be selected again
          e.target.value = '';
        }}
        aria-label="Upload photos or videos from device"
      />

      {/* Controls: Upload | Gallery | Shutter | Flip */}
      <div className="phone-camera__controls">
        {/* Upload button */}
        <button
          type="button"
          className="phone-camera__upload-btn"
          onClick={() => fileInputRef.current?.click()}
          disabled={isRecording}
          aria-label="Upload photos or videos from device"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
        </button>

        {/* Gallery button */}
        <button
          type="button"
          className="phone-camera__gallery-btn"
          onClick={onOpenGallery}
          aria-label={`View gallery — ${mediaCount} items`}
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <circle cx="8.5" cy="8.5" r="1.5" />
            <polyline points="21 15 16 10 5 21" />
          </svg>
          {mediaCount > 0 && (
            <span className="phone-camera__gallery-badge">{mediaCount}</span>
          )}
        </button>

        {/* Shutter / Record button */}
        <button
          type="button"
          className={`phone-camera__shutter ${isRecording ? 'is-recording' : ''} ${captureMode === 'video' && !isRecording ? 'is-video-mode' : ''}`}
          onClick={handleShutterPress}
          aria-label={isRecording ? 'Stop recording' : captureMode === 'photo' ? 'Take photo' : 'Start recording'}
        >
          <span className="phone-camera__shutter-outer">
            <span className="phone-camera__shutter-inner" />
          </span>
        </button>

        {/* Flip camera button */}
        <button
          type="button"
          className="phone-camera__flip-btn"
          onClick={switchCamera}
          disabled={isRecording}
          aria-label={`Switch to ${facingMode === 'environment' ? 'front' : 'rear'} camera`}
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M11 19H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h5" />
            <path d="M13 5h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-5" />
            <polyline points="16 3 18 1 20 3" />
            <polyline points="8 21 6 23 4 21" />
            <path d="M18.5 8.5A6 6 0 1 0 12 18" />
          </svg>
        </button>
      </div>

      {/* Recording stop button (shown during recording) */}
      <AnimatePresence>
        {isRecording && (
          <motion.div
            className="phone-camera__stop-bar"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
          >
            <button
              type="button"
              className="phone-camera__stop-btn"
              onClick={stopRecording}
              aria-label="Stop recording"
            >
              <span className="phone-camera__stop-square" />
              <span>Stop Recording</span>
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
