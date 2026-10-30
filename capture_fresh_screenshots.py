import os
import time
import subprocess
import requests

CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
OUT_DIR = os.path.abspath("assets/slides")
os.makedirs(OUT_DIR, exist_ok=True)

def capture_chrome(url, output_filename, width=1440, height=900, delay_ms=2500):
    out_path = os.path.join(OUT_DIR, output_filename)
    cmd = [
        CHROME_BIN,
        "--headless=new",
        f"--screenshot={out_path}",
        f"--window-size={width},{height}",
        f"--virtual-time-budget={delay_ms}",
        url
    ]
    print(f"Capturing: {output_filename} from {url}...")
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    if os.path.exists(out_path):
        print(f"  -> Saved {out_path} ({os.path.getsize(out_path)//1024} KB)")
    else:
        print(f"  -> ERROR: Failed to save {out_path}")

def main():
    base_url = "http://localhost:8080"
    
    # 1. Switch to CAM-01 (Concourse Main) with overlays off
    print("\n--- Step 1: CAM-01 Standard Dashboard ---")
    requests.post(f"{base_url}/switch_camera", json={"camera_id": "CAM-01"})
    time.sleep(2)
    capture_chrome(f"{base_url}/", "main_dashboard_live.png", 1440, 900, 3000)
    
    # 2. Toggle Optical Flow ON
    print("\n--- Step 2: Optical Flow Vectors Overlay ---")
    requests.post(f"{base_url}/toggle_flow")
    time.sleep(1.5)
    capture_chrome(f"{base_url}/", "dense_tracking_overlay.png", 1440, 900, 3000)
    requests.post(f"{base_url}/toggle_flow") # Turn off
    
    # 3. Toggle Density Heatmap ON
    print("\n--- Step 3: Gaussian Density Heatmap & 4x4 Zones ---")
    requests.post(f"{base_url}/toggle_heatmap")
    time.sleep(1.5)
    capture_chrome(f"{base_url}/", "spatial_zones_grid.png", 1440, 900, 3000)
    requests.post(f"{base_url}/toggle_heatmap") # Turn off
    
    # 4. Alerts Tab View
    print("\n--- Step 4: Incident Alerts Drawer ---")
    capture_chrome(f"{base_url}/?tab=alerts", "incident_alerts_snapshots.png", 1440, 900, 2500)
    
    # 5. Connect Feed Modal View
    print("\n--- Step 5: Add Feed / Stream Connector Modal ---")
    capture_chrome(f"{base_url}/?modal=add_feed", "add_feed_modal.png", 1440, 900, 2500)
    
    # 6. Switch to CAM-03 (Crosswalk Intersection)
    print("\n--- Step 6: CAM-03 Street-Level Crosswalk ---")
    requests.post(f"{base_url}/switch_camera", json={"camera_id": "CAM-03"})
    time.sleep(3)
    capture_chrome(f"{base_url}/", "telemetry_gauges.png", 1440, 900, 3000)
    
    # Switch back to CAM-01
    requests.post(f"{base_url}/switch_camera", json={"camera_id": "CAM-01"})
    time.sleep(2)
    
    # 7. Post-Incident Audit Report Page
    print("\n--- Step 7: Post-Incident Executive Audit Report Page ---")
    capture_chrome(f"{base_url}/report_page", "report_page_screenshot.png", 1440, 1100, 3000)
    
    print("\nAll 7 fresh screenshots captured successfully!")

if __name__ == "__main__":
    main()
