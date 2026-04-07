# PowerShell script to download SSD MobileNet v3 model files for object detection
# Run this script from the proctoring/ directory

# Download the frozen inference graph (.pb file)
# Note: If access is denied, you may need to use a different model or source
Invoke-WebRequest -Uri "https://storage.googleapis.com/download.tensorflow.org/models/object_detection/ssd_mobilenet_v3_large_coco_2020_01_14/frozen_inference_graph.pb" -OutFile "frozen_inference_graph.pb"

# Download the model configuration (.pbtxt file)
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/opencv/opencv_extra/master/testdata/dnn/ssd_mobilenet_v3_large_coco_2020_01_14.pbtxt" -OutFile "ssd_mobilenet_v3_large_coco_2020_01_14.pbtxt"

# Download the COCO class names file
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/opencv/opencv/master/samples/data/dnn/coco.names" -OutFile "coco.names"

# Verify downloads
if (Test-Path "frozen_inference_graph.pb") { Write-Host "Downloaded frozen_inference_graph.pb" } else { Write-Host "Failed to download frozen_inference_graph.pb" }
if (Test-Path "ssd_mobilenet_v3_large_coco_2020_01_14.pbtxt") { Write-Host "Downloaded ssd_mobilenet_v3_large_coco_2020_01_14.pbtxt" } else { Write-Host "Failed to download ssd_mobilenet_v3_large_coco_2020_01_14.pbtxt" }
if (Test-Path "coco.names") { Write-Host "Downloaded coco.names" } else { Write-Host "Failed to download coco.names" }