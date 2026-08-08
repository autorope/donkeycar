"""
Local web viewer for Grad-CAM uncertainty analyses (Feature 4 of the
uncertainty toolkit) -- and, when no analysis is given yet, a small local
GUI ("launcher") for running one, so you never have to type the full
``python -m donkeycar.parts.gradcam_uncertainty --tub ... --model ...``
command line by hand.

Serves the output folder produced by ``donkeycar.parts.gradcam_uncertainty``
together with a small self-contained web page (no internet required) that
provides:

  * the camera frame with the uncertainty-map overlay (or mean attention,
    novelty, saliency, or the plain frame),
  * a confidence-over-time graph for the whole drive with the current
    position marked, click-to-jump,
  * video-like playback (play/pause at a configurable 2-10 fps, scrub bar,
    arrow-key stepping, optional "analysed frames only" mode).

Frames without a precomputed uncertainty map simply show the camera frame
(from the analysis dir if it was created with ``--export-frames``, else
straight from the tub's images/ folder when the tub is available locally).

**Launcher mode**: if ``--analysis`` is omitted (or points at a directory
with no ``data.json`` yet), the server shows a form instead of the viewer:
pick a tub and model (autodiscovered from ``data/`` and ``models/`` in the
current directory, or typed by hand), choose which frames to analyse, and
click Run. The analysis runs in this same process on a background thread
(reusing ``gradcam_uncertainty.analyze_tub`` directly -- no subprocess), the
page polls progress, and once done the server starts serving the viewer for
the new output directory automatically -- no second command.

Usage:
    python -m donkeycar.parts.uncertainty_viewer [--analysis <dir>] \
        [--tub <tub_dir>] [--config <config.py>] [--port 8890] [--host 127.0.0.1]

Then open http://localhost:8890 in a browser.
"""
import argparse
import copy
import json
import logging
import os
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

logger = logging.getLogger(__name__)

HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         'uncertainty_viewer.html')
LAUNCHER_HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'analysis_launcher.html')


