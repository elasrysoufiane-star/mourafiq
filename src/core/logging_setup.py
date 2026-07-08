"""
Système de logs runtime — capture TOUTE la sortie console dans un fichier daté.

Le projet écrit partout via print() (dans plusieurs threads : AutoScene,
Conversation). Plutôt que de réécrire chaque appel avec le module logging, on
installe un « tee » sur sys.stdout / sys.stderr : chaque print() continue de
s'afficher à l'écran ET est écrit dans logs/mourafiq_AAAAMMJJ_HHMMSS.log, avec
l'heure + le nom du thread devant chaque ligne (précieux pour déboguer les
latences, timeouts API, l'ordre des threads).

- Écriture immédiate (flush par ligne) : rien n'est perdu sur Ctrl+C / crash.
- Thread-safe (verrou) : AutoScene et Conversation écrivent sans se mélanger.
- Console inchangée (pas d'horodatage à l'écran) — seul le fichier est annoté.
- stdlib uniquement, importable/testable sur Windows sans matériel.

Piloté par LOG_TO_FILE / LOG_KEEP_FILES (config/settings.py). setup_logging()
est appelé au tout début de src.core.app.main().
"""
import sys
import threading
from datetime import datetime
from pathlib import Path

_installed = False       # garde-fou : ne pas doubler le tee si appelé 2 fois
_original_stdout = None
_original_stderr = None
_logfile = None


class _LogWriter:
    """Écrit dans le fichier log, horodaté + nom du thread, thread-safe.
    Partagé par les tees stdout et stderr → un seul fichier cohérent."""

    def __init__(self, fileobj):
        self._file = fileobj
        self._lock = threading.Lock()
        self._need_prefix = True   # début d'une nouvelle ligne → préfixe à écrire

    def write(self, text):
        if not text:
            return
        with self._lock:
            morceaux = []
            for ligne in text.splitlines(keepends=True):
                if self._need_prefix:
                    morceaux.append(self._prefixe())
                    self._need_prefix = False
                morceaux.append(ligne)
                if ligne.endswith('\n'):
                    self._need_prefix = True
            self._file.write(''.join(morceaux))
            self._file.flush()

    @staticmethod
    def _prefixe():
        heure = datetime.now().strftime('%H:%M:%S')
        thread = threading.current_thread().name
        return f'[{heure} {thread}] '


class _Tee:
    """Redirige un flux (stdout/stderr) vers l'écran ET le fichier log.
    Délègue le reste (isatty, encoding, fileno…) au flux d'origine pour ne
    rien casser côté bibliothèques qui inspectent le flux."""

    def __init__(self, flux_original, writer):
        self._flux = flux_original
        self._writer = writer

    def write(self, text):
        self._flux.write(text)     # écran : verbatim, sans horodatage
        self._flux.flush()
        self._writer.write(text)   # fichier : horodaté + thread

    def flush(self):
        self._flux.flush()

    def __getattr__(self, nom):
        # Appelé seulement si l'attribut n'existe pas sur le Tee → délègue au flux
        return getattr(self._flux, nom)


def _nettoyer_anciens_logs(dossier: Path, garder: int) -> None:
    """Garde les `garder` fichiers .log les plus récents, supprime le reste
    (évite de saturer la carte SD du Pi au fil des lancements)."""
    if garder <= 0:
        return
    logs = sorted(dossier.glob('mourafiq_*.log'), key=lambda p: p.stat().st_mtime,
                  reverse=True)
    for ancien in logs[garder:]:
        try:
            ancien.unlink()
        except OSError:
            pass


def setup_logging(base_dir, to_file: bool = True, keep_files: int = 20):
    """Installe le tee stdout/stderr → fichier log daté. Idempotent.
    Retourne le chemin du fichier log, ou None si désactivé/échec."""
    global _installed, _original_stdout, _original_stderr, _logfile
    if _installed or not to_file:
        return None

    dossier = Path(base_dir) / 'logs'
    dossier.mkdir(exist_ok=True)
    _nettoyer_anciens_logs(dossier, keep_files)

    chemin = dossier / f"mourafiq_{datetime.now():%Y%m%d_%H%M%S}.log"
    try:
        _logfile = open(chemin, 'a', encoding='utf-8', buffering=1)  # line-buffered
    except OSError as e:
        print(f'AVERTISSEMENT: impossible d\'ouvrir le fichier log ({e}) — console seule')
        return None

    _logfile.write(f'=== Mourafiq — log démarré le {datetime.now():%Y-%m-%d %H:%M:%S} ===\n')
    _logfile.flush()

    writer = _LogWriter(_logfile)
    _original_stdout, _original_stderr = sys.stdout, sys.stderr
    sys.stdout = _Tee(_original_stdout, writer)
    sys.stderr = _Tee(_original_stderr, writer)
    _installed = True
    return chemin


def teardown_logging() -> None:
    """Restaure stdout/stderr et ferme le fichier (surtout utile aux tests)."""
    global _installed, _logfile
    if not _installed:
        return
    if _original_stdout is not None:
        sys.stdout = _original_stdout
    if _original_stderr is not None:
        sys.stderr = _original_stderr
    if _logfile is not None:
        try:
            _logfile.close()
        except OSError:
            pass
        _logfile = None
    _installed = False
