const params = new URLSearchParams(window.location.search);
const guestName = (params.get('name') || 'Guest').trim();
let eventCode = (params.get('event') || '').trim();
// Backward-compat: some flows may pass eventCode instead of event.
if (!eventCode) eventCode = (params.get('eventCode') || '').trim();


// Backend base URL (same-origin by default). If backend runs on another host/port,
// you can set window.BACKEND_BASE_URL before camera.js loads.
const BACKEND_BASE_URL = window.BACKEND_BASE_URL || '';
const API_BASE = `${BACKEND_BASE_URL}`; // '' => same-origin

// UI elements
const guestPillEl = document.getElementById('guestPill');
const guestSubtitleEl = document.getElementById('guestSubtitle');
const cameraBg = document.getElementById('cameraBg');

cameraBg.style.backgroundImage = 'url("./assets/wedding bgd 2.jpg")';

document.getElementById('guestPill').textContent = eventCode ? `Event: ${eventCode}` : guestName;
document.getElementById('guestSubtitle').textContent = `Hi ${guestName} — take a photo or video.`;

// Disable UI if eventCode missing
const video = document.getElementById('video');
const captureCanvas = document.getElementById('captureCanvas');
const capturedItems = document.getElementById('capturedItems');

const enableCameraBtn = document.getElementById('enableCameraBtn');
const switchCameraBtn = document.getElementById('switchCameraBtn');
const capturePhotoBtn = document.getElementById('capturePhotoBtn');
const recordVideoBtn = document.getElementById('recordVideoBtn');
const stopRecordBtn = document.getElementById('stopRecordBtn');

const fileInput = document.getElementById('fileInput');
const uploadBtn = document.getElementById('uploadBtn');
const uploadAllBtn = document.getElementById('uploadAllBtn');
const clearBtn = document.getElementById('clearBtn');

let pendingUploads = [];
let stream = null;
let mediaRecorder = null;
let recordedChunks = [];
let isRecording = false;

let currentFacing = 'user'; // 'user' (front) | 'environment' (back)
let cachedVideoDevices = [];
let switching = false;

function supportsMediaRecorder(){
  return typeof MediaRecorder !== 'undefined';
}

function stopStreamTracks(){
  if (!stream) return;
  try { stream.getTracks().forEach(t => t.stop()); } catch {}
  stream = null;
}

async function refreshVideoDevices(){
  if (!navigator.mediaDevices?.enumerateDevices) return;
  try{
    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoDevs = devices.filter(d => d.kind === 'videoinput');
    cachedVideoDevices = videoDevs.map(d => {
      const label = d.label || '';
      const isFront = /front|user|self|facetime|true(depth)?/i.test(label);
      const isBack = /back|rear|environment|wide/i.test(label);
      return {
        deviceId: d.deviceId,
        facingHint: isBack ? 'environment' : (isFront ? 'user' : null)
      };
    });
  }catch{
    cachedVideoDevices = [];
  }
}

function pickDeviceIdForFacing(facing){
  const hinted = cachedVideoDevices.filter(d => d.facingHint === facing);
  if (hinted[0]?.deviceId) return hinted[0].deviceId;
  if (cachedVideoDevices.length >= 2){
    return facing === 'user' ? cachedVideoDevices[0].deviceId : cachedVideoDevices[1].deviceId;
  }
  return null;
}

function humanizeCameraError(err){
  const name = err?.name || 'Error';
  const msg = err?.message ? String(err.message) : '';
  const lower = `${name} ${msg}`.toLowerCase();

  let hint = 'Camera access failed due to browser/security/device restrictions.';
  if (lower.includes('notallowed') || lower.includes('permission')) {
    hint = 'Permission was denied by the browser. Allow Camera permission for this site.';
  } else if (lower.includes('insecure') || lower.includes('https') || lower.includes('secure')) {
    hint = 'This page must be served over HTTPS (or localhost) for camera access.';
  } else if (lower.includes('notfound') || lower.includes('overconstrained')) {
    hint = 'No camera device matched the requested constraints. Try switching again or use Upload.';
  } else if (lower.includes('notreadable') || lower.includes('busy')) {
    hint = 'Camera is already in use by another app/tab. Close other camera usage and retry.';
  }

  return { name, msg, hint };
}

