// ============================================================
// Lentis Gallery — Mock Host Data
// ------------------------------------------------------------
// Frontend-only mock data for the Event Host Console.
// The host manages ONE assigned event (TARAGOLD 2026).
//
// FUTURE: These values will be fetched from the Python backend.
// This file exists so the UI can be built and tested before the
// API is available. Replace with real API calls later.
// ============================================================

import type { Event } from '../types/event';
import type { GalleryMedia, Guest } from '../types/gallery';
import type { HostDashboardSummary } from '../types/dashboard';

/** The single event assigned to the host. */
export const mockAssignedEvent: Event = {
  id: 'evt_taragold_2026',
  slug: 'taragold-2026',
  name: 'TARAGOLD 2026',
  subtitle: 'A celebration of love, memories & moments.',
  hostName: 'Saheed',
  hostEmail: 'host@lentis.gallery',
  eventDate: '2026-08-15',
  status: 'live',
  theme: 'gold',
  slides: [
    { src: '/assets/event/Slideshow1.jpg', alt: 'TARAGOLD 2026 celebration' },
    { src: '/assets/event/Slideshow2.jpg', alt: 'Guests celebrating at TARAGOLD 2026' },
    { src: '/assets/event/Slideshow3.jpg', alt: 'A beautiful moment from TARAGOLD 2026' },
    { src: '/assets/event/Slideshow4.jpg', alt: 'A memorable moment from TARAGOLD 2026' },
  ],
  totalUploads: 248,
  photoCount: 186,
  videoCount: 62,
  contributingGuests: 97,
  storageUsedMb: 1284,
  guestLink: 'https://lentis.gallery/taragold-2026',
  archived: false,
};

/** Storage figure is an estimate — clearly labelled in the UI. */
export const storageIsEstimate = true;

/** Realistic mock gallery media (guest uploads). */
export const mockGalleryMedia: GalleryMedia[] = [
  {
    id: 'm1',
    type: 'photo',
    src: '/assets/event/Slideshow1.jpg',
    guestName: 'Amara Okafor',
    uploadedAt: '12m ago',
    status: 'approved',
    caption: 'Golden hour with the family',
  },
  {
    id: 'm2',
    type: 'photo',
    src: '/assets/event/Slideshow2.jpg',
    guestName: 'Diego Fernández',
    uploadedAt: '38m ago',
    status: 'approved',
    caption: 'The toast',
  },
  {
    id: 'm3',
    type: 'video',
    src: '/assets/event/Slideshow3.jpg',
    guestName: 'Yuki Tanaka',
    uploadedAt: '1h ago',
    status: 'pending',
    caption: 'First dance (clip)',
  },
  {
    id: 'm4',
    type: 'photo',
    src: '/assets/event/Slideshow4.jpg',
    guestName: 'Priya Sharma',
    uploadedAt: '2h ago',
    status: 'hidden',
    caption: 'Behind the scenes',
  },
  {
    id: 'm5',
    type: 'photo',
    src: '/assets/event/Slideshow1.jpg',
    guestName: 'Lucas Meyer',
    uploadedAt: '3h ago',
    status: 'approved',
    caption: 'Cake cutting',
  },
  {
    id: 'm6',
    type: 'video',
    src: '/assets/event/Slideshow2.jpg',
    guestName: 'Amara Okafor',
    uploadedAt: '4h ago',
    status: 'approved',
    caption: 'Speeches highlight',
  },
  {
    id: 'm7',
    type: 'photo',
    src: '/assets/event/Slideshow3.jpg',
    guestName: 'Sofia Rossi',
    uploadedAt: '5h ago',
    status: 'pending',
    caption: 'Guests arriving',
  },
  {
    id: 'm8',
    type: 'photo',
    src: '/assets/event/Slideshow4.jpg',
    guestName: 'Noah Williams',
    uploadedAt: '6h ago',
    status: 'approved',
    caption: 'Group photo',
  },
];

/** Mock guests who contributed. */
export const mockGuests: Guest[] = [
  { id: 'g1', name: 'Amara Okafor', contributionCount: 14, lastActive: '12m ago' },
  { id: 'g2', name: 'Diego Fernández', contributionCount: 9, lastActive: '38m ago' },
  { id: 'g3', name: 'Yuki Tanaka', contributionCount: 6, lastActive: '1h ago' },
  { id: 'g4', name: 'Priya Sharma', contributionCount: 11, lastActive: '2h ago' },
  { id: 'g5', name: 'Lucas Meyer', contributionCount: 8, lastActive: '3h ago' },
  { id: 'g6', name: 'Sofia Rossi', contributionCount: 5, lastActive: '5h ago' },
  { id: 'g7', name: 'Noah Williams', contributionCount: 7, lastActive: '6h ago' },
  { id: 'g8', name: 'Maya Patel', contributionCount: 3, lastActive: '8h ago' },
];

/** Host Overview summary figures. */
export const mockHostSummary: HostDashboardSummary = {
  totalUploads: 248,
  photoCount: 186,
  videoCount: 62,
  contributingGuests: 97,
  storageUsedMb: 1284,
  storageIsEstimate: true,
};
