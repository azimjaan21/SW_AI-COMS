# SW-AICOMS Package

A real-time AI surveillance system designed for industrial safety. This package provides high-performance detection for PPE, Fire, Forklifts, Danger Zone violations, and Fall Detection.

---

## 1. Setup Environment

### Clone the Repository
```bash
git clone <repo-url>
cd SW_AI-COMS

# Create the environment
python3 -m venv .venv

# Activate - Linux / Mac / NVIDIA Jetson
source .venv/bin/activate

# Activate - Windows
# .venv\Scripts\activate


Install Dependencies
Bash

pip install --upgrade pip
pip install -r requirements.txt
[!IMPORTANT]

NVIDIA Jetson Users: Do not install torch via pip. Use the pre-built JetPack wheels provided by NVIDIA to ensure GPU acceleration is enabled.

Standard PC Users (CUDA 12.1):

Bash

pip install torch torchvision torchaudio --index-url [https://download.pytorch.org/whl/cu121](https://download.pytorch.org/whl/cu121)
2. Prepare Models
Place your YOLO weights in the models/ directory. Ensure the filenames match the following:

ppe.pt — (PPE Detection)

fire.pt — (Fire/Smoke Detection)

forklift.pt — (Forklift/Vehicle Detection)

yolo11s-pose.pt — (For Danger Zone & Fall Detection)

3. Run the Flask App
Start the web server by running the application script:

Bash

python app.py
The server will initialize and become available at: http://0.0.0.0:5000/

4. Using the Web Interface
Open Browser: Navigate to http://localhost:5000/.

Upload Video: Use the upload button in the left 70% video window to select your footage.

Configure Tasks: * Select detection modules from the right-side list (PPE, Fire, Forklift).

For Danger Zone, use the interactive tool to draw your restricted area.

Start Analysis: Click the Start button to begin real-time processing.

Monitor: View real-time annotated frames and safety alerts directly in the browser.