import { useState, useRef, useEffect } from 'react';
import { Pose } from '@mediapipe/pose';
import { drawConnectors, drawLandmarks } from '@mediapipe/drawing_utils';
import { POSE_CONNECTIONS } from '@mediapipe/pose';
import { GestureRecognizer, FilesetResolver } from '@mediapipe/tasks-vision';
import { calculateJointAngles } from '../utils/poseCalculations';
import AngleDisplay from './AngleDisplay';
import GestureOverlay from './GestureOverlay';
import cameraIcon from '../assets/cameraicon.svg';
import overlayIcon from '../assets/overlay.svg';
import '../css/WebcamLiveFeed.css';

function WebcamLiveFeed({ onGestureDetected, onAnglesUpdate, onGestureUpdate, onCameraStateChange }) {
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [showWebcamOverlay, setShowWebcamOverlay] = useState(true);
  const [webcamAngles, setWebcamAngles] = useState({});
  const [poseModelLoaded, setPoseModelLoaded] = useState(false);
  const [gestureModelLoaded, setGestureModelLoaded] = useState(false);
  const [currentGesture, setCurrentGesture] = useState(null);
  const [gestureConfidence, setGestureConfidence] = useState(0);

  const webcamVideoRef = useRef(null);
  const webcamCanvasRef = useRef(null);
  const webcamStreamRef = useRef(null);
  const webcamPoseRef = useRef(null);
  const webcamAnimationRef = useRef(null);
  const gestureRecognizerRef = useRef(null);
  const gestureAnimationRef = useRef(null);
  const showWebcamOverlayRef = useRef(true);
  const isCameraOnRef = useRef(false);
  const lastGestureRef = useRef(null);
  const gestureTimeoutRef = useRef(null);

  // Webcam pose results handler
  const onWebcamPoseResults = (results) => {
    if (!webcamCanvasRef.current || !webcamVideoRef.current) return;

    const canvasElement = webcamCanvasRef.current;
    const canvasCtx = canvasElement.getContext('2d');
    
    canvasElement.width = 640;
    canvasElement.height = 480;

    canvasCtx.save();
    canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);

    if (results.poseLandmarks) {
      if (showWebcamOverlayRef.current) {
        drawConnectors(canvasCtx, results.poseLandmarks, POSE_CONNECTIONS, {
          color: '#10b981',
          lineWidth: 4
        });
        drawLandmarks(canvasCtx, results.poseLandmarks, {
          color: '#ef4444',
          lineWidth: 2,
          radius: 6
        });
      }

      const landmarks = results.poseLandmarks;
      const webcamJointAngles = calculateJointAngles(landmarks);
      setWebcamAngles(webcamJointAngles);
      
      // Send angles to parent component
      if (onAnglesUpdate) {
        onAnglesUpdate(webcamJointAngles);
      }
    }

    canvasCtx.restore();
  };

  // Webcam pose detection loop
  const detectWebcamPose = async () => {
    if (webcamVideoRef.current && webcamPoseRef.current && isCameraOnRef.current) {
      await webcamPoseRef.current.send({ image: webcamVideoRef.current });
      webcamAnimationRef.current = requestAnimationFrame(detectWebcamPose);
    }
  };

  // Gesture detection loop
  const detectGesture = async () => {
    if (webcamVideoRef.current && gestureRecognizerRef.current && isCameraOnRef.current) {
      const nowInMs = Date.now();
      
      try {
        const results = await gestureRecognizerRef.current.recognizeForVideo(
          webcamVideoRef.current,
          nowInMs
        );
        
        if (results.gestures && results.gestures.length > 0) {
          const gesture = results.gestures[0][0];
          console.log('👋 Gesture detected:', gesture.categoryName, 'confidence:', gesture.score);
          setCurrentGesture(gesture.categoryName);
          setGestureConfidence(gesture.score);
          
          // Send gesture data to parent
          if (onGestureUpdate) {
            onGestureUpdate(gesture.categoryName, gesture.score);
          }
          
          // Call parent callback with gesture
          if (lastGestureRef.current !== gesture.categoryName) {
            lastGestureRef.current = gesture.categoryName;
            
            if (gestureTimeoutRef.current) {
              clearTimeout(gestureTimeoutRef.current);
            }
            
            onGestureDetected?.(gesture.categoryName);
            
            gestureTimeoutRef.current = setTimeout(() => {
              lastGestureRef.current = null;
            }, 1000);
          }
        } else {
          setCurrentGesture(null);
          setGestureConfidence(0);
          
          // Clear gesture data in parent
          if (onGestureUpdate) {
            onGestureUpdate(null, 0);
          }
        }
      } catch (error) {
        console.error('Error detecting gesture:', error);
      }
      
      gestureAnimationRef.current = requestAnimationFrame(detectGesture);
    }
  };

  // Webcam handlers
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 },
        audio: false
      });
      
      if (webcamVideoRef.current) {
        webcamVideoRef.current.srcObject = stream;
        webcamStreamRef.current = stream;
        setIsCameraOn(true);
        isCameraOnRef.current = true;
        if (onCameraStateChange) onCameraStateChange(true);
        
        webcamVideoRef.current.onloadedmetadata = () => {
          if (webcamPoseRef.current && poseModelLoaded) {
            detectWebcamPose();
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
    if (webcamAnimationRef.current) {
      cancelAnimationFrame(webcamAnimationRef.current);
      webcamAnimationRef.current = null;
    }
    if (gestureAnimationRef.current) {
      cancelAnimationFrame(gestureAnimationRef.current);
      gestureAnimationRef.current = null;
    }
    
    if (webcamStreamRef.current) {
      webcamStreamRef.current.getTracks().forEach(track => track.stop());
      webcamStreamRef.current = null;
    }
    if (webcamVideoRef.current) {
      webcamVideoRef.current.srcObject = null;
    }
    
    setIsCameraOn(false);
    isCameraOnRef.current = false;
    if (onCameraStateChange) onCameraStateChange(false);
    setWebcamAngles({});
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

  // Initialize models
  useEffect(() => {
    const initializeWebcamPose = async () => {
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

        pose.onResults(onWebcamPoseResults);
        webcamPoseRef.current = pose;
        setPoseModelLoaded(true);
        console.log('Webcam pose model loaded');
      } catch (error) {
        console.error('Error loading webcam pose model:', error);
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
          numHands: 2
        });
        
        gestureRecognizerRef.current = gestureRecognizer;
        setGestureModelLoaded(true);
        console.log('Gesture recognition model loaded');
      } catch (error) {
        console.error('Error loading gesture recognizer:', error);
      }
    };

    initializeWebcamPose();
    initializeGesture();

    return () => {
      if (webcamAnimationRef.current) {
        cancelAnimationFrame(webcamAnimationRef.current);
      }
      if (gestureAnimationRef.current) {
        cancelAnimationFrame(gestureAnimationRef.current);
      }
      if (webcamPoseRef.current) {
        webcamPoseRef.current.close();
      }
      if (gestureRecognizerRef.current) {
        gestureRecognizerRef.current.close();
      }
      stopCamera();
    };
  }, []);

  return (
    <div className="webcam-section">
      <div className="webcam-header">
        <div className="webcam-header-left">
          <img src={cameraIcon} alt="camera" className="webcam-icon" />
          <span className="webcam-title">Your Camera</span>
          {(!poseModelLoaded || !gestureModelLoaded) && <span className="webcam-status">Loading models...</span>}
        </div>
        <div className="webcam-header-right">
          <button 
            onClick={() => {
              setShowWebcamOverlay(!showWebcamOverlay);
              showWebcamOverlayRef.current = !showWebcamOverlay;
            }}
            className={`webcam-toggle-btn ${showWebcamOverlay ? 'active' : ''}`}
            disabled={!isCameraOn}
            title="Toggle overlay"
          >
            <img src={overlayIcon} alt="overlay" className="webcam-btn-icon" />
          </button>
          <button 
            onClick={toggleCamera}
            className={`webcam-toggle-btn ${isCameraOn ? 'active' : ''}`}
            disabled={!poseModelLoaded || !gestureModelLoaded}
          >
            <img src={cameraIcon} alt="camera" className="webcam-btn-icon" />
          </button>
        </div>
      </div>

      <div className="webcam-video-wrapper">
        <video
          ref={webcamVideoRef}
          autoPlay
          playsInline
          muted
          disablePictureInPicture
          disableRemotePlayback
          className="webcam-video"
          style={{ display: isCameraOn ? 'block' : 'none' }}
          onPause={(e) => {
            // Prevent video from pausing when scrolling
            if (isCameraOnRef.current && e.target.srcObject) {
              e.target.play().catch(err => console.log('Video play prevented:', err));
            }
          }}
        />
        
        <canvas
          ref={webcamCanvasRef}
          className="webcam-canvas"
          style={{ display: isCameraOn ? 'block' : 'none' }}
        />
        
        {!isCameraOn && (
          <div className="webcam-placeholder">
            <div>User Video</div>
            {poseModelLoaded && gestureModelLoaded && <div className="webcam-ready">Ready</div>}
          </div>
        )}
      </div>
    </div>
  );
}

export default WebcamLiveFeed;
