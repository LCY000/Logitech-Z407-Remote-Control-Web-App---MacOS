'use strict';

/* Z407 Control web remote.
 * The server owns all state; this page polls /api/status and renders it. */

const $ = (id) => document.getElementById(id);
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const CLIENT_HEADER = { 'X-Z407-Client': '1' };
const POLL_IDLE_MS = 2000;
const POLL_BUSY_MS = 350;
const REPEAT_DELAY_MS = 380;      // hold this long before a button starts repeating
const REPEAT_INTERVAL_MS = 150;   // the speaker drops steps that arrive faster
const DIAL_START_DEG = 135;       // 7 o'clock
const DIAL_SWEEP_DEG = 270;
const SVG_NS = 'http://www.w3.org/2000/svg';

const I18N = JSON.parse($('i18n').textContent);
const LANGS = Object.keys(I18N);

let lang = pickLanguage();
let status = null;              // last /api/status payload
let offline = false;            // server unreachable
let quitting = false;
let localBusy = 0;              // long requests started from this page
const pending = { volume: null, bass: null };   // value being dragged / applied

/* ---------- i18n ---------- */

function pickLanguage() {
    // ?lang=en or ?lang=zh-TW in the address wins, so a link can pin the language.
    const requested = new URLSearchParams(location.search).get('lang');
    if (requested && LANGS.includes(requested)) return requested;
    let saved = null;
    try { saved = localStorage.getItem('z407.lang'); } catch { /* private mode */ }
    if (saved && LANGS.includes(saved)) return saved;
    // Otherwise the language last chosen on the Mac (kept by the app), English by default.
    const remembered = document.documentElement.dataset.savedLang;
    return LANGS.includes(remembered) ? remembered : 'en';
}

function t(key, vars) {
    let text = I18N[lang]?.[key] ?? I18N.en[key] ?? key;
    for (const [name, value] of Object.entries(vars || {})) {
        text = text.replaceAll(`{${name}}`, value);
    }
    return text;
}

function applyLanguage() {
    document.documentElement.lang = lang;
    document.querySelectorAll('[data-i18n]').forEach((el) => { el.textContent = t(el.dataset.i18n); });
    document.querySelectorAll('[data-i18n-aria]').forEach((el) => {
        el.setAttribute('aria-label', t(el.dataset.i18nAria));
    });
    $('langToggle').textContent = t('lang.switch');
    $('langToggle').setAttribute('aria-label', t('lang.switchLabel'));
    $('langToggle').lang = lang === 'en' ? 'zh-TW' : 'en';
    render();
}

/* ---------- Server calls ---------- */

async function api(path, { method = 'GET', body } = {}) {
    const options = { method, headers: { ...CLIENT_HEADER }, cache: 'no-store' };
    if (body !== undefined) {
        options.headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(body);
    }

    let response;
    try {
        response = await fetch(path, options);
    } catch {
        const error = new Error(t('error.network'));
        error.code = 'network';
        throw error;
    }

    let data = null;
    try { data = await response.json(); } catch { /* not JSON */ }
    if (!response.ok || data?.success === false) {
        const error = new Error(data?.error || `HTTP ${response.status}`);
        error.code = data?.code;
        throw error;
    }
    return data;
}

function describeError(error) {
    const key = `error.${error.code}`;
    return I18N.en[key] ? t(key) : error.message;
}

let refreshTimer = null;
function refreshSoon(delay = 180) {
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(refresh, delay);
}

async function refresh() {
    if (quitting) return;
    try {
        status = await api('/api/status');
        offline = false;
    } catch {
        offline = true;
    }
    render();
}

async function pollLoop() {
    while (!quitting) {
        if (!document.hidden) await refresh();
        await sleep(localBusy || status?.busy ? POLL_BUSY_MS : POLL_IDLE_MS);
    }
}

/* ---------- Commands ---------- */

