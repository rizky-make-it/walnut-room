const $ = (selector, parent = document) => parent.querySelector(selector);
const $$ = (selector, parent = document) => [...parent.querySelectorAll(selector)];

const menu = $('.menu-toggle');
const nav = $('#main-nav');
function closeMenu() { menu.setAttribute('aria-expanded', 'false'); menu.setAttribute('aria-label', 'Buka navigasi'); nav.classList.remove('is-open'); }
menu.addEventListener('click', () => { const open = menu.getAttribute('aria-expanded') !== 'true'; menu.setAttribute('aria-expanded', String(open)); menu.setAttribute('aria-label', open ? 'Tutup navigasi' : 'Buka navigasi'); nav.classList.toggle('is-open', open); });
$$('a', nav).forEach(a => a.addEventListener('click', closeMenu));
document.addEventListener('keydown', event => { if (event.key === 'Escape') closeMenu(); });
document.addEventListener('click', event => { if (!event.target.closest('.header-inner')) closeMenu(); });

const comparison = $('.comparison');
const range = $('#comparison-range');
function setSplit(value) {
  const percentage = Math.max(0, Math.min(100, Number(value)));
  comparison.style.setProperty('--split', `${percentage}%`);
  range.value = percentage;
  range.setAttribute('aria-valuetext', `${percentage} persen render revisi`);
  $$('[data-split]').forEach(b => b.setAttribute('aria-pressed', String(Number(b.dataset.split) === percentage)));
  $('.label-render').style.opacity = percentage < 12 ? '0' : '1';
  $('.label-reference').style.opacity = percentage > 88 ? '0' : '1';
}
range.addEventListener('input', () => setSplit(range.value));
$$('[data-split]').forEach(button => button.addEventListener('click', () => setSplit(button.dataset.split)));

