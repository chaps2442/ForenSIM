import os
import sys
import subprocess
import threading
import queue
import datetime


def get_python_executable():
    """Interpreteur utilise pour lancer pySim-shell en sous-processus.

    On reutilise le MEME interpreteur que celui qui fait tourner ForenSIM
    (sys.executable), afin que le moteur pySim importe ses dependances
    (osmocom / pyosmocom, pyscard, ...) depuis l'environnement ou elles ont
    ete installees. Evite le piege classique ou ForenSIM est lance avec
    `py -3.14` mais le sous-processus tapait un `python` different sur le PATH.
    Repli sur "python" si sys.executable est indisponible (builds geles).
    """
    return sys.executable or "python"


def preflight_osmocom(python_exe=None, timeout=10):
    """Verifie que le module 'osmocom' (paquet pyosmocom) est importable.

    Depuis 2024, pySim a deplace ses utilitaires internes dans un paquet
    PyPI separe : 'pyosmocom' (importe sous le nom 'osmocom'). S'il manque,
    pySim-shell.py plante avec 'ModuleNotFoundError: No module named osmocom'
    EN PLEINE extraction -> rapport vide + scelle trompeur. On le detecte
    donc en amont, avant de lancer quoi que ce soit sur la carte.

    Retourne (ok: bool, message: str).
    """
    if python_exe is None:
        python_exe = get_python_executable()
    try:
        proc = subprocess.run(
            [python_exe, "-c",
             "import osmocom, sys; sys.stdout.write(getattr(osmocom, '__file__', 'ok'))"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=timeout,
        )
    except FileNotFoundError:
        return False, f"Interpreteur Python introuvable : {python_exe}"
    except subprocess.TimeoutExpired:
        return False, "Timeout lors de la verification du module osmocom."
    except Exception as e:
        return False, f"Erreur inattendue lors du pre-flight osmocom : {e}"

    if proc.returncode == 0:
        return True, "osmocom OK"

    err = (proc.stderr or "").strip()
    if "No module named 'osmocom'" in err or "ModuleNotFoundError" in err:
        return False, (
            "Le module 'osmocom' (moteur pySim) est introuvable.\n"
            "  -> Corrige avec :  pip install pyosmocom\n"
            "     (ou, dans ton dossier pySim :  pip install -r requirements.txt)\n"
            "  Rappel : pySim >= 2024 a deplace ses utilitaires dans le paquet\n"
            "  PyPI 'pyosmocom'."
        )
    return False, f"Erreur d'import osmocom :\n{err[:500]}"


def preflight_pysim_engine(pysim_path, python_exe=None, timeout=20):
    """Pre-flight GENERIQUE du moteur pySim (V2.04).

    Lance `python pySim-shell.py --help`. Comme tous les imports du moteur
    (osmocom, cmd2, ...) s'executent AVANT que argparse n'affiche l'aide,
    un demarrage propre (returncode 0 + 'usage') prouve que TOUTES les
    dependances sont satisfaites. Sinon on renvoie la sortie d'erreur avec
    un indice cible (osmocom, cmd2, module manquant).

    Retourne (ok: bool, message: str).
    """
    import re
    if python_exe is None:
        python_exe = get_python_executable()
    shell = os.path.join(pysim_path, "pySim-shell.py")
    if not os.path.isfile(shell):
        return False, ("pySim-shell.py introuvable dans :\n  %s\n"
                       "Verifie le chemin du dossier pySim." % pysim_path)
    env = os.environ.copy()
    env["PYTHONPATH"] = pysim_path
    try:
        proc = subprocess.run(
            [python_exe, shell, "--help"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=timeout, env=env,
        )
    except FileNotFoundError:
        return False, f"Interpreteur Python introuvable : {python_exe}"
    except subprocess.TimeoutExpired:
        return False, "Timeout au demarrage de pySim-shell.py (pre-flight)."
    except Exception as e:
        return False, f"Erreur inattendue au pre-flight moteur : {e}"

    out = proc.stdout or ""
    if proc.returncode == 0 and ("usage" in out.lower() or "pySim" in out):
        return True, "Moteur pySim OK"

    hint = ""
    if "No module named 'osmocom'" in out:
        hint = "\n  -> pip install pyosmocom   (module 'osmocom' manquant)"
    elif "cmd2" in out and ("ImportError" in out or "cannot import name" in out):
        hint = ("\n  -> Version cmd2 incompatible avec ton clone pySim."
                "\n     Corrige : cd <dossier pySim> && git pull && "
                "pip install -r requirements.txt")
    else:
        m = re.search(r"No module named '([^']+)'", out)
        if m:
            hint = ("\n  -> Module manquant : %s   (pip install %s)"
                    % (m.group(1), m.group(1)))
    return False, ("Le moteur pySim ne demarre pas "
                   "(pySim-shell.py --help a echoue)." + hint +
                   "\n\n--- Sortie moteur ---\n" + out[-1200:])


class PySimRunner:
    def __init__(self, pysim_path, reader_idx, output_dir, ui_queue):
        self.pysim_path = pysim_path
        self.reader_idx = str(reader_idx)
        self.output_dir = output_dir
        self.ui_queue = ui_queue
        self.process = None
        self.is_running = False

    def _enqueue_output(self, out, queue_obj, log_file_obj):
        try:
            for line in iter(out.readline, ''):
                decoded = line
                if log_file_obj and not log_file_obj.closed:
                    log_file_obj.write(decoded)
                    log_file_obj.flush()
                queue_obj.put(decoded)
        finally:
            out.close()

    def run_script(self, cmds, log_filename="output.txt"):
        self.is_running = True
        os.makedirs(self.output_dir, exist_ok=True)
        script_path = os.path.join(self.output_dir, "temp_cmds.txt")
        
        with open(script_path, "w") as f:
            f.write(cmds)
            
        shell_path = os.path.join(self.pysim_path, "pySim-shell.py")
        # On utilise le meme interpreteur que ForenSIM (voir get_python_executable)
        cmd = [get_python_executable(), shell_path, "-p", self.reader_idx, "--pcsc-shared", "--noprompt", "--script", script_path]
        
        env = os.environ.copy()
        env["PYTHONPATH"] = self.pysim_path
        
        log_path = os.path.join(self.output_dir, log_filename)
        out_f = open(log_path, "w")
        
        try:
            self.process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                env=env,
                bufsize=1,
                text=True
            )
            
            # Read stdout line by line and queue it for the UI
            q_thread = threading.Thread(target=self._enqueue_output, args=(self.process.stdout, self.ui_queue, out_f))
            q_thread.daemon = True
            q_thread.start()
            
            self.process.wait()
            q_thread.join()
            
            # Read whatever got into the log
            # Since we consumed stdout, we should also manually write the lines to log_path if we want,
            # or we rely on the UI to save the final log. 
            # For now, let's just let the UI handle displaying it.
        except Exception as e:
            self.ui_queue.put(f"[!] Error running PySim: {str(e)}\n")
        finally:
            out_f.close()
            if os.path.exists(script_path):
                os.remove(script_path)
            self.is_running = False
            self.ui_queue.put("===PROCESS_DONE===")

    def stop(self):
        if self.process and self.is_running:
            self.process.terminate()
            self.ui_queue.put("\n[!] FORCED STOP.\n")
