// ============================================================
// Lentis Gallery — GalleryMediaCard
// ------------------------------------------------------------
// A single media item card in the Host Gallery view.
// Shows the thumbnail, guest name, upload time, status badge,
// and action buttons (approve / hide / delete) based on the
// current moderation status.
// ============================================================

import type { GalleryMedia, MediaStatus } from '../../types/gallery';
import StatusBadge from './StatusBadge';

interface GalleryMediaCardProps {
  media: GalleryMedia;
  /** Called when the moderation status changes. */
  onStatusChange: (id: string, status: MediaStatus) => void;
  /** Called when the item is deleted. */
  onDelete: (id: string) => void;
}

/**
 * Card for a single photo/video upload with moderation actions.
 */
export default function GalleryMediaCard({ media, onStatusChange, onDelete }: GalleryMediaCardProps) {
  const isVideo = media.type === 'video';

  return (
    <article className="gallery-card">
      <div className="gallery-card__media">
        {isVideo ? (
          <video src={media.src} muted playsInline aria-label={media.caption ?? `${media.guestName}'s video`} />
        ) : (
          <img src={media.src} alt={media.caption ?? `${media.guestName}'s photo`} loading="lazy" />
        )}
        {isVideo && <span className="gallery-card__type">Video</span>}
      </div>

      <div className="gallery-card__body">
        <div className="gallery-card__meta">
          <span className="gallery-card__guest">{media.guestName}</span>
          <span className="gallery-card__time">{media.uploadedAt}</span>
        </div>
        {media.caption && <p className="gallery-card__caption">{media.caption}</p>}
        <div className="gallery-card__row">
          <StatusBadge status={media.status} />
        </div>
        <div className="gallery-card__actions">
          {media.status !== 'approved' && (
            <button
              type="button"
              className="gallery-card__btn is-approve"
              onClick={() => onStatusChange(media.id, 'approved')}
            >
              Approve
            </button>
          )}
          {media.status !== 'hidden' && (
            <button
              type="button"
              className="gallery-card__btn is-hide"
              onClick={() => onStatusChange(media.id, 'hidden')}
            >
              Hide
            </button>
          )}
          <button
            type="button"
            className="gallery-card__btn is-delete"
            onClick={() => onDelete(media.id)}
          >
            Delete
          </button>
        </div>
      </div>
    </article>
  );
}
