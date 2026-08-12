const params = new URLSearchParams(window.location.search);
const eventCode = params.get('event') || '';

const landingBg = document.getElementById('landingBg');
// IMPORTANT: leave src empty in <img> tags (tiles). For background, set it below using this exact line:
// landingBg.style.backgroundImage = 'url("PUT_YOUR_BACKGROUND_IMAGE_LINK_HERE")';
landingBg.style.backgroundImage = 'url("./assets/wedding background 1.jpg")';

const eventCodePill = document.getElementById('eventCodePill');
eventCodePill.textContent = eventCode ? `Event: ${eventCode}` : 'Event';

// Doodle logo customization:
// Replace text/emoji in doodleLogo, or swap with an <img> tag in the HTML if you prefer.
const doodle = document.getElementById('doodleLogo');
// Example: doodle.textContent = '💍';

const form = document.getElementById('rsvpForm');
const nameInput = document.getElementById('guestName');
const enterBtn = document.getElementById('enterBtn');

form.addEventListener('submit', (e) => {
  e.preventDefault();
  const guestName = (nameInput.value || '').trim();
  if (!guestName) return;

  const url = new URL('./camera.html', window.location.href);
  url.searchParams.set('name', guestName);
  if (eventCode) url.searchParams.set('event', eventCode);

  // small UX: disable button briefly
  enterBtn.disabled = true;
  enterBtn.style.opacity = '0.85';

  window.location.href = url.toString();
});

