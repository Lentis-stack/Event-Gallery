import { ChangeEvent, useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import FilmShell from '../components/FilmShell';
import EventBranding from '../components/EventBranding';
import PageTransition from '../components/PageTransition';
import SiteFooter from '../components/SiteFooter';
import { eventConfig } from '../config/event';

type CaptureKind = 'photo' | 'video' | 'file';

interface LocalMedia {
  id: string;
  url: string;
  kind: CaptureKind;
  name: string;
}

let mediaIdCounter = 0;
const nextMediaId = () => `media-${Date.now()}-${++mediaIdCounter}`;

/** Media remains on-device until the future Python upload API is introduced. */
export default function CameraPage() {
  const navigate = useNavigate();
  const guestName = sessionStorage.getItem('guestName');
  const videoRef = useRef<HTMLVideoElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const recordedChunksRef = useRef<Blob[]>([]);
  const [cameraState, setCameraState] = useState<'idle' | 'starting' | 'ready' | 'error'>('idle');
  const [cameraError, setCameraError] = useState('');
  const [facingMode, setFacingMode] = useState<'environment' | 'user'>('environment');
  const [isRecording, setIsRecording] = useState(false);
  const [mediaList, setMediaList] = useState<LocalMedia[]>([]);

  const stopCamera = useCallback(() => {
    recorderRef.current?.stop();
    recorderRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setIsRecording(false);
  }, []);

  useEffect(() => {
    if (!guestName) navigate('/guest', { replace: true });
  }, [guestName, navigate]);

  useEffect(() => () => stopCamera(), [stopCamera]);

  // Clean up all object URLs on unmount.
  useEffect(() => {
    return () => {
      mediaList.forEach((item) => URL.revokeObjectURL(item.url));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const addLocalMedia = (blob: Blob, kind: CaptureKind, name: string) => {
    const url = URL.createObjectURL(blob);
    setMediaList((current) => [...current, { id: nextMediaId(), url, kind, name }]);
  };

  const removeMedia = (id: string) => {
    setMediaList((current) => {
      const target = current.find((item) => item.id === id);
      if (target) URL.revokeObjectURL(target.url);
      return current.filter((item) => item.id !== id);
    });
  };

  const startCamera = async (requestedFacingMode = facingMode) => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraError('Camera access is not available in this browser. You can still choose a photo or video from your device.');
      setCameraState('error');
      return;
    }

    stopCamera();
    setCameraError('');
    setCameraState('starting');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: { facingMode: { ideal: requestedFacingMode } },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCameraState('ready');
    } catch {
      setCameraError('We could not open your camera. Allow camera access, then try again—or choose a file instead.');
      setCameraState('error');
    }
  };

  const switchCamera = async () => {
    const nextFacingMode = facingMode === 'environment' ? 'user' : 'environment';
    setFacingMode(nextFacingMode);
    await startCamera(nextFacingMode);
  };

  const capturePhoto = () => {
    const video = videoRef.current;
    if (!video || !video.videoWidth || !video.videoHeight) return;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d')?.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (blob) addLocalMedia(blob, 'photo', `lentis-photo-${Date.now()}.jpg`);
    }, 'image/jpeg', 0.92);
  };

  const toggleRecording = () => {
    if (isRecording) {
      recorderRef.current?.stop();
      return;
    }
    if (!streamRef.current || !window.MediaRecorder) {
      setCameraError('Video recording is not supported in this browser. You can still upload a video from your device.');
      return;
    }

    recordedChunksRef.current = [];
    const recorder = new MediaRecorder(streamRef.current);
    recorderRef.current = recorder;
    recorder.ondataavailable = (event) => {
      if (event.data.size) recordedChunksRef.current.push(event.data);
    };
    recorder.onstop = () => {
      const videoBlob = new Blob(recordedChunksRef.current, { type: recorder.mimeType || 'video/webm' });
      if (videoBlob.size) addLocalMedia(videoBlob, 'video', `lentis-video-${Date.now()}.webm`);
      setIsRecording(false);
      recorderRef.current = null;
    };
    recorder.start();
    setIsRecording(true);
  };

  const chooseFile = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    files.forEach((file) => {
      addLocalMedia(file, file.type.startsWith('video/') ? 'video' : 'file', file.name);
    });
    event.target.value = '';
  };

  return (
    <PageTransition>
      <FilmShell staticImage={eventConfig.images[0]?.src}>
        <div className="camera-page">
          <header className="page-top">
            <Link to="/guest" className="back-link" aria-label="Back to guest entry">← Back</Link>
          </header>

          <div className="page-center">
            <EventBranding showPlatform={false} as="h2" className="page-center__branding" />
            <div className="camera-page__greeting">
              <p className="camera-page__welcome">Welcome, {guestName}.</p>
              <p className="page-center__muted">Capture the moments that matter.</p>
            </div>

            <motion.div className="camera-unit" initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, ease: [0.22, 1, 0.36, 1], delay: 0.5 }}>
              <div className="camera-unit__frame">
                {cameraState === 'ready' ? (
                  <video ref={videoRef} className="camera-live" autoPlay muted playsInline aria-label="Live camera preview" />
                ) : (
                  <div className="camera-unit__placeholder"><span className="camera-unit__ring" /><span className="camera-unit__label">{cameraState === 'starting' ? 'Opening camera' : 'Your camera preview'}</span></div>
                )}
              </div>

              <div className="camera-page__actions">
                {cameraState !== 'ready' && <button type="button" className="btn-primary camera-page__cta" onClick={() => startCamera()} disabled={cameraState === 'starting'}>Enable camera</button>}
                {cameraState === 'ready' && <>
                  <button type="button" className="btn-primary camera-page__cta" onClick={capturePhoto}>Take photo</button>
                  <button type="button" className={`btn-ghost camera-page__cta${isRecording ? ' is-recording' : ''}`} onClick={toggleRecording}>{isRecording ? 'Stop recording' : 'Record video'}</button>
                  <button type="button" className="btn-ghost camera-page__cta camera-page__switch" onClick={switchCamera}>Switch camera</button>
                </>}
                <button type="button" className="btn-ghost camera-page__cta" onClick={() => fileInputRef.current?.click()}>Choose from device</button>
                <input ref={fileInputRef} className="sr-only" type="file" accept="image/*,video/*" multiple onChange={chooseFile} />
              </div>

              {cameraError && <p className="camera-page__error" role="alert">{cameraError}</p>}

              {mediaList.length > 0 && (
                <div className="media-section">
                  <div className="media-section__header">
                    <span className="media-section__count" aria-live="polite">
                      {mediaList.length} {mediaList.length === 1 ? 'item' : 'items'} selected
                    </span>
                  </div>
                  <ul className="media-grid">
                    {mediaList.map((item) => (
                      <li key={item.id} className="media-item">
                        {item.kind === 'video' ? (
                          <video src={item.url} controls playsInline aria-label={`Video preview: ${item.name}`} />
                        ) : (
                          <img src={item.url} alt={`Selected photo: ${item.name}`} />
                        )}
                        <span className="media-item__name">{item.name}</span>
                        <button
                          type="button"
                          className="media-item__remove"
                          onClick={() => removeMedia(item.id)}
                          aria-label={`Remove ${item.name}`}
                        >
                          ×
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <p className="camera-page__note">Your photos and videos stay on this device for now. Upload will be connected in the next backend phase.</p>
            </motion.div>
          </div>
          <SiteFooter />
        </div>
      </FilmShell>
    </PageTransition>
  );
}
