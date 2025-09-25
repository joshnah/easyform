import subprocess
import json
import re
import os
import sys
import tempfile

def get_base_dir():
    """Get the correct base directory for PyInstaller/frozen or dev environment."""
    if getattr(sys, 'frozen', False):  # Running as PyInstaller executable
        # Look for model folder next to the executable (copied manually)
        exe_dir = os.path.dirname(sys.executable)
        model_dir = os.path.join(exe_dir, 'model')
        
        if os.path.exists(model_dir):
            return model_dir
        
        # Fallback: check _MEIPASS (if model was included in build)
        if hasattr(sys, '_MEIPASS'):
            meipass_model = os.path.join(sys._MEIPASS, 'model')
            if os.path.exists(meipass_model):
                return meipass_model
        
        # Last resort: return the attempted directory for error reporting
        return model_dir
    print("Running in development mode")
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'model'))

# Path to your Genie executable and config
GENIE_DIR = get_base_dir()
GENIE_PATH = os.path.join(GENIE_DIR, "genie-t2t-run.exe")
CONFIG_FILE = os.path.join(GENIE_DIR, "genie_config.json")
print(f"GENIE_DIR: {GENIE_DIR}")
print(f"GENIE_PATH: {GENIE_PATH}")
print(f"CONFIG_FILE: {CONFIG_FILE}")
def validate_model_files():
    """Validate that required model files exist."""
    missing_files = []
    
    if not os.path.exists(GENIE_DIR):
        return [f"Model directory not found: {GENIE_DIR}"]
    
    if not os.path.exists(GENIE_PATH):
        missing_files.append(f"Genie executable not found: {GENIE_PATH}")
    
    if not os.path.exists(CONFIG_FILE):
        missing_files.append(f"Config file not found: {CONFIG_FILE}")
    
    return missing_files
def run_genie(prompt_file):
    """Run Genie executable with proper encoding handling."""
    print(f"Running Genie with prompt file: {prompt_file}")
    
    try:
        # Try with binary mode first to avoid encoding issues
        process = subprocess.Popen(
            [
                GENIE_PATH,
                "-c", CONFIG_FILE,
                "--prompt_file", prompt_file
            ],
            cwd=GENIE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        
        # Get output with timeout
        try:
            stdout_bytes, stderr_bytes = process.communicate(timeout=300)  # 5 minute timeout
        except subprocess.TimeoutExpired:
            process.kill()
            print("Genie process timed out")
            return None
        
        print(f"Genie return code: {process.returncode}")
        
        if process.returncode != 0:
            # Try to decode stderr
            try:
                stderr_text = stderr_bytes.decode('utf-8', errors='replace')
            except:
                stderr_text = str(stderr_bytes)
            print(f"Error running Genie: {stderr_text}")
            return None
        
        # Try to decode stdout with fallback encodings
        output_text = None
        for encoding in ['utf-8', 'cp1252', 'latin1']:
            try:
                output_text = stdout_bytes.decode(encoding)
                print(f"Successfully decoded with {encoding}")
                break
            except UnicodeDecodeError:
                continue
        
        if output_text is None:
            # Last resort: decode with errors='replace'
            output_text = stdout_bytes.decode('utf-8', errors='replace')
            print("Decoded with error replacement")
        
        output_text = output_text.strip()
        print(f"Raw output length: {len(output_text)}")
        
        # Extract content between [BEGIN] and [END] markers
        match = re.search(r'\[BEGIN\s*\]:([\s\S]*?)\[END\]', output_text)
        if match:
            extracted = match.group(1).strip()
            return extracted
        else:
            print("No [BEGIN]...[END] markers found")
            print(f"Full output preview: {output_text[:200]}...")
            return None
            
    except Exception as e:
        print(f"Exception in run_genie: {e}")
        return None

def response(prompt):
    """Write prompt to temporary file and process with Genie."""
    # Validate model files first
    missing_files = validate_model_files()
    if missing_files:
        print("Error: Missing model files:")
        for file in missing_files:
            print(f"  - {file}")
        return None
    
    # Format prompt for Llama3 chat template
    formatted_prompt = f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
    
    # Create temporary file and write prompt
    temp_file = None
    try:
        # Use system temp directory when frozen, model directory when in dev
        temp_dir = tempfile.gettempdir() if getattr(sys, 'frozen', False) else GENIE_DIR
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(
            mode='w+', 
            encoding='utf-8', 
            suffix='.txt', 
            dir=temp_dir,
            delete=False  # Don't auto-delete so we can debug if needed
        )
        
        # Clear file and write formatted prompt
        temp_file.seek(0)
        temp_file.truncate(0)  # Empty the file first
        temp_file.write(formatted_prompt)
        temp_file.flush()  # Ensure data is written
        temp_file.close()
        
        print(f"Wrote prompt to temporary file: {temp_file.name}")
        # Run Genie with the temporary file
        answer = run_genie(temp_file.name)
        
        return answer if answer else None
        
    except Exception as e:
        print(f"Error handling temporary file: {e}")
        return None
    finally:
        # Clean up temporary file
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.unlink(temp_file.name)
                print(f"Cleaned up temporary file: {temp_file.name}")
            except Exception as e:
                print(f"Warning: Could not delete temporary file {temp_file.name}: {e}")