const COMMAND_TOASTS = {
    input_aux: () => t('input.switched', { input: t('input.aux') }),
    input_usb: () => t('input.switched', { input: t('input.usb') }),
    input_bluetooth: () => t('input.switched', { input: t('input.bluetooth') }),
    bluetooth_pair: () => t('toast.pairing'),
    factory_reset: () => t('toast.reset'),
};

async function send(command) {
    try {
        await api(`/api/${command}`, { method: 'POST' });
        if (COMMAND_TOASTS[command]) toast(COMMAND_TOASTS[command]());
        refreshSoon();
        return true;
    } catch (error) {
        toast(describeError(error), 'bad');
        refreshSoon(0);
        return false;
    }
}

async function setLevel(target, value) {
    if (status?.[target] == null) {
        toast(t('toast.needCalibration'), 'bad');
        return;
    }
    if (value === status[target]) return;

    pending[target] = value;
    localBusy += 1;
    render();
    try {
        const result = await api('/api/set_level', { method: 'POST', body: { target, value } });
        if (!result.reached) toast(t('toast.notReached'), 'bad');
    } catch (error) {
        toast(describeError(error), 'bad');
    } finally {
        pending[target] = null;
        localBusy -= 1;
        await refresh();
    }
}

async function calibrate() {
    const confirmed = await ask('calibrate');
    if (!confirmed) return;
    localBusy += 1;
    refreshSoon(250);
    try {
        await api('/api/calibrate', { method: 'POST' });
        toast(t('toast.calibrated'));
    } catch (error) {
        toast(describeError(error), 'bad');
    } finally {
        localBusy -= 1;
        await refresh();
    }
}

async function quitApp() {
    const confirmed = await ask('quit', { danger: true });
    if (!confirmed) return;
    try {
        await api('/api/shutdown', { method: 'POST' });
    } catch (error) {
        toast(describeError(error), 'bad');
        return;
    }
    quitting = true;
    const farewell = document.createElement('main');
    farewell.className = 'farewell';
    const title = document.createElement('h1');
    title.textContent = t('quit.title');
    const body = document.createElement('p');
    body.textContent = t('quit.body');
    farewell.append(title, body);
    document.body.replaceChildren(farewell);
}

/* ---------- Confirm dialog ---------- */

function ask(name, { danger = false } = {}) {
    const dialog = $('confirm');
    $('confirmTitle').textContent = t(`confirm.${name}.title`);
    $('confirmBody').textContent = t(`confirm.${name}.body`);
    $('confirmOk').textContent = t(`confirm.${name}.ok`);
    $('confirmOk').classList.toggle('danger', danger);

    return new Promise((resolve) => {
        const finish = (answer) => {
            $('confirmOk').onclick = null;
            $('confirmCancel').onclick = null;
            dialog.onclose = null;
            if (dialog.open) dialog.close();
            resolve(answer);
        };
        $('confirmOk').onclick = () => finish(true);
        $('confirmCancel').onclick = () => finish(false);
        dialog.onclose = () => finish(false);   // Esc key
        dialog.showModal();
        $('confirmCancel').focus();
    });
}

/* ---------- Toast ---------- */

let toastTimer = null;
function toast(message, tone = 'info') {
    const el = $('toast');
    el.textContent = message;
    el.dataset.tone = tone;
    el.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.hidden = true; }, tone === 'bad' ? 6000 : 2600);
}

/* ---------- Dial ---------- */

function polar(angleDeg, radius) {
    const rad = (angleDeg * Math.PI) / 180;
    return [160 + radius * Math.cos(rad), 160 + radius * Math.sin(rad)];
}

function buildDial(max) {
    const group = $('dialTicks');
    group.replaceChildren();
    for (let i = 0; i <= max; i += 1) {
        const angle = DIAL_START_DEG + (i / max) * DIAL_SWEEP_DEG;
        const [x1, y1] = polar(angle, 126);
        const [x2, y2] = polar(angle, i % 8 === 0 ? 150 : 144);
        const tick = document.createElementNS(SVG_NS, 'line');
        tick.setAttribute('x1', x1.toFixed(2));
        tick.setAttribute('y1', y1.toFixed(2));
        tick.setAttribute('x2', x2.toFixed(2));
        tick.setAttribute('y2', y2.toFixed(2));
        tick.setAttribute('class', 'tick');
        group.append(tick);
    }
    group.dataset.max = String(max);
}

