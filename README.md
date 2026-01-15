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
.venv\Scripts\activate

```
## Install Dependencies
```Bash

pip install --upgrade pip
pip install -r requirements.txt
pip install torch torchvision torchaudio --index-url [https://download.pytorch.org/whl/cu121](https://download.pytorch.org/whl/cu121)
```
## 2. Prepare Models
Place your YOLO weights in the models/ directory. Ensure the filenames match the following:

ppe.pt — (PPE Detection)

fire.pt — (Fire/Smoke Detection)

forklift.pt — (Forklift/Vehicle Detection)

yolo11s-pose.pt — (For Danger Zone & Fall Detection)

## 3. Run the Flask App
Start the web server by running the application script:
```
python app.py
```
The server will initialize and become available at: 

## 4. Using the Web Interface
Open Browser: Navigate to **http://127.0.0.1:5000/**

## 5. Upload Video or Add RTSP CAM URL:
<img width="1916" height="959" alt="image" src="https://github.com/user-attachments/assets/3940f19c-0f7e-49bb-8e2e-05ba9f105e11" />


# Configure Tasks: * Select detection modules from the right-side list (PPE, Fire, Forklift):
<img width="587" height="557" alt="image" src="https://github.com/user-attachments/assets/48580c33-c99c-4081-b67d-2d374fb182b3" />



## **Start Stream**: Button to begin real-time processing.

--------

## Monitor: View real-time annotated frames and safety alerts directly in the browser.

<img width="1912" height="896" alt="image" src="https://github.com/user-attachments/assets/910ef65c-76f9-4352-82a2-ab02320d11a6" />