async function startCamera({ facing = currentFacing, deviceId = null } = {}){
  if (switching) return;
  switching = true;

  try{
    if (!cachedVideoDevices.length) await refreshVideoDevices();
    stopStreamTracks();

    let constraints;
    const chosenDeviceId = deviceId ?? pickDeviceIdForFacing(facing);

    if (chosenDeviceId){
      constraints = {
        video: { deviceId: { exact: chosenDeviceId } },
        audio: false
      };
    } else {
      constraints = {
        video: { facingMode: { ideal: facing } },
        audio: false
      };
    }

    stream = await navigator.mediaDevices.getUserMedia(constraints);
    video.srcObject = stream;

    try { await video.play(); } catch {}

    capturePhotoBtn.disabled = false;
    recordVideoBtn.disabled = false;
    if (switchCameraBtn) switchCameraBtn.disabled = false;
  }catch(err){
    console.error(err);
    const { name, msg, hint } = humanizeCameraError(err);
    alert(
      'Camera access failed (' + name + ').\n' +
      (msg ? (msg + '\n') : '') +
      hint +
      '\n\n1) Ensure you opened this in Safari/Chrome (not in-app browser)\n' +
      '2) If it still fails, use the Upload button as a fallback.'
    );

    capturePhotoBtn.disabled = true;
    recordVideoBtn.disabled = true;
    if (switchCameraBtn) switchCameraBtn.disabled = true;
  }finally{
    switching = false;
  }
}

async function switchCamera(){
  if (!stream) return;
  if (switching) return;
  if (isRecording) return;

  currentFacing = currentFacing === 'user' ? 'environment' : 'user';

  if (switchCameraBtn) switchCameraBtn.disabled = true;
  capturePhotoBtn.disabled = true;
  recordVideoBtn.disabled = true;
  stopRecordBtn.disabled = true;

  await refreshVideoDevices();
  await startCamera({ facing: currentFacing });
}

function addThumbnailFromBlob(blob, type){
  const wrap = document.createElement('div');
  wrap.className = 'thumb';

  const url = URL.createObjectURL(blob);
  const id = (blob && blob.type)
    ? `${Date.now()}-${Math.random().toString(16).slice(2)}`
    : String(Date.now());
  wrap.dataset.pendingId = id;

  if (type && type.startsWith('video/')){
    const v = document.createElement('video');
    v.src = url;
    v.controls = true;
    v.playsInline = true;
    wrap.appendChild(v);
  } else {
    const img = document.createElement('img');
    img.src = url;
    img.alt = 'Captured media';
    wrap.appendChild(img);
  }

  capturedItems.prepend(wrap);
  pendingUploads.push({ id, blob, mime: blob.type || type || 'application/octet-stream' });
}

capturePhotoBtn.addEventListener('click', () => {
  const w = video.videoWidth;
  const h = video.videoHeight;
  if (!w || !h) return;

  captureCanvas.width = w;
  captureCanvas.height = h;
  const ctx = captureCanvas.getContext('2d');
  ctx.drawImage(video, 0, 0, w, h);

  captureCanvas.toBlob((blob) => {
    if (!blob) return;
    addThumbnailFromBlob(blob, blob.type || 'image/png');
  }, 'image/jpeg', 0.92);
});

function safeDisableWhileRecording(){
  recordVideoBtn.disabled = true;
  stopRecordBtn.disabled = false;
}

recordVideoBtn.addEventListener('click', async () => {
  if (!supportsMediaRecorder()){
    alert('Recording is not supported on this device/browser. You can still upload files.');
    return;
  }

  if (!stream) await startCamera({ facing: currentFacing });
  if (!stream) return;

  recordedChunks = [];

  const options = (() => {
    const candidates = [
      { mimeType: 'video/webm;codecs=vp9' },
      { mimeType: 'video/webm;codecs=vp8' },
      { mimeType: 'video/webm' }
    ];
    for (const c of candidates){
      if (MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(c.mimeType)) return c;
    }
    return {};
  })();

  try{
    mediaRecorder = new MediaRecorder(stream, options);

    mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) recordedChunks.push(e.data);
    };

    mediaRecorder.onstop = () => {
      const blob = new Blob(recordedChunks, { type: recordedChunks[0]?.type || 'video/webm' });
      addThumbnailFromBlob(blob, blob.type);
      isRecording = false;

      stopRecordBtn.disabled = true;
      recordVideoBtn.disabled = false;
      stopRecordBtn.style.opacity = '1';
      recordVideoBtn.style.opacity = '1';
      if (switchCameraBtn) switchCameraBtn.disabled = false;
    };

    safeDisableWhileRecording();

    mediaRecorder.start();
    isRecording = true;
    recordVideoBtn.style.opacity = '0.75';
    stopRecordBtn.style.opacity = '1';

    if (switchCameraBtn) switchCameraBtn.disabled = true;
  }catch(err){
    console.error(err);
    alert('Could not start video recording.');
  }
});

