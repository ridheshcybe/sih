import time
import urllib.request
import json
import sys

OLLAMA_HOST = "https://ridheshcybepc.tailbc591e.ts.net:11434"

def get_running_models():
    """Fetches currently loaded models and their VRAM/CPU distribution from Ollama."""
    try:
        req = urllib.request.Request(f"{OLLAMA_HOST}/api/ps")
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode())
            return data.get("models", [])
    except Exception:
        return []

def unload_model(model_name):
    """Forces an immediate unload of a model by setting keep_alive to 0."""
    try:
        url = f"{OLLAMA_HOST}/api/generate"
        payload = json.dumps({"model": model_name, "keep_alive": 0}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5):
            print(f"🧹 [Auto-Manager] Successfully unloaded idle model: {model_name}")
    except Exception as e:
        print(f"⚠️ [Auto-Manager] Failed to unload {model_name}: {e}")

def preload_model(model_name):
    """Preloads a target model into memory with an indefinite keep-alive."""
    try:
        print(f"🚀 [Auto-Manager] Preloading priority model: {model_name}...")
        url = f"{OLLAMA_HOST}/api/generate"
        payload = json.dumps({"model": model_name, "keep_alive": -1}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120):
            print(f"✅ [Auto-Manager] {model_name} is locked into VRAM and ready.")
    except Exception as e:
        print(f"❌ [Auto-Manager] Error preloading {model_name}: {e}")

def monitor_loop(primary_model="qwen2.5-coder:7b-instruct", max_idle_minutes=10):
    print("🤖 Ollama Auto-Manager Daemon Started...")
    print(f"🎯 Target Primary Model: {primary_model}")
    print("--------------------------------------------------")

    # Initial preload so it's instantly ready for Cline
    preload_model(primary_model)

    while True:
        try:
            running = get_running_models()
            
            # Check resource congestion & memory management
            if len(running) > 2:
                print(f"⚠️ VRAM Congestion Detected ({len(running)} models active). Cleaning up...")
                for m in running:
                    name = m.get("name")
                    if name != primary_model:
                        unload_model(name)

            # Print status summary
            if running:
                status_str = ", ".join([f"{m['name']} ({m.get('processor', 'Unknown')})" for m in running])
                print(f"📊 Active VRAM/RAM State: [ {status_str} ]", end="\r")
            else:
                print("💤 No models currently active in memory.", end="\r")

        except KeyboardInterrupt:
            print("\nShutting down Auto-Manager.")
            sys.exit(0)
        except Exception:
            print("🔌 Waiting for Ollama server to spin up...", end="\r")

        time.sleep(10) # Check every 10 seconds

if __name__ == "__main__":
    # You can change the primary model argument here if needed
    target = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5-coder:7b-instruct"
    monitor_loop(primary_model=target)