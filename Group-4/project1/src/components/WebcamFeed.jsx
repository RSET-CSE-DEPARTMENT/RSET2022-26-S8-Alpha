import { useState, useRef, useEffect } from 'react';
import { Pose } from '@mediapipe/pose';
import { drawConnectors, drawLandmarks } from '@mediapipe/drawing_utils';
import { POSE_CONNECTIONS } from '@mediapipe/pose';
import { GestureRecognizer, FilesetResolver } from '@mediapipe/tasks-vision';
import cameraIcon from '../assets/cameraicon.svg';
import '../styles/WebcamFeed.css';

function WebcamFeed() {
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [showOverlay, setShowOverlay] = useState(true);
  const [jointAngles, setJointAngles] = useState({});
  const [modelLoaded, setModelLoaded] = useState(false);
  const [gestureModelLoaded, setGestureModelLoaded] = useState(false);
  const [currentGesture, setCurrentGesture] = useState(null);
  const [gestureConfidence, setGestureConfidence] = useState(0);
  
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const canvasRef = useRef(null);
  const poseRef = useRef(null);
  const gestureRecognizerRef = useRef(null);
  const animationRef = useRef(null);
  const gestureAnimationRef = useRef(null);
  const showOverlayRef = useRef(true);
  const isCameraOnRef = useRef(false);

  // Calculate angle between three points
  const calculateAngle = (a, b, c) => {
    const radians = Math.atan2(c.y - b.y, c.x - b.x) - Math.atan2(a.y - b.y, a.x - b.x);
    let angle = Math.abs((radians * 180.0) / Math.PI);
    if (angle > 180.0) {
      angle = 360 - angle;
    }
    return angle.toFixed(2);
  };

  // Process pose results
  const onResults = (results) => {
    if (!canvasRef.current || !videoRef.current) return;

    const canvasElement = canvasRef.current;
    const canvasCtx = canvasElement.getContext('2d');
    
    // Set canvas dimensions to match video
    canvasElement.width = 640;
    canvasElement.height = 480;

    // Clear canvas
    canvasCtx.save();
    canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);

    if (results.poseLandmarks) {
      // Only draw if overlay is enabled (use ref for current value)
      if (showOverlayRef.current) {
        // Draw connections
        drawConnectors(canvasCtx, results.poseLandmarks, POSE_CONNECTIONS, {
          color: '#10b981',
          lineWidth: 4
        });
        
        // Draw landmarks
        drawLandmarks(canvasCtx, results.poseLandmarks, {
          color: '#ef4444',
          lineWidth: 2,
          radius: 6
        });
      }

      // Always calculate joint angles (even when overlay is hidden)
      const landmarks = results.poseLandmarks;
      const angles = {
        // Left arm
        leftShoulder: calculateAngle(landmarks[13], landmarks[11], landmarks[23]),
        leftElbow: calculateAngle(landmarks[11], landmarks[13], landmarks[15]),
        leftWrist: calculateAngle(landmarks[13], landmarks[15], landmarks[17]),
        
        // Right arm
        rightShoulder: calculateAngle(landmarks[14], landmarks[12], landmarks[24]),
        rightElbow: calculateAngle(landmarks[12], landmarks[14], landmarks[16]),
        rightWrist: calculateAngle(landmarks[14], landmarks[16], landmarks[18]),
        
        // Left leg
        leftHip: calculateAngle(landmarks[11], landmarks[23], landmarks[25]),
        leftKnee: calculateAngle(landmarks[23], landmarks[25], landmarks[27]),
        leftAnkle: calculateAngle(landmarks[25], landmarks[27], landmarks[31]),
        
        // Right leg
        rightHip: calculateAngle(landmarks[12], landmarks[24], landmarks[26]),
        rightKnee: calculateAngle(landmarks[24], landmarks[26], landmarks[28]),
        rightAnkle: calculateAngle(landmarks[26], landmarks[28], landmarks[32]),
        
        // Spine and neck
        leftSpine: calculateAngle(landmarks[11], landmarks[23], landmarks[25]),
        rightSpine: calculateAngle(landmarks[12], landmarks[24], landmarks[26]),
        neck: calculateAngle(landmarks[11], landmarks[0], landmarks[12])
      };
      
      setJointAngles(angles);
    }

    canvasCtx.restore();
  };

  // Pose detection loop
  const detectPose = async () => {
    if (videoRef.current && poseRef.current && isCameraOnRef.current) {
      console.log('🦴 Pose detection running');
      await poseRef.current.send({ image: videoRef.current });
      animationRef.current = requestAnimationFrame(detectPose);
    } else {
      console.log('⚠️ Pose detection stopped - videoRef:', !!videoRef.current, 'poseRef:', !!poseRef.current, 'isCameraOn:', isCameraOnRef.current);
    }
  };

  // Gesture detection loop
  const detectGesture = async () => {
    if (videoRef.current && gestureRecognizerRef.current && isCameraOnRef.current) {
      const nowInMs = Date.now();
      
      try {
        const results = await gestureRecognizerRef.current.recognizeForVideo(
          videoRef.current,
          nowInMs
        );
        
        if (results.gestures && results.gestures.length > 0) {
          const gesture = results.gestures[0][0];
          setCurrentGesture(gesture.categoryName);
          setGestureConfidence(gesture.score);
        } else {
          setCurrentGesture(null);
          setGestureConfidence(0);
        }
      } catch (error) {
        console.error('Error detecting gesture:', error);
      }
      
      gestureAnimationRef.current = requestAnimationFrame(detectGesture);
    }
  };

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 },
        audio: false
      });
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        streamRef.current = stream;
        setIsCameraOn(true);
        isCameraOnRef.current = true;
        
        // Wait for video to be ready then start detection
        videoRef.current.onloadedmetadata = () => {
          if (poseRef.current && modelLoaded) {
            detectPose();
          }
          if (gestureRecognizerRef.current && gestureModelLoaded) {
            detectGesture();
          }
        };
      }
    } catch (err) {
      console.error('Error accessing camera:', err);
      alert('Failed to access camera');
    }
  };

  const stopCamera = () => {
    // Cancel animation frames
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
    if (gestureAnimationRef.current) {
      cancelAnimationFrame(gestureAnimationRef.current);
      gestureAnimationRef.current = null;
    }
    
    // Stop camera stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    
    setIsCameraOn(false);
    isCameraOnRef.current = false;
    setJointAngles({});
    setCurrentGesture(null);
    setGestureConfidence(0);
  };

  const toggleCamera = () => {
    if (isCameraOn) {
      stopCamera();
    } else {
      startCamera();
    }
  };

  // Initialize pose model (keep loaded in memory)
  useEffect(() => {
    const initializePose = async () => {
      try {
        const pose = new Pose({
          locateFile: (file) => {
            return `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`;
          }
        });

        pose.setOptions({
          modelComplexity: 1,
          smoothLandmarks: true,
          enableSegmentation: false,
          minDetectionConfidence: 0.5,
          minTrackingConfidence: 0.5
        });

        pose.onResults(onResults);
        poseRef.current = pose;
        setModelLoaded(true);
        console.log('Pose model loaded successfully');
      } catch (error) {
        console.error('Error loading pose model:', error);
        alert('Failed to load pose detection model');
      }
    };

    const initializeGesture = async () => {
      try {
        const vision = await FilesetResolver.forVisionTasks(
          "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm"
        );
        
        const gestureRecognizer = await GestureRecognizer.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath: "/gesture_recognizer.task",
            delegate: "GPU"
          },
          runningMode: "VIDEO",
          numHands: 1
        });
        
        gestureRecognizerRef.current = gestureRecognizer;
        setGestureModelLoaded(true);
        console.log('Gesture recognition model loaded successfully');
      } catch (error) {
        console.error('Error loading gesture recognizer:', error);
      }
    };

    initializePose();
    initializeGesture();

    return () => {
      // Cleanup on component unmount
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      if (gestureAnimationRef.current) {
        cancelAnimationFrame(gestureAnimationRef.current);
      }
      if (poseRef.current) {
        poseRef.current.close();
      }
      if (gestureRecognizerRef.current) {
        gestureRecognizerRef.current.close();
      }
      stopCamera();
    };
  }, []);

  return (
    <div className="webcam-container">
      {/* Header */}
      <div className="webcam-header">
        <div className="webcam-header-left">
          <img src={cameraIcon} alt="camera" className="webcam-icon" />
          <span className="webcam-title">Your Camera</span>
          {(!modelLoaded || !gestureModelLoaded) && <span className="webcam-status">Loading models...</span>}
        </div>
        <div className="webcam-header-right">
          <button 
            onClick={() => {
              setShowOverlay(!showOverlay);
              showOverlayRef.current = !showOverlay;
            }}
            className={`webcam-toggle-btn ${showOverlay ? 'active' : ''}`}
            disabled={!isCameraOn}
            title="Toggle overlay"
          >
            👁️
          </button>
          <button 
            onClick={toggleCamera}
            className={`webcam-toggle-btn ${isCameraOn ? 'active' : ''}`}
            disabled={!modelLoaded || !gestureModelLoaded}
          >
            <img src={cameraIcon} alt="camera" className="webcam-btn-icon" />
          </button>
        </div>
      </div>

      {/* Video Container */}
      <div className="webcam-video-wrapper">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="webcam-video"
          style={{ display: isCameraOn ? 'block' : 'none' }}
        />
        
        <canvas
          ref={canvasRef}
          className="webcam-canvas"
          style={{ display: isCameraOn ? 'block' : 'none' }}
        />
        
        {!isCameraOn && (
          <div className="webcam-placeholder">
            <div>User Video</div>
            {modelLoaded && gestureModelLoaded && <div className="webcam-ready">Ready</div>}
          </div>
        )}

        {/* Gesture Display Overlay */}
        {isCameraOn && currentGesture && (
          <div className="gesture-overlay">
            <div className="gesture-name">{currentGesture}</div>
            <div className="gesture-confidence">{(gestureConfidence * 100).toFixed(0)}%</div>
          </div>
        )}
      </div>

      {/* Joint Angles Display */}
      {isCameraOn && Object.keys(jointAngles).length > 0 && (
        <div className="webcam-angles-container">
          <div className="webcam-angles-header">Joint Angles (degrees)</div>
          <div className="webcam-angles-content">
            <pre>{JSON.stringify(jointAngles, null, 2)}</pre>
          </div>
        </div>
      )}

      {/* Gesture Information */}
      {isCameraOn && (
        <div className="webcam-angles-container">
          <div className="webcam-angles-header">Current Gesture</div>
          <div className="webcam-angles-content">
            <pre>{JSON.stringify({
              gesture: currentGesture || 'No gesture detected',
              confidence: currentGesture ? `${(gestureConfidence * 100).toFixed(2)}%` : 'N/A'
            }, null, 2)}</pre>
          </div>
        </div>
      )}
    </div>
  );
}

export default WebcamFeed;
