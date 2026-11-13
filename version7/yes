import queue
import threading
import json
import time

# --- QUEUE INFRASTRUCTURE ---
# Queue for Supervisor to send tasks to Worker
worker_task_queue = queue.Queue()

# Queue for Worker to send execution results back to Supervisor
supervisor_result_queue = queue.Queue()


class SupervisorAgent:
    """High-level agent responsible for user interaction, task breakdown, 

    delegation, and verifying execution quality.

    """
    def __init__(self, task_queue, result_queue):
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.task_counter = 0

    def process_user_request(self, user_prompt):
        print(f"\n[Supervisor] Received Goal: '{user_prompt}'")
        
        # Step 1: Break down request into actionable sub-tasks
        # (In practice, this is where you call your Gemini/Local LLM to plan)
        sub_tasks = [
            f"Execute step 1 for goal: {user_prompt}",
            f"Execute step 2 and verify state"
        ]

        # Step 2: Delegate sub-tasks to the Worker
        for task_desc in sub_tasks:
            self.task_counter += 1
            task_payload = {
                "task_id": f"TASK_{self.task_counter:03d}",
                "instruction": task_desc,
                "max_retries": 2
            }
            print(f"[Supervisor] Delegating -> {task_payload['task_id']}")
            self.task_queue.put(task_payload)

            # Step 3: Wait for and evaluate the worker's output
            self.verify_worker_output()

    def verify_worker_output(self):
        """Blocks briefly to wait for worker output and validates completion."""
        try:
            result = self.result_queue.get(timeout=30.0)
            print(f"[Supervisor] Reviewing {result['task_id']} | Status: {result['status']}")
            
            if result["status"] == "FAILURE":
                print(f"[Supervisor] Task failed! Error: {result.get('error')}. Course correcting...")
                # Here Supervisor can re-frame the task or switch models
            else:
                print(f"[Supervisor] Verification Passed: {result.get('output')}")
        except queue.Empty:
            print("[Supervisor Warning]: Worker timed out respond back!")


class WorkerAgent:
    """Execution agent responsible for interacting with PC tools 

    (my_tools4.py) and reporting hardware/execution results.

    """
    def __init__(self, task_queue, result_queue, tools_module=None):
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.tools = tools_module
        self.is_running = True

    def start_listener(self):
        """Runs in a background thread to continuously process tasks."""
        thread = threading.Thread(target=self._execution_loop, daemon=True)
        thread.start()

    def _execution_loop(self):
        while self.is_running:
            try:
                task = self.task_queue.get(timeout=0.5)
                if task.get("command") == "SHUTDOWN":
                    break

                task_id = task["task_id"]
                instruction = task["instruction"]
                print(f"  └── [Worker] Executing {task_id}: {instruction}")

                # --- TOOL EXECUTION / LOCAL INFERENCE HERE ---
                # Simulate task execution or call tools directly
                time.sleep(1) 
                
                # Report back to Supervisor
                response = {
                    "task_id": task_id,
                    "status": "SUCCESS",
                    "output": f"Completed: {instruction}"
                }
                self.result_queue.put(response)
                self.task_queue.task_done()

            except queue.Empty:
                continue


# --- EXAMPLE RUNTIME INITIALIZATION ---
if __name__ == "__main__":
    print("Initializing Multi-Agent System...")

    supervisor = SupervisorAgent(worker_task_queue, supervisor_result_queue)
    worker = WorkerAgent(worker_task_queue, supervisor_result_queue)

    # Start the worker thread
    worker.start_listener()

    # Pass a complex user prompt
    supervisor.process_user_request("Check my system stats and organize my files")