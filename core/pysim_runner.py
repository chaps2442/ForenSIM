import os
import subprocess
import threading
import queue
import datetime

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
        cmd = ["python", shell_path, "-p", self.reader_idx, "--pcsc-shared", "--noprompt", "--script", script_path]
        
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
