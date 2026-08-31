// ============================================================
// Lentis Gallery — Camera Utilities
// ============================================================
// Pure functions for camera API detection, permission handling,
// and media capture. No React dependencies.
// ============================================================

/** Camera permission states */
export type CameraPermission = 'checking' | 'prompt' | 'granted' | 'denied' | 'unavailable';

/** Camera error types mapped from browser errors */
export type CameraErrorType =
  | 'permission-denied'
  | 'no-camera'
  | 'in-use'
  | 'overconstrained'
  | 'unavailable'
  | 'https-required'
  | 'unknown';

export interface CameraError {
  type: CameraErrorType;
  message: string;
  technical?: string;
}

/**
 * Check if the camera API is available in this browser.
 */
export function isCameraSupported(): boolean {
  return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
}

/**
 * Check if we're in a secure context (required for camera on most browsers).
 * localhost is considered secure for development.
 */
export function isSecureContext(): boolean {
  return window.isSecureContext;
}

/**
 * Map a browser error to a user-friendly camera error.
 */
export function mapCameraError(error: unknown): CameraError {
  const name = error instanceof DOMException ? error.name : '';
  const message = error instanceof Error ? error.message : String(error);

  // NotAllowedError = permission denied
  if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
    return {
      type: 'permission-denied',
      message: 'Camera permission was denied. Please allow camera access in your browser settings and try again.',
      technical: message,
    };
  }

  // NotFoundError = no camera device
  if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
    return {
      type: 'no-camera',
      message: 'No camera was found on this device. You can still upload photos from your device.',
      technical: message,
    };
  }

  // NotReadableError = camera in use by another app
  if (name === 'NotReadableError' || name === 'TrackStartError') {
    return {
      type: 'in-use',
      message: 'Your camera is currently being used by another application. Please close other camera apps and try again.',
      technical: message,
    };
  }

  // OverconstrainedError = requested constraints can't be satisfied
  if (name === 'OverconstrainedError') {
    return {
      type: 'overconstrained',
      message: 'This camera does not support the requested configuration. Trying with default settings.',
      technical: message,
    };
  }

  // SecurityError = insecure context
  if (name === 'SecurityError') {
    return {
      type: 'https-required',
      message: 'Camera requires a secure connection (HTTPS). Please open this event using HTTPS.',
      technical: message,
    };
  }

  // AbortError = operation aborted
  if (name === 'AbortError') {
    return {
      type: 'unavailable',
      message: 'Camera operation was interrupted. Please try again.',
      technical: message,
    };
  }

  // TypeError = invalid constraints or API issue
  if (name === 'TypeError') {
    return {
      type: 'unavailable',
      message: 'Camera is unavailable in this browser. You can still upload photos from your device.',
      technical: message,
    };
  }

  // Default
  return {
    type: 'unknown',
    message: 'Could not access your camera. You can still upload photos from your device.',
    technical: message,
  };
}

/**
 * Get the current camera permission state (if the Permissions API is available).
 */
export async function checkCameraPermission(): Promise<CameraPermission> {
  // Check if Permissions API is available
  if (!navigator.permissions || !navigator.permissions.query) {
    // Permissions API not available — we'll find out when we call getUserMedia
    return 'prompt';
  }

  try {
    const result = await navigator.permissions.query({ name: 'camera' as PermissionName });
    switch (result.state) {
      case 'granted':
        return 'granted';
      case 'denied':
        return 'denied';
      case 'prompt':
      default:
        return 'prompt';
    }
  } catch {
    // Permissions API query failed — fall through
    return 'prompt';
  }
}

/**
 * Build getUserMedia constraints for a given facing mode.
 */
export function buildConstraints(
  facingMode: 'user' | 'environment',
  options?: { width?: number; height?: number }
): MediaStreamConstraints {
  return {
    audio: false,
    video: {
      facingMode: { ideal: facingMode },
      width: { ideal: options?.width ?? 1920 },
      height: { ideal: options?.height ?? 1080 },
    },
  };
}

/**
 * Capture a photo from a video element as a JPEG Blob.
 * Returns null if capture fails.
 */
export function capturePhotoFromVideo(
  video: HTMLVideoElement,
  quality: number = 0.92
): Promise<File | null> {
  return new Promise((resolve) => {
    if (!video || !video.videoWidth || !video.videoHeight) {
      resolve(null);
      return;
    }

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext('2d');
    if (!ctx) {
      resolve(null);
      return;
    }

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      (blob) => {
        if (!blob) {
          resolve(null);
          return;
        }
        const timestamp = Date.now();
        const file = new File([blob], `lentis-photo-${timestamp}.jpg`, {
          type: 'image/jpeg',
          lastModified: timestamp,
        });
        resolve(file);
      },
      'image/jpeg',
      quality
    );
  });
}

/**
 * Stop all tracks in a MediaStream.
 */
export function stopStream(stream: MediaStream | null): void {
  if (!stream) return;
  stream.getTracks().forEach((track) => {
    try {
      track.stop();
    } catch {
      // Track may already be stopped
    }
  });
}
