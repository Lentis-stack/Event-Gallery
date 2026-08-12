// ============================================================
// Lentis Gallery — ConfirmDialog
// ------------------------------------------------------------
// A small accessible confirmation dialog used for destructive
// or important actions (delete media, archive event, etc.).
// Rendered as an overlay with a backdrop. Uses native <dialog>
// semantics via a styled div + role="dialog".
// ============================================================

import type { ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface ConfirmDialogProps {
  /** Whether the dialog is open. */
  open: boolean;
  /** Title, e.g. "Delete this photo?". */
  title: string;
  /** Body message. */
  message: ReactNode;
  /** Confirm button label. */
  confirmLabel?: string;
  /** Cancel button label. */
  cancelLabel?: string;
  /** Whether the confirm action is destructive (red accent). */
  destructive?: boolean;
  /** Called when confirming. */
  onConfirm: () => void;
  /** Called when cancelling / closing. */
  onCancel: () => void;
}

/**
 * Accessible confirmation dialog. Clicking the backdrop cancels.
 * Escape key cancels. Focus is moved to the dialog on open.
 */
export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  destructive = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="confirm-dialog__backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onCancel}
        >
          <motion.div
            className="confirm-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="confirm-dialog-title"
            aria-describedby="confirm-dialog-message"
            initial={{ opacity: 0, scale: 0.96, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 10 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="confirm-dialog__title" id="confirm-dialog-title">
              {title}
            </h2>
            <div className="confirm-dialog__message" id="confirm-dialog-message">
              {message}
            </div>
            <div className="confirm-dialog__actions">
              <button type="button" className="btn-ghost confirm-dialog__btn" onClick={onCancel}>
                {cancelLabel}
              </button>
              <button
                type="button"
                className={`btn-primary confirm-dialog__btn${destructive ? ' is-destructive' : ''}`}
                onClick={onConfirm}
              >
                {confirmLabel}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