function dialValueAt(event, max) {
    const rect = $('dial').getBoundingClientRect();
    const dx = event.clientX - (rect.left + rect.width / 2);
    const dy = event.clientY - (rect.top + rect.height / 2);
    let sweep = ((Math.atan2(dy, dx) * 180) / Math.PI - DIAL_START_DEG + 720) % 360;
    if (sweep > DIAL_SWEEP_DEG) {
        // In the gap at the bottom: snap to whichever end is closer.
        sweep = sweep > (360 + DIAL_SWEEP_DEG) / 2 ? 0 : DIAL_SWEEP_DEG;
    }
    return Math.round((sweep / DIAL_SWEEP_DEG) * max);
}

function bindDial() {
    const dial = $('dial');
    let dragging = false;

    const canDrag = () => controlsReady() && status?.volume != null;

    dial.addEventListener('pointerdown', (event) => {
        if (event.button || !canDrag()) return;
        dragging = true;
        dial.setPointerCapture(event.pointerId);
        dial.dataset.dragging = 'true';
        pending.volume = dialValueAt(event, status.volumeMax);
        render();
    });
    dial.addEventListener('pointermove', (event) => {
        if (!dragging) return;
        pending.volume = dialValueAt(event, status.volumeMax);
        render();
    });
    const release = (commit) => {
        if (!dragging) return;
        dragging = false;
        dial.dataset.dragging = 'false';
        const value = pending.volume;
        pending.volume = null;
        if (commit && value != null) setLevel('volume', value);
        else render();
    };
    dial.addEventListener('pointerup', () => release(true));
    dial.addEventListener('pointercancel', () => release(false));

    dial.addEventListener('keydown', (event) => {
        const command = { ArrowUp: 'vol_up', ArrowRight: 'vol_up', ArrowDown: 'vol_down', ArrowLeft: 'vol_down' }[event.key];
        if (!command) return;
        event.preventDefault();
        event.stopPropagation();
        throttledSend(command);
    });
}

/* ---------- Buttons ---------- */

let lastKeySend = 0;
function throttledSend(command) {
    const now = performance.now();
    if (now - lastKeySend < REPEAT_INTERVAL_MS) return;
    lastKeySend = now;
    send(command);
}

// Press sends once; holding keeps stepping, one request at a time.
function bindRepeat(button) {
    const command = button.dataset.repeat;
    let run = 0;

    button.addEventListener('pointerdown', async (event) => {
        if (event.button || button.disabled) return;
        button.setPointerCapture(event.pointerId);
        const mine = ++run;
        let first = true;
        while (mine === run && !button.disabled) {
            if (!(await send(command))) break;
            await sleep(first ? REPEAT_DELAY_MS : REPEAT_INTERVAL_MS);
            first = false;
        }
    });
    const stop = () => { run += 1; };
    button.addEventListener('pointerup', stop);
    button.addEventListener('pointercancel', stop);
    button.addEventListener('lostpointercapture', stop);
    button.addEventListener('contextmenu', (event) => event.preventDefault());
    // Keyboard and assistive tech activate with a click that has no pointer.
    button.addEventListener('click', (event) => { if (event.detail === 0) send(command); });
}

function buildBassSegments(max) {
    const container = $('bassSegments');
    container.replaceChildren();
    for (let value = 1; value <= max; value += 1) {
        const segment = document.createElement('button');
        segment.type = 'button';
        segment.dataset.value = String(value);
        segment.addEventListener('click', () => setLevel('bass', value));
        container.append(segment);
    }
    container.dataset.max = String(max);
}

