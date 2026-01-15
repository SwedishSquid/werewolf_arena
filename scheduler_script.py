import subprocess
import sys
from pathlib import Path


def run_and_log(command, log_filename):
    """
    Runs a command, streams output to console, and logs to file.
    """
    print("=" * 80)
    print(f"--- Starting: {' '.join(command)} ---")
    print(f"--- Logging to: {log_filename} ---")
    assert not Path(log_filename).exists(), "shall not override log files"
    with open(log_filename, 'w', encoding='utf-8') as log_file:
        # Popen allows us to run the process and keep control
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # Merge stderr into stdout to catch errors in the same log
            text=True,                # Decode bytes to strings automatically
            bufsize=1,                # Line buffered
            encoding='utf-8',
        )

        # Iterate over the output line by line as it is generated
        for line in process.stdout:
            # 1. Write to console (sys.stdout)
            sys.stdout.write(line)
            sys.stdout.flush() # Ensure it appears immediately

            # 2. Write to file
            log_file.write(line)
            log_file.flush() # Uncomment if you want the file updated instantly, not just on buffer fill

        # Wait for process to finish to get return code
        return_code = process.wait()
    
    print(f"--- Finished with exit code: {return_code} ---\n")

# ==========================================
# Configuration: Define your commands here
# ==========================================

# Example: We run the dummy script 3 times with different arguments

path_to_shell_logs = (Path(__file__).parent / "shell_logs").resolve()

command = ["python", "-u", "main.py", "--model_pool", "deepseek/deepseek-chat-v3.1,meta-llama/llama-3.3-70b-instruct,x-ai/grok-4.1-fast,qwen/qwen3-235b-a22b-2507,mistralai/devstral-2512,tngtech/deepseek-r1t2-chimera:free,google/gemini-2.5-flash-lite,openai/gpt-oss-120b:free"]

start_run = 20
n_runs = 10

tasks = [
    # [Command List], Output Filename
    # (["python", "-u", "dummy_task.py", "First_Run", "3"], "log_1.txt"),
    # (["python", "-u", "dummy_task.py", "Second_Run", "2"], "log_2.txt"),
    # (["python", "-u", "dummy_task.py", "Third_Run", "4"], "log_3.txt"),
    # (["python", "-u", "dummy_task.py", "Example_Task", "5"], "example_task_log.txt"),
    (command, str(path_to_shell_logs / f"run_{i}_log.txt")) for i in range(start_run, start_run + n_runs)
]

print(f"executing {len(tasks)} commands")

if __name__ == "__main__":
    for command, filename in tasks:
        run_and_log(command, filename)