stopRecordBtn.addEventListener('click', () => {
  if (!mediaRecorder || !isRecording) return;
  try { mediaRecorder.stop(); } catch {}
});

clearBtn.addEventListener('click', () => {
  capturedItems.innerHTML = '';
  pendingUploads = [];
});

// Uploads
async function uploadBlobToBackend(blob, pending, uploadId){
  if (!eventCode) throw new Error('eventCode missing (URL ?event=...)');
  const guestNameLocal = guestName;
  if (!guestNameLocal) throw new Error('guestName missing');

  const form = new FormData();
  form.append('eventCode', eventCode);
  form.append('guestName', guestNameLocal);
  form.append('guestId', guestNameLocal.toLowerCase().replace(/\s+/g, '-').slice(0, 40) || 'guest');
  form.append('uploadId', uploadId || pending.uploadId || 'upload');
  form.append('media', blob, pending.filename || (pending.id + (blob.type ? ('.' + blob.type.split('/')[1]) : '')));

  const endpoint = `${API_BASE}/api/upload`;
  console.debug('[upload]', { endpoint, eventCode, guestName: guestNameLocal, uploadId });

  const res = await fetch(endpoint, { method: 'POST', body: form });
  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    throw new Error(`Upload failed: ${res.status} ${txt}`);
  }
  return res.json();
}

async function uploadPendingToBackend(){
  if (!eventCode){
    alert('Missing event code in the URL. Go back and try again.');
    return;
  }
  if (!pendingUploads.length) return;

  const uploadId = `u-${Date.now()}`;
  const toUpload = pendingUploads.slice();
  pendingUploads = [];

  for (const p of toUpload){
    try{
      await uploadBlobToBackend(p.blob, p, uploadId);
    }catch(e){
      console.error(e);
      alert('Upload failed for one item. Check console and try again.');
    }
  }
}

uploadBtn.addEventListener('click', async () => {
  const files = Array.from(fileInput.files || []);
  if (!files.length) return;

  for (const f of files){
    addThumbnailFromBlob(f, f.type);
  }
  fileInput.value = '';
  await uploadPendingToBackend();
});

uploadAllBtn.addEventListener('click', async () => {
  await uploadPendingToBackend();
});

// Buttons
let enableAttempted = false;

enableCameraBtn.addEventListener('click', async () => {
  enableAttempted = true;
  enableCameraBtn.disabled = true;
  enableCameraBtn.textContent = 'Opening camera...';

  currentFacing = 'user';
  await refreshVideoDevices();
  await startCamera({ facing: currentFacing });

  if (stream){
    enableCameraBtn.style.display = 'none';
  }else{
    enableCameraBtn.disabled = false;
    enableCameraBtn.textContent = 'Enable Camera';
  }
});

if (switchCameraBtn){
  switchCameraBtn.addEventListener('click', async () => {
    await switchCamera();
  });
}

// Secondary safety: attempt camera on first user interaction (only as best-effort)
window.addEventListener('touchstart', async () => {
  if (stream || enableAttempted) return;
  try{
    currentFacing = 'user';
    await refreshVideoDevices();
    await startCamera({ facing: currentFacing });
  }catch{}
},{ once:true });

window.addEventListener('beforeunload', () => {
  try{
    if (stream){
      stream.getTracks().forEach(t => t.stop());
    }
  }catch{}
});

// If eventCode missing, disable capture until user goes back
if (!eventCode){
  console.warn('Missing event code. Guest uploads require ?event=... in URL.');
  capturePhotoBtn.disabled = true;
  recordVideoBtn.disabled = true;
  if (switchCameraBtn) switchCameraBtn.disabled = true;
}