function bindControls() {
    document.querySelectorAll('[data-repeat]').forEach(bindRepeat);
    document.querySelectorAll('[data-command]').forEach((button) => {
        button.addEventListener('click', () => send(button.dataset.command));
    });
    document.querySelectorAll('[data-input]').forEach((button) => {
        button.addEventListener('click', () => send(`input_${button.dataset.input}`));
    });

    $('calibrateBtn').addEventListener('click', calibrate);
    $('pairBtn').addEventListener('click', async () => {
        if (await ask('pair')) send('bluetooth_pair');
    });
    $('resetBtn').addEventListener('click', async () => {
        if (await ask('reset', { danger: true })) send('factory_reset');
    });
    $('quitBtn').addEventListener('click', quitApp);

    $('firstRunCalibrate').addEventListener('click', calibrate);
    $('firstRunLater').addEventListener('click', async () => {
        $('firstRun').hidden = true;
        try {
            status = await api('/api/preferences', { method: 'POST', body: { calibrationHintDismissed: true } });
        } catch (error) {
            toast(describeError(error), 'bad');
        }
        render();
    });

    $('langToggle').addEventListener('click', () => {
        lang = lang === 'en' ? 'zh-TW' : 'en';
        try { localStorage.setItem('z407.lang', lang); } catch { /* private mode */ }
        applyLanguage();
        // Also kept by the app itself, so the choice survives a different browser or a cleared cache.
        api('/api/preferences', { method: 'POST', body: { language: lang } }).catch(() => {});
    });

    $('copyUrl').addEventListener('click', async () => {
        try {
            await navigator.clipboard.writeText($('lanUrl').textContent);
            toast(t('phone.copied'));
        } catch { /* clipboard is unavailable on plain-http LAN pages */ }
    });

    document.addEventListener('keydown', (event) => {
        if (event.metaKey || event.ctrlKey || event.altKey) return;
        if (event.target.closest('button, input, dialog, summary, a, [role="slider"]')) return;
        if (!controlsReady()) return;
        const command = {
            ArrowUp: 'vol_up', ArrowDown: 'vol_down',
            ArrowRight: 'bass_up', ArrowLeft: 'bass_down',
            m: 'play_pause', M: 'play_pause',
        }[event.key];
        if (!command) return;
        event.preventDefault();
        throttledSend(command);
    });

    document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
}

/* ---------- Render ---------- */

function controlsReady() {
    return Boolean(status?.connected) && !offline && !status.busy && !localBusy;
}

function linkState() {
    if (offline || !status) return offline ? 'offline' : 'searching';
    if (status.connected) return 'connected';
    return {
        starting: 'searching', scanning: 'searching', not_found: 'searching',
        connecting: 'connecting', disconnected: 'disconnected', error: 'error',
    }[status.connectionState] || 'searching';
}

function hintFor(state) {
    if (state === 'offline') return [t('hint.offline'), 'bad'];
    if (!status || status.connected || !status.lastError) return null;
    const key = `hint.${status.lastErrorCode}`;
    if (I18N.en[key]) return [t(key), status.lastErrorCode === 'bluetooth_unavailable' ? 'bad' : 'warn'];
    return [t('hint.generic', { error: status.lastError }), 'warn'];
}