const images = {
  render: { src: 'assets/bedroom-render.jpg', alt: 'Render revisi detail kamar walnut dan mustard', caption: 'Walnut & ochre · Render Cycles asli 7680 × 5416 px', download: 'downloads/bedroom-render-8k.jpg', master: true, filename: 'walnut-bedroom-cycles-8k.jpg', label: 'Unduh PNG 8K' },
  reference: { src: 'assets/bedroom-reference.jpg', alt: 'Referensi awal kamar walnut dan mustard', caption: 'Referensi awal · Arah komposisi dan palet material', filename: 'walnut-bedroom-reference.jpg' },
  walnut: { src: 'assets/detail-walnut.jpg', alt: 'Detail serat walnut pada dresser', caption: '01 / Walnut · Natural grain, satin roughness & relief serat', filename: 'walnut-detail.jpg' },
  cotton: { src: 'assets/detail-cotton.jpg', alt: 'Detail katun putih dan lipatan duvet', caption: '02 / Natural cotton · Cross-woven threads & sculpted folds', filename: 'cotton-detail.jpg' },
  ochre: { src: 'assets/detail-ochre.jpg', alt: 'Detail bantal mustard dan bolster corduroy', caption: '03 / Ochre · Linen weave, pinched seams & corduroy ribs', filename: 'ochre-detail.jpg' },
  leather: { src: 'assets/detail-leather.jpg', alt: 'Detail ottoman kulit cognac dan jahitan', caption: '04 / Cognac leather · Pori kulit, patina & double saddle stitch', filename: 'leather-detail.jpg' },
};
const dialog = $('#image-dialog');
function selectImage(name) {
  const image = images[name] || images.render;
  $('#lightbox-image').src = image.src; $('#lightbox-image').alt = image.alt;
  $('#lightbox-download').href = image.download || image.src; $('#lightbox-download').download = image.filename;
  $('#lightbox-download').dataset.downloadMaster = String(!!image.master);
  $('#lightbox-download').firstChild.textContent = `${image.label || 'Unduh detail'} `;
  $('#lightbox-caption').textContent = image.caption;
  $$('[data-lightbox-image]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.lightboxImage === name)));
}
$$('[data-open-image]').forEach(button => button.addEventListener('click', () => { selectImage(button.dataset.openImage); dialog.showModal(); document.body.style.overflow = 'hidden'; }));
$$('[data-lightbox-image]').forEach(button => button.addEventListener('click', () => selectImage(button.dataset.lightboxImage)));
$('#close-dialog').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', event => { if (event.target === dialog) { const rect = dialog.getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close(); } });
dialog.addEventListener('close', () => { document.body.style.overflow = ''; });

// Large lossless renders travel as small verified byte parts, avoiding an
// oversized static asset. Reassembly preserves every pixel of the native PNG.
let masterBusy = false;
const downloadNotice = document.createElement('p');
downloadNotice.className = 'download-notice'; downloadNotice.hidden = true;
downloadNotice.setAttribute('role', 'status'); downloadNotice.setAttribute('aria-live', 'polite');
document.body.append(downloadNotice);
dialog.addEventListener('close', () => { if (masterBusy) document.body.append(downloadNotice); });
document.addEventListener('click', async event => {
  const anchor = event.target.closest('a[data-download-master="true"]');
  if (!anchor) return;
  event.preventDefault();
  if (masterBusy) return;
  masterBusy = true;
  (dialog.open ? dialog : document.body).append(downloadNotice);
  downloadNotice.hidden = false; downloadNotice.textContent = 'Menyiapkan PNG 8K…';
  $$('a[data-download-master="true"]').forEach(a => a.setAttribute('aria-disabled', 'true'));
  try {
    const response = await fetch('downloads/render-8k.json');
    if (!response.ok) throw new Error('Manifest unavailable');
    const manifest = await response.json();
    if (!manifest.parts?.length || manifest.bytes > 160 * 1024 * 1024) throw new Error('Invalid master size');
    const parts = []; let loaded = 0;
    for (const part of manifest.parts) {
      downloadNotice.textContent = `Mengunduh PNG 8K… ${Math.round(loaded / manifest.bytes * 100)}%`;
      const result = await fetch(part.url);
      if (!result.ok) throw new Error('Part unavailable');
      const bytes = await result.arrayBuffer();
      if (bytes.byteLength !== part.bytes) throw new Error('Incomplete part');
      const digest = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(n => n.toString(16).padStart(2, '0')).join('');
      if (digest !== part.sha256) throw new Error('Checksum mismatch');
      parts.push(bytes); loaded += bytes.byteLength;
    }
    if (loaded !== manifest.bytes) throw new Error('Incomplete render');
    const blob = new Blob(parts, { type: 'image/png' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a'); link.href = url; link.download = manifest.filename;
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
    downloadNotice.textContent = 'PNG 8K siap. Periksa unduhan browser.';
  } catch {
    downloadNotice.textContent = 'PNG belum terunduh. Coba lagi, atau gunakan tautan JPEG 8K pada bagian proyek.';
  } finally {
    masterBusy = false;
    $$('a[data-download-master="true"]').forEach(a => a.removeAttribute('aria-disabled'));
    setTimeout(() => { downloadNotice.hidden = true; }, 12000);
  }
});

const viewer = $('#room-viewer');
const viewerShell = $('#viewer-shell');
const status = $('#viewer-status');
const loadButton = $('#load-model');
const rotateButton = $('#rotate-toggle');
const cameraViews = {
  perspective: { orbit: '32deg 73deg 8.8m', target: '0.1m 0.95m 0m', index: '01 / 03' },
  top: { orbit: '0deg 14deg 10m', target: '0.1m 0.5m 0m', index: '02 / 03' },
  detail: { orbit: '30deg 78deg 4.6m', target: '0.54m 0.75m -0.15m', index: '03 / 03' },
};
let componentReady = false;
let requestedOpen = false;
function showViewerError() { $('.viewer-error').hidden = false; status.textContent = 'RENDER TERSEDIA'; loadButton.disabled = false; }
async function openModel() {
  requestedOpen = true; loadButton.disabled = true; $('span', loadButton).textContent = 'Memuat ruang…'; status.textContent = 'MEMUAT MODEL';
  try { await customElements.whenDefined('model-viewer'); componentReady = true; viewer.loading = 'eager'; viewer.dismissPoster(); if (viewer.loaded) { status.textContent = 'RUANG SIAP DIJELAJAHI'; loadButton.disabled = false; } }
  catch { showViewerError(); }
}
loadButton.addEventListener('click', openModel);
viewer.addEventListener('load', () => { status.textContent = requestedOpen ? 'RUANG SIAP DIJELAJAHI' : 'MODEL 3D SIAP'; loadButton.disabled = false; $('span', loadButton).textContent = 'Buka model 3D'; });
viewer.addEventListener('poster-dismissed', () => { requestedOpen = true; status.textContent = 'RUANG SIAP DIJELAJAHI'; });
viewer.addEventListener('progress', event => { const progress = event.detail.totalProgress; $('.model-progress>div').style.width = `${progress * 100}%`; $('.model-progress').style.opacity = progress >= 1 ? '0' : '1'; });
viewer.addEventListener('error', showViewerError);
customElements.whenDefined('model-viewer').then(() => { componentReady = true; });
setTimeout(() => { if (!componentReady) showViewerError(); }, 18000);
$$('[data-view]').forEach(button => button.addEventListener('click', async () => { const selected = cameraViews[button.dataset.view]; if (!componentReady || !requestedOpen) await openModel(); viewer.cameraOrbit = selected.orbit; viewer.cameraTarget = selected.target; viewer.autoRotate = false; rotateButton.setAttribute('aria-pressed', 'false'); $$('[data-view]').forEach(b => b.setAttribute('aria-pressed', String(b === button))); $('.viewer-index').textContent = selected.index; }));
rotateButton.addEventListener('click', async () => { if (!componentReady || !requestedOpen) await openModel(); const rotate = rotateButton.getAttribute('aria-pressed') !== 'true'; viewer.autoRotate = rotate; rotateButton.setAttribute('aria-pressed', String(rotate)); rotateButton.setAttribute('aria-label', rotate ? 'Hentikan putaran otomatis' : 'Aktifkan putaran otomatis'); });
$('#fullscreen-toggle').addEventListener('click', async () => { try { if (document.fullscreenElement) await document.exitFullscreen(); else await viewerShell.requestFullscreen(); } catch { status.textContent = 'LAYAR PENUH TIDAK TERSEDIA'; } });
document.addEventListener('fullscreenchange', () => { $('#fullscreen-toggle').setAttribute('aria-label', document.fullscreenElement ? 'Keluar dari layar penuh' : 'Buka model layar penuh'); });
$('#retry-model').addEventListener('click', () => { $('.viewer-error').hidden = true; viewer.src = `assets/bedroom.glb?retry=${Date.now()}`; openModel(); });
if (matchMedia('(prefers-reduced-motion: reduce)').matches) viewer.interpolationDecay = 0;
