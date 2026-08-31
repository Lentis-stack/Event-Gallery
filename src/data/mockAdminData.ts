// ============================================================
// Lentis Gallery — Mock Admin Data
// ------------------------------------------------------------
// Frontend-only mock data for the Lentis Admin Console.
// The Admin manages MULTIPLE events across the platform.
//
// FUTURE: These values will be fetched from the Python backend.
// This file exists so the UI can be built and tested before the
// API is available. Replace with real API calls later.
// ============================================================

import type { Event } from '../types/event';
import type { AdminDashboardSummary } from '../types/dashboard';

/** The full list of events managed by Lentis Admin. */
export const mockEvents: Event[] = [
  {
    id: 'evt_taragold_2026',
    slug: 'taragold-2026',
    name: 'TARAGOLD 2026',
    subtitle: 'A celebration of love, memories & moments.',
    hostName: 'Ava Sterling',
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
  },
  {
    id: 'evt_aurora_2026',
    slug: 'aurora-spring-2026',
    name: 'Aurora Spring 2026',
    subtitle: 'An evening of art, light & connection.',
    hostName: 'Marcus Chen',
    hostEmail: 'marcus@lentis.gallery',
    eventDate: '2026-06-20',
    status: 'draft',
    theme: 'blue',
    slides: [
      { src: '/assets/event/Slideshow1.jpg', alt: 'Aurora Spring 2026' },
      { src: '/assets/event/Slideshow2.jpg', alt: 'Aurora Spring 2026 guests' },
    ],
    totalUploads: 0,
    photoCount: 0,
    videoCount: 0,
    contributingGuests: 0,
    storageUsedMb: 0,
    guestLink: 'https://lentis.gallery/aurora-spring-2026',
    archived: false,
  },
  {
    id: 'evt_nova_2025',
    slug: 'nova-gala-2025',
    name: 'Nova Gala 2025',
    subtitle: 'A night of celebration under the stars.',
    hostName: 'Elena Petrova',
    hostEmail: 'elena@lentis.gallery',
    eventDate: '2025-12-05',
    status: 'ended',
    theme: 'rose',
    slides: [
      { src: '/assets/event/Slideshow3.jpg', alt: 'Nova Gala 2025' },
      { src: '/assets/event/Slideshow4.jpg', alt: 'Nova Gala 2025 celebration' },
    ],
    totalUploads: 512,
    photoCount: 402,
    videoCount: 110,
    contributingGuests: 203,
    storageUsedMb: 3072,
    guestLink: 'https://lentis.gallery/nova-gala-2025',
    archived: false,
  },
  {
    id: 'evt_terra_2025',
    slug: 'terra-festival-2025',
    name: 'Terra Festival 2025',
    subtitle: 'A community celebration of heritage.',
    hostName: 'Owen Gallagher',
    hostEmail: 'owen@lentis.gallery',
    eventDate: '2025-09-18',
    status: 'ended',
    theme: 'emerald',
    slides: [
      { src: '/assets/event/Slideshow1.jpg', alt: 'Terra Festival 2025' },
      { src: '/assets/event/Slideshow2.jpg', alt: 'Terra Festival 2025 crowd' },
    ],
    totalUploads: 176,
    photoCount: 140,
    videoCount: 36,
    contributingGuests: 88,
    storageUsedMb: 912,
    guestLink: 'https://lentis.gallery/terra-festival-2025',
    archived: true,
  },
];

/** Admin Console overview totals. */
export const mockAdminSummary: AdminDashboardSummary = {
  totalEvents: 4,
  liveEvents: 1,
  totalUploads: 936,
  totalHosts: 4,
};