function render() {
    if (quitting) return;
    const state = linkState();
    const ready = controlsReady();

    $('connection').dataset.state = state;
    $('connectionText').textContent = t(`state.${state}`);
    $('demoBadge').hidden = !status?.demo;

    const hint = hintFor(state);
    $('hint').hidden = !hint;
    if (hint) {
        $('hint').textContent = hint[0];
        $('hint').dataset.tone = hint[1];
    }

    // First-run reminder: only until the first calibration (or "Not now").
    $('firstRun').hidden = !(status?.connected && !offline && status.volume == null
        && !status.calibrationHintDismissed && !status.busy);
    $('firstRunCalibrate').disabled = !ready;

    // Volume dial
    const volumeMax = status?.volumeMax ?? 32;
    if ($('dialTicks').dataset.max !== String(volumeMax)) buildDial(volumeMax);
    const actualVolume = status?.volume ?? null;
    const shownVolume = pending.volume ?? actualVolume;
    const dial = $('dial');
    dial.dataset.known = String(shownVolume != null);
    dial.dataset.draggable = String(ready && actualVolume != null);
    dial.dataset.busy = String(Boolean(status?.busy));
    dial.setAttribute('aria-valuemax', volumeMax);
    dial.setAttribute('aria-valuenow', shownVolume ?? 0);
    dial.setAttribute('aria-valuetext', shownVolume != null ? `${shownVolume} / ${volumeMax}` : t('volume.unknown'));
    dial.setAttribute('aria-disabled', String(!ready));
    $('dialTicks').querySelectorAll('.tick').forEach((tick, index) => {
        const lit = shownVolume != null && index >= 1 && index <= shownVolume;
        tick.classList.toggle('on', lit && pending.volume == null);
        tick.classList.toggle('preview', lit && pending.volume != null);
    });
    const [px, py] = polar(DIAL_START_DEG + ((shownVolume ?? 0) / volumeMax) * DIAL_SWEEP_DEG, 84);
    $('dialPointer').setAttribute('cx', px.toFixed(2));
    $('dialPointer').setAttribute('cy', py.toFixed(2));
    $('volumeValue').textContent = shownVolume ?? '–';
    $('volumeCaption').textContent = shownVolume != null ? t('volume.of', { max: volumeMax }) : t('volume.unknown');

    if (status?.busy) $('stageNote').textContent = t(`busy.${status.busy}`);
    else $('stageNote').textContent = actualVolume != null ? t('volume.dragHint') : t('volume.calibrateHint');

    // Bass
    const bassMax = status?.bassMax ?? 15;
    if ($('bassSegments').dataset.max !== String(bassMax)) buildBassSegments(bassMax);
    const actualBass = status?.bass ?? null;
    const shownBass = pending.bass ?? actualBass;
    $('bassValue').textContent = `${shownBass ?? '—'} / ${bassMax}`;
    $('bassSegments').dataset.known = String(actualBass != null);
    $('bassSegments').querySelectorAll('button').forEach((segment) => {
        const value = Number(segment.dataset.value);
        const lit = shownBass != null && value <= shownBass;
        segment.classList.toggle('on', lit && pending.bass == null);
        segment.classList.toggle('preview', lit && pending.bass != null);
        segment.disabled = !ready;
        segment.setAttribute('aria-label', t('bass.step', { value }));
    });

    // Input
    const activeInput = status?.input ?? null;
    document.querySelectorAll('[data-input]').forEach((button) => {
        button.setAttribute('aria-pressed', String(button.dataset.input === activeInput));
    });
    const preferred = status?.preferredInput || 'aux';
    $('inputNote').textContent = [
        activeInput ? t('input.active', { input: t(`input.${activeInput}`) }) : t('input.unknown'),
        activeInput === preferred ? '' : t('input.recommended', { input: t(`input.${preferred}`) }),
    ].filter(Boolean).join('\n');

    // Availability
    document.querySelectorAll('[data-needs-speaker]').forEach((el) => { el.disabled = !ready; });
    document.querySelectorAll('[data-host-media]').forEach((el) => {
        el.disabled = offline || !status || status.platform !== 'macos';
    });
    const isLocal = status?.localClient !== false;
    document.querySelectorAll('[data-local-only]').forEach((el) => { el.hidden = !isLocal; });
    $('localOnlyNote').hidden = isLocal;
    $('quitBtn').disabled = offline;

    // Phone address
    $('phonePanel').hidden = !(status?.lanUrl && isLocal);
    if (status?.lanUrl) $('lanUrl').textContent = status.lanUrl;
    $('copyUrl').hidden = !navigator.clipboard;
}

/* ---------- Start ---------- */

bindControls();
bindDial();
applyLanguage();
pollLoop();
