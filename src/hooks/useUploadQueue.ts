// ============================================================
// Lentis Gallery — Upload Queue Hook
// ============================================================
// Manages a queue of media uploads with:
//   - Sequential upload with status tracking per item
//   - Offline queuing and automatic retry on reconnect
//   - No blocking of camera capture during uploads
// ============================================================

import { useState, useCallback, useRef, useEffect } from 'react';

export type UploadStatus = 'queued' | 'uploading' | 'uploaded' | 'failed';

export interface UploadQueueItem {
  id: string;
  file: File;
  name: string;
  type: 'photo' | 'video';
  status: UploadStatus;
  /** Error message if status is 'failed'. */
  error?: string;
  /** Timestamp when this item was queued. */
  queuedAt: number;
}

interface UseUploadQueueOptions {
  /** Called to actually perform the upload. Should throw on failure. */
  onUpload: (file: File) => Promise<void>;
  /** Called after each successful upload (for gallery refresh, etc.). */
  onComplete?: () => void;
}

export function useUploadQueue({ onUpload, onComplete }: UseUploadQueueOptions) {
  const [items, setItems] = useState<UploadQueueItem[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const processingRef = useRef(false);
  const queueRef = useRef<UploadQueueItem[]>([]);

  // Keep ref in sync with state
  useEffect(() => {
    queueRef.current = items;
  }, [items]);

  // ── Online/offline detection ──
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // ── Process queue sequentially ──
  const processQueue = useCallback(async () => {
    if (processingRef.current) return;
    processingRef.current = true;
    setIsUploading(true);

    while (true) {
      // Find next queued item
      const current = queueRef.current;
      const nextIdx = current.findIndex((i) => i.status === 'queued');
      if (nextIdx === -1) break;

      const item = current[nextIdx];

      // Mark as uploading
      setItems((prev) =>
        prev.map((i) => (i.id === item.id ? { ...i, status: 'uploading' as const } : i))
      );

      try {
        await onUpload(item.file);
        setItems((prev) =>
          prev.map((i) => (i.id === item.id ? { ...i, status: 'uploaded' as const } : i))
        );
        onComplete?.();
      } catch (err: any) {
        setItems((prev) =>
          prev.map((i) =>
            i.id === item.id
              ? { ...i, status: 'failed' as const, error: err?.message || 'Upload failed' }
              : i
          )
        );
      }
    }

    setIsUploading(false);
    processingRef.current = false;
  }, [onUpload, onComplete]);

  // ── Trigger processing when queue changes or we come back online ──
  useEffect(() => {
    if (isOnline && items.some((i) => i.status === 'queued')) {
      processQueue();
    }
  }, [isOnline, items, processQueue]);

  // ── Add files to queue ──
  const enqueue = useCallback(
    (files: File[]) => {
      const newItems: UploadQueueItem[] = files.map((file) => ({
        id: `upload-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        file,
        name: file.name,
        type: file.type.startsWith('video') ? 'video' : 'photo',
        status: 'queued' as const,
        queuedAt: Date.now(),
      }));

      setItems((prev) => [...prev, ...newItems]);

      // Kick off processing
      setTimeout(() => processQueue(), 50);
    },
    [processQueue]
  );

  // ── Retry a single failed item ──
  const retry = useCallback(
    (id: string) => {
      setItems((prev) =>
        prev.map((i) => (i.id === id ? { ...i, status: 'queued' as const, error: undefined } : i))
      );
      setTimeout(() => processQueue(), 50);
    },
    [processQueue]
  );

  // ── Retry all failed items ──
  const retryAll = useCallback(() => {
    setItems((prev) =>
      prev.map((i) => (i.status === 'failed' ? { ...i, status: 'queued' as const, error: undefined } : i))
    );
    setTimeout(() => processQueue(), 50);
  }, [processQueue]);

  // ── Remove a specific item ──
  const remove = useCallback((id: string) => {
    setItems((prev) => prev.filter((i) => i.id !== id));
  }, []);

  // ── Clear completed items ──
  const clearCompleted = useCallback(() => {
    setItems((prev) => prev.filter((i) => i.status !== 'uploaded'));
  }, []);

  // ── Auto-clear uploaded items after a delay ──
  useEffect(() => {
    const uploadedIds = items
      .filter((i) => i.status === 'uploaded')
      .map((i) => i.id);
    if (uploadedIds.length === 0) return;

    const timer = setTimeout(() => {
      setItems((prev) => prev.filter((i) => !uploadedIds.includes(i.id)));
    }, 3000);

    return () => clearTimeout(timer);
  }, [items]);

  return {
    items,
    isUploading,
    isOnline,
    enqueue,
    retry,
    retryAll,
    remove,
    clearCompleted,
    pendingCount: items.filter((i) => i.status === 'queued' || i.status === 'uploading').length,
    failedCount: items.filter((i) => i.status === 'failed').length,
    completedCount: items.filter((i) => i.status === 'uploaded').length,
  };
}