class LauncherState:
    """
    Owns the background analysis thread and its progress state. One instance
    per server process, shared (read via a lock) across request-handling
    threads.
    """

    def __init__(self, cfg, cwd):
        self.cfg = cfg
        self.cwd = cwd
        self._lock = threading.Lock()
        self._progress = {'running': False, 'done': False, 'error': None,
                          'stage': None, 'current': 0, 'total': 0,
                          'out_dir': None, 'calibration_warning': None}

    def progress_snapshot(self):
        with self._lock:
            return dict(self._progress)

    def _set(self, **kwargs):
        with self._lock:
            self._progress.update(kwargs)

    def scan_defaults(self):
        """Best-effort discovery of tub dirs (contain manifest.json) and
        model .h5 files under the current directory, for the form's
        suggestion lists. Returns {} entries if nothing found -- the form
        fields are free text either way."""
        tubs = []
        data_dir = os.path.join(self.cwd, 'data')
        if os.path.isfile(os.path.join(data_dir, 'manifest.json')):
            tubs.append('data')
        if os.path.isdir(data_dir):
            for name in sorted(os.listdir(data_dir)):
                p = os.path.join(data_dir, name)
                if os.path.isdir(p) and os.path.isfile(
                        os.path.join(p, 'manifest.json')):
                    tubs.append(os.path.join('data', name))

        models = []
        models_dir = os.path.join(self.cwd, 'models')
        if os.path.isdir(models_dir):
            for name in sorted(os.listdir(models_dir)):
                lower = name.lower()
                # Skip the OOD-encoder sidecars this toolkit writes next to
                # each model (<model>.novelty_encoder.h5). They're .h5 files
                # but not pilots, and offering them here doubles the list with
                # entries that can only ever fail if picked.
                if lower.endswith('.novelty_encoder.h5'):
                    continue
                if lower.endswith('.h5'):
                    models.append(os.path.join('models', name))

        return {'tubs': tubs, 'models': models}

    def tub_record_count(self, tub_path):
        """
        Best-effort total record count for a tub, read from its
        ``manifest.json`` (a few small JSON-per-line records -- no need to
        load the whole catalog dataset just to size the form's validation).
        Returns None if it can't be determined (bad path, unexpected
        manifest format).
        """
        manifest_path = os.path.join(
            os.path.expanduser(tub_path), 'manifest.json')
        if not os.path.isfile(manifest_path):
            return None
        try:
            with open(manifest_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    d = json.loads(line)
                    if isinstance(d, dict) and 'current_index' in d:
                        n_deleted = len(d.get('deleted_indexes', []))
                        return max(0, d['current_index'] - n_deleted)
        except Exception as e:
            logger.debug(f'tub_record_count({tub_path}) failed: {e}')
        return None

    def training_tubs_for_model(self, model_path):
        """Best-effort lookup of the tub(s) `model_path` was actually trained
        on (see ``mc_calibrate.find_training_tubs``), for pre-filling the
        form's "Calibration tub" field. Returns None if unknown."""
        try:
            from donkeycar.parts.mc_calibrate import find_training_tubs
            return find_training_tubs(self.cfg, os.path.expanduser(model_path))
        except Exception as e:
            logger.debug(f'training_tubs_for_model({model_path}) failed: {e}')
            return None

    def saved_pipeline_for_model(self, model_path):
        """
        Read `model_path`'s ``.preprocessing.json`` sidecar (written by
        training, see ``image_transformations.save_preprocessing_metadata``)
        and return its recorded pipeline, so the form can show what a model
        actually expects before the user decides whether to accept this
        launcher's config or type an override. Returns None if no sidecar
        exists (e.g. a model trained before this tracking existed).
        """
        from donkeycar.parts.image_transformations import _sidecar_path_for
        sidecar_path = _sidecar_path_for(os.path.expanduser(model_path))
        if not os.path.isfile(sidecar_path):
            return None
        try:
            with open(sidecar_path) as f:
                saved = json.load(f)
        except Exception as e:
            logger.debug(f'saved_pipeline_for_model({model_path}) failed: {e}')
            return None
        return {
            'pipeline_steps': saved.get('pipeline_steps'),
        }

    def has_calibration(self, model_path):
        """Whether `model_path` already has a saved `<model>.calib.json`
        (see ``mc_calibrate.default_calib_path``), for the form's
        auto-calibrate checkbox default."""
        from donkeycar.parts.mc_calibrate import default_calib_path
        return os.path.isfile(
            default_calib_path(os.path.expanduser(model_path)))

    def start(self, form):
        with self._lock:
            if self._progress['running']:
                raise RuntimeError('An analysis is already running.')
            self._progress = {'running': True, 'done': False, 'error': None,
                              'stage': 'starting', 'current': 0, 'total': 0,
                              'out_dir': None, 'calibration_warning': None}
        thread = threading.Thread(target=self._run, args=(form,), daemon=True)
        thread.start()

    def _run(self, form):
        try:
            tub = form['tub']
            model = form['model']
            if not tub or not model:
                raise ValueError('Tub and model paths are required.')
            mode = form.get('mode', 'top_k')
            out_dir = form.get('out') or os.path.join(
                os.path.expanduser(tub), 'gradcam_analysis')

            def cb(stage, current, total):
                self._set(stage=stage, current=current, total=total)

            # This server's cfg is fixed at startup (from --config), so it
            # was almost never trained alongside every model the form could
            # point at -- it's the wrong pipeline for any model that used a
            # different one. A comma-separated override in the form lets the
            # user say "use THIS pipeline for this run" instead of restarting
            # the whole launcher with a different --config per model.
            # Applied to POST_TRANSFORMATIONS, matching how this project
            # actually uses these settings (TRANSFORMATIONS stays empty,
            # everything goes in POST_TRANSFORMATIONS). copy.copy() so the
            # override never leaks
            # into self.cfg and affect a later run that doesn't ask for it.
            override_raw = (form.get('transformations_override') or '').strip()
            if override_raw:
                override_steps = [s.strip().upper() for s in
                                  override_raw.split(',') if s.strip()]
                run_cfg = copy.copy(self.cfg)
                run_cfg.POST_TRANSFORMATIONS = override_steps
                verify_preprocessing = False
                logger.info(
                    f'Transformations override from the form: '
                    f'POST_TRANSFORMATIONS={override_steps} for this run '
                    f'only. Skipping the saved-pipeline check since this is '
                    f'an explicit override.')
            else:
                run_cfg = self.cfg
                verify_preprocessing = True

            from donkeycar.parts.mc_calibrate import (default_calib_path,
                                                      calibrate_from_tub,
                                                      find_training_tubs)
            calib_path = default_calib_path(os.path.expanduser(model))
            # Auto-calibrate models that have never been calibrated, so a
            # first-time user gets confidence/novelty %% without having to
            # know `mc_calibrate` exists as a separate command. Opt-out via
            # the form checkbox; a calibration failure here degrades to the
            # pre-existing behaviour (variance-only) rather than blocking the
            # analysis the user actually asked for.
            #
            # IMPORTANT: calibration establishes "what does normal (training)
            # data look like" -- it must run against the tub(s) the model was
            # actually TRAINED on, not necessarily the tub being analysed here
            # (which is very often a separate inference/test drive). Using the
            # analysis tub as the calibration baseline would make novelty mean
            # "unlike this other drive" instead of "unlike what the model
            # learned" -- silently defeating the point of the signal. Priority
            # order: (1) a tub the user explicitly typed into the "Calibration
            # tub" field, (2) the real training tub(s) looked up from
            # DonkeyCar's own training database, (3) the analysis tub as a
            # last resort -- with a visible warning, not just a log line, for
            # (3) since it's the one case that's likely wrong.
            if (form.get('auto_calibrate', True)
                    and not os.path.exists(calib_path)):
                calib_tub_override = (form.get('calib_tub') or '').strip()
                if calib_tub_override:
                    calib_tubs = [t.strip() for t in
                                 calib_tub_override.split(',') if t.strip()]
                    logger.info(f'No calibration at {calib_path}; '
                                f'auto-calibrating against the user-specified '
                                f'tub(s): {calib_tubs}')
                else:
                    training_tubs = find_training_tubs(run_cfg, model)
                    if training_tubs:
                        calib_tubs = training_tubs
                        logger.info(f'No calibration at {calib_path}; '
                                    f'auto-calibrating against this model\'s '
                                    f'recorded training tub(s): {calib_tubs}')
                    else:
                        calib_tubs = [tub]
                        warning = (
                            f'Could not find this model\'s recorded training '
                            f'tub (no models/database.json entry, and no '
                            f'"Calibration tub" was specified), so '
                            f'calibration used the ANALYSIS tub ({tub}) '
                            f'instead. If that is not the tub this model was '
                            f'actually trained on, confidence/novelty %% here '
                            f'are calibrated against the wrong baseline -- '
                            f'specify the real training tub and recalibrate '
                            f'for meaningful numbers.')
                        logger.warning(warning)
                        self._set(calibration_warning=warning)
                try:
                    # Calibration replays training-tub frames through
                    # TRANSFORMATIONS/POST_TRANSFORMATIONS too (it needs to
                    # see what the model actually sees), so it must use the
                    # same run_cfg as the analysis below - otherwise the
                    # baseline and the analysis would be built from two
                    # different pipelines, corrupting the novelty stats.
                    calibrate_from_tub(run_cfg, calib_tubs, model,
                                       progress_callback=cb)
                except Exception as e:
                    # Surfaced to the UI (not just logged) -- a bad tub path
                    # here was previously silently swallowed, leaving the user
                    # with no calibration and no idea why.
                    msg = (f'Auto-calibration against {calib_tubs} failed: '
                          f'{e}. Continuing without it -- confidence/'
                          f'novelty %% will be unavailable.')
                    logger.warning(msg)
                    self._set(calibration_warning=msg)

            from donkeycar.parts.gradcam_uncertainty import analyze_tub
            analyze_tub(
                run_cfg, tub, model, out_dir,
                num_passes=getattr(run_cfg, 'XAI_CONFIDENCE_PASSES', 15),
                alpha=getattr(run_cfg, 'XAI_CONFIDENCE_ALPHA', 0.2),
                ig_steps=getattr(run_cfg, 'XAI_IG_STEPS', 32),
                verify_preprocessing=verify_preprocessing,
                top_k=int(form['value']) if mode == 'top_k'
                      and form.get('value') else 50,
                percentile=float(form['value']) if mode == 'percentile'
                          and form.get('value') else None,
                analyze_all=(mode == 'all'),
                limit=int(form['limit']) if form.get('limit') else None,
                start=int(form['start']) if form.get('start') else None,
                export_frames=bool(form.get('export_frames')),
                progress_callback=cb)

            # Point the viewer at the freshly-produced analysis.
            ViewerHandler.active_dir = os.path.abspath(out_dir)
            candidate = os.path.join(os.path.expanduser(tub), 'images')
            ViewerHandler.tub_images_dir = \
                os.path.abspath(candidate) if os.path.isdir(candidate) else None

            self._set(running=False, done=True, out_dir=out_dir)
        except Exception as e:
            logger.exception('Analysis failed')
            self._set(running=False, done=True, error=str(e))


class ViewerHandler(SimpleHTTPRequestHandler):
    """
    Serves either the analysis viewer (if ``active_dir`` has a ready
    ``data.json``) or the launcher form (otherwise), plus a small JSON API
    for the launcher (``/api/scan``, ``/api/run``, ``/api/progress``) and raw
    camera frames at ``/tub/<filename>`` when a tub is available.

    ``active_dir``/``tub_images_dir``/``launcher_state`` are mutable class
    attributes rather than constructor args, because ``http.server`` creates
    a fresh handler instance per request -- setting them here lets the
    *directory being served* change at runtime (e.g. once a launcher-mode
    analysis finishes) without restarting the server.
    """

    tub_images_dir = None
    active_dir = None
    launcher_state = None

    def __init__(self, *args, **kwargs):
        # NEVER fall back to os.getcwd(): in launcher mode that would hand the
        # whole car directory -- myconfig.py and its credentials, models, tubs
        # -- to anyone who can reach this port, which with --host 0.0.0.0 is
        # the entire network. Serve only a real analysis dir; static file
        # requests are refused outright until one exists (see _serve_static).
        directory = ViewerHandler.active_dir or os.path.dirname(
            os.path.abspath(__file__))
        super().__init__(*args, directory=directory, **kwargs)

    def _serve_static(self, method):
        """Hand off to the base handler, but only once an analysis directory
        is actually being served."""
        if ViewerHandler.active_dir is None:
            return self.send_error(404, 'No analysis is being served yet.')
        return method()

    def _analysis_ready(self):
        return (ViewerHandler.active_dir is not None
                and os.path.isfile(
                    os.path.join(ViewerHandler.active_dir, 'data.json')))

    def do_GET(self):
        if self.path.startswith('/') and '?' in self.path:
            path, query = self.path.split('?', 1)
        else:
            path, query = self.path, ''

        if path in ('/', '/index.html'):
            force_launcher = 'new=1' in query
            if not force_launcher and self._analysis_ready():
                return self._send_file(HTML_PATH, 'text/html; charset=utf-8')
            if ViewerHandler.launcher_state is not None:
                return self._send_file(LAUNCHER_HTML_PATH,
                                       'text/html; charset=utf-8')
            return self.send_error(
                404, 'No analysis available and launcher mode is off '
                     '(pass --analysis, or run without it to enable the '
                     'launcher).')

        if path == '/api/scan':
            if ViewerHandler.launcher_state is None:
                return self.send_error(404)
            return self._send_json(ViewerHandler.launcher_state.scan_defaults())

        if path == '/api/progress':
            if ViewerHandler.launcher_state is None:
                return self._send_json({})
            return self._send_json(
                ViewerHandler.launcher_state.progress_snapshot())

        if path == '/api/tub_info':
            if ViewerHandler.launcher_state is None:
                return self.send_error(404)
            tub = parse_qs(query).get('tub', [''])[0]
            if not tub:
                return self._send_json({'error': 'no tub given'}, status=400)
            n = ViewerHandler.launcher_state.tub_record_count(tub)
            if n is None:
                return self._send_json(
                    {'error': f'could not read manifest.json for {tub}'},
                    status=404)
            return self._send_json({'n_records': n})

        if path == '/api/training_tubs':
            if ViewerHandler.launcher_state is None:
                return self.send_error(404)
            model = parse_qs(query).get('model', [''])[0]
            if not model:
                return self._send_json({'error': 'no model given'}, status=400)
            tubs = ViewerHandler.launcher_state.training_tubs_for_model(model)
            return self._send_json({'tubs': tubs})

        if path == '/api/model_info':
            if ViewerHandler.launcher_state is None:
                return self.send_error(404)
            model = parse_qs(query).get('model', [''])[0]
            if not model:
                return self._send_json({'error': 'no model given'}, status=400)
            info = ViewerHandler.launcher_state.saved_pipeline_for_model(model)
            result = info or {'pipeline_steps': None}
            result['has_calibration'] = \
                ViewerHandler.launcher_state.has_calibration(model)
            return self._send_json(result)

        if path.startswith('/tub/'):
            if not self.tub_images_dir:
                return self.send_error(404, 'tub not available')
            # basename() blocks any path traversal
            name = os.path.basename(path[len('/tub/'):])
            file_path = os.path.join(self.tub_images_dir, name)
            if not os.path.isfile(file_path):
                return self.send_error(404)
            ctype = 'image/png' if name.lower().endswith('.png') \
                else 'image/jpeg'
            return self._send_file(file_path, ctype)

        # everything else (data.json, images/, frames/) comes from
        # active_dir via the base handler
        return self._serve_static(super().do_GET)

    def do_HEAD(self):
        return self._serve_static(super().do_HEAD)

    def do_POST(self):
        if self.path == '/api/run':
            if ViewerHandler.launcher_state is None:
                return self.send_error(404)
            length = int(self.headers.get('Content-Length', 0))
            try:
                form = json.loads(self.rfile.read(length)) if length else {}
                ViewerHandler.launcher_state.start(form)
                return self._send_json({'ok': True})
            except Exception as e:
                return self._send_json({'ok': False, 'error': str(e)},
                                       status=400)
        return self.send_error(404)

    def _send_file(self, path, ctype):
        try:
            with open(path, 'rb') as f:
                body = f.read()
        except OSError:
            return self.send_error(404)
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        logger.debug(fmt % args)


def _load_config(config_path):
    from donkeycar.parts.image_transformations import \
        load_config_and_myconfig
    return load_config_and_myconfig(config_path)


def main(args=None):
    parser = argparse.ArgumentParser(
        prog='uncertainty_viewer',
        description='Web viewer (and analysis launcher) for Grad-CAM '
                    'uncertainty analyses.')
    parser.add_argument('--analysis', default=None,
                        help='analysis dir produced by gradcam_uncertainty '
                             '(must contain data.json). Omit to start in '
                             'launcher mode and run a new analysis from the '
                             'browser.')
    parser.add_argument('--tub', default=None,
                        help='tub dir for camera frames of non-analysed '
                             'frames (default: the tub path recorded in '
                             'data.json, if it exists on this machine)')
    parser.add_argument('--config', default=None,
                        help='path to config.py, used by launcher mode when '
                             'starting a new analysis (defaults to '
                             './config.py, falling back to bundled defaults)')
    parser.add_argument('--port', type=int, default=8890)
    parser.add_argument('--host', default='127.0.0.1',
                        help='bind address (use 0.0.0.0 to allow access '
                             'from other machines)')
    parsed = parser.parse_args(args)

    cwd = os.getcwd()
    cfg = _load_config(parsed.config)
    ViewerHandler.launcher_state = LauncherState(cfg, cwd)

    if parsed.analysis:
        analysis_dir = os.path.abspath(os.path.expanduser(parsed.analysis))
        data_json = os.path.join(analysis_dir, 'data.json')
        if os.path.isfile(data_json):
            ViewerHandler.active_dir = analysis_dir
            tub_dir = parsed.tub
            if tub_dir is None:
                with open(data_json) as f:
                    tub_dir = json.load(f).get('tub')
            if tub_dir:
                candidate = os.path.join(os.path.expanduser(tub_dir), 'images')
                if os.path.isdir(candidate):
                    ViewerHandler.tub_images_dir = os.path.abspath(candidate)
        else:
            logger.warning(f'{analysis_dir} has no data.json yet; starting '
                           f'in launcher mode instead.')

    logger.info(f'Analysis dir : {ViewerHandler.active_dir or "(none yet -- launcher mode)"}')
    if ViewerHandler.tub_images_dir:
        logger.info(f'Tub images   : {ViewerHandler.tub_images_dir}')

    server = ThreadingHTTPServer((parsed.host, parsed.port), ViewerHandler)
    shown_host = 'localhost' if parsed.host in ('127.0.0.1', '0.0.0.0') \
        else parsed.host
    print(f'\nUncertainty viewer running at '
          f'http://{shown_host}:{parsed.port}  (Ctrl+C to stop)\n')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
