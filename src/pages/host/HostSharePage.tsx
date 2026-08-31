// ============================================================
// Lentis Gallery — Host Share Page
// ------------------------------------------------------------
// Lets the host share the event with guests:
//   - QR code (generated client-side with qrcode.react)
//   - Copy guest link button
//   - Download QR code as PNG
//
// Data is provided by the mock host service (frontend-only).
// ============================================================

import { useRef, useState, useEffect } from 'react';
import { QRCodeCanvas } from 'qrcode.react';
import HostLayout from '../../components/host/HostLayout';
import { getAssignedEvent } from '../../services/mockHostService';
import type { Event } from '../../types/event';

export default function HostSharePage() {
  const [event, setEvent] = useState<Event>({ id: '', slug: '', name: 'Loading...', subtitle: '', hostName: '', hostEmail: '', eventDate: '', status: 'draft', theme: 'gold', slides: [], totalUploads: 0, photoCount: 0, videoCount: 0, contributingGuests: 0, storageUsedMb: 0, guestLink: '', archived: false });

  useEffect(() => {
    getAssignedEvent().then(setEvent);
  }, []);
  const [copied, setCopied] = useState(false);
  const qrRef = useRef<HTMLDivElement>(null);

  const link = event.guestLink;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API may be blocked; fall back to selecting the text.
      setCopied(false);
    }
  };

  const handleDownload = () => {
    // Find the <canvas> inside the QR container and export it as PNG.
    const canvas = qrRef.current?.querySelector('canvas');
    if (!canvas) return;
    const url = canvas.toDataURL('image/png');
    const a = document.createElement('a');
    a.href = url;
    a.download = `${event.slug}-qr.png`;
    a.click();
  };

  return (
    <HostLayout event={event}>
      <div className="host-share">
        <header className="host-share__header">
          <div>
            <p className="host-share__eyebrow">Share Event</p>
            <h1 className="host-share__title">Invite Guests</h1>
          </div>
        </header>

        <div className="host-share__card">
          <div className="host-share__qr" ref={qrRef}>
            <QRCodeCanvas
              value={link}
              size={200}
              bgColor="#0a0806"
              fgColor="#c8a96a"
              level="M"
              aria-label={`QR code for ${event.name} guest link`}
            />
          </div>

          <div className="host-share__info">
            <p className="host-share__label">Guest Link</p>
            <p className="host-share__link">{link}</p>
            <div className="host-share__actions">
              <button type="button" className="btn-primary" onClick={handleCopy}>
                {copied ? 'Copied ✓' : 'Copy Link'}
              </button>
              <button type="button" className="btn-ghost" onClick={handleDownload}>
                Download QR
              </button>
            </div>
            <p className="host-share__note">
              Guests scan this QR or open the link to view and upload to the gallery.
            </p>
          </div>
        </div>
      </div>
    </HostLayout>
  );
}
