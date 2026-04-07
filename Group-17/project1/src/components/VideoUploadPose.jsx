import { useState, useRef, useEffect, forwardRef, useImperativeHandle } from 'react';
import { useNavigate } from 'react-router-dom';
import { Pose } from '@mediapipe/pose';
import { drawConnectors, drawLandmarks } from '@mediapipe/drawing_utils';
import { POSE_CONNECTIONS } from '@mediapipe/pose';
import { calculateJointAngles } from '../utils/poseCalculations';
import AngleDisplay from './AngleDisplay';
import uploadIcon from '../assets/upload.svg';
import overlayIcon from '../assets/overlay.svg';
import backIcon from '../assets/backtodashboard.svg';
import '../css/VideoUploadPose.css';

const VideoUploadPose = forwardRef(({ videoFile, onVideoFileChange, onPlayStateChange, onAnglesUpdate }, ref) => {
  const navigate = useNavigate();
  const [isProcessing, setIsProcessing] = useState(false);
  const [showOverlay, setShowOverlay] = useState(true);
  const [angles, setAngles] = useState({});
  const [fps, setFps] = useState(0);

  const uploadVideoRef = useRef(null);
  const uploadCanvasRef = useRef(null);
  const uploadPoseRef = useRef(null);
  const uploadAnimationRef = useRef(null);
  const showOverlayRef = useRef(true);
  const frameCountRef = useRef(0);
  const fpsUpdateTimeRef = useRef(Date.now());

  // Expose video ref to parent
  useImperativeHandle(ref, () => ({
    videoElement: uploadVideoRef.current
  }));

  // Upload video pose results handler
  const onUploadVideoResults = (results) => {
    if (!uploadCanvasRef.current || !uploadVideoRef.current) return;

    const canvasCtx = uploadCanvasRef.current.getContext('2d');
    uploadCanvasRef.current.width = uploadVideoRef.current.videoWidth;
    uploadCanvasRef.current.height = uploadVideoRef.current.videoHeight;

    canvasCtx.save();
    canvasCtx.clearRect(0, 0, uploadCanvasRef.current.width, uploadCanvasRef.current.height);

    if (results.poseLandmarks) {
      const jointAngles = calculateJointAngles(results.poseLandmarks);
      setAngles(jointAngles);
      
      // Send angles to parent component
      if (onAnglesUpdate) {
        onAnglesUpdate(jointAngles);
      }

      if (showOverlayRef.current) {
        drawConnectors(canvasCtx, results.poseLandmarks, POSE_CONNECTIONS, {
          color: '#00FF00',
          lineWidth: 4
        });
        drawLandmarks(canvasCtx, results.poseLandmarks, {
          color: '#FF0000',
          lineWidth: 2,
          radius: 6
        });
      }
    }

    canvasCtx.restore();
  };

  // Upload video detection loop
  const detectUploadVideoPose = async () => {
    if (uploadVideoRef.current && !uploadVideoRef.current.paused && !uploadVideoRef.current.ended && uploadPoseRef.current) {
      console.log('📹 Video pose detection running');
      await uploadPoseRef.current.send({ image: uploadVideoRef.current });
      
      // Calculate FPS
      frameCountRef.current++;
      const now = Date.now();
      const elapsed = now - fpsUpdateTimeRef.current;
      
      if (elapsed >= 1000) {
        const currentFps = Math.round((frameCountRef.current * 1000) / elapsed);
        setFps(currentFps);
        frameCountRef.current = 0;
        fpsUpdateTimeRef.current = now;
      }
      
      uploadAnimationRef.current = requestAnimationFrame(detectUploadVideoPose);
    } else {
      console.log('⚠️ Video pose detection stopped');
      setIsProcessing(false);
      onPlayStateChange?.(false);
    }
  };

  // Upload video handlers
  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file && file.type.startsWith('video/')) {
      const url = URL.createObjectURL(file);
      onVideoFileChange(url);
      setIsProcessing(false);
    } else {
      alert('Please select a valid video file');
    }
  };

  const handleVideoPlay = () => {
    console.log('🎬 handleVideoPlay called');
    onPlayStateChange?.(true);
    setIsProcessing(true);
    frameCountRef.current = 0;
    fpsUpdateTimeRef.current = Date.now();
    if (uploadPoseRef.current) {
      console.log('Starting video pose detection from handleVideoPlay');
      detectUploadVideoPose();
    } else {
      console.log('⚠️ Upload pose ref not ready');
    }
  };

  const handleVideoPause = () => {
    onPlayStateChange?.(false);
    setIsProcessing(false);
    if (uploadAnimationRef.current) {
      cancelAnimationFrame(uploadAnimationRef.current);
    }
  };

  const toggleOverlay = () => {
    setShowOverlay(!showOverlay);
    showOverlayRef.current = !showOverlay;
  };

  // Initialize upload pose model
  useEffect(() => {
    const initializeUploadPose = async () => {
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

        pose.onResults(onUploadVideoResults);
        uploadPoseRef.current = pose;
        console.log('Upload video pose model loaded');
      } catch (error) {
        console.error('Error loading upload video pose model:', error);
      }
    };

    initializeUploadPose();

    return () => {
      if (uploadAnimationRef.current) {
        cancelAnimationFrame(uploadAnimationRef.current);
      }
      if (uploadPoseRef.current) {
        uploadPoseRef.current.close();
      }
    };
  }, []);

  return (
    <div className="video-upload-section">
      <div className="upload-controls">
        <button 
          onClick={() => navigate('/dashboard')} 
          className="back-to-dashboard-btn"
          title="Back to Dashboard"
        >
          <img src={backIcon} alt="back" style={{ width: '20px', height: '20px' }} />
        </button>
        <label htmlFor="video-upload" className="upload-label">
          <img src={uploadIcon} alt="upload" style={{ width: '16px', height: '16px', marginRight: '8px' }} />
          Choose Video
        </label>
        <input
          id="video-upload"
          type="file"
          accept="video/*"
          onChange={handleFileUpload}
          className="file-input"
        />
        {videoFile && (
          <>
            <button 
              onClick={toggleOverlay} 
              className={`control-btn ${showOverlay ? 'active' : ''}`}
            >
              <img src={overlayIcon} alt="overlay" style={{ width: '16px', height: '16px', marginRight: '8px' }} />
              {showOverlay ? 'Hide Overlay' : 'Show Overlay'}
            </button>
            {isProcessing && (
              <div className="fps-display">
                {fps} FPS
              </div>
            )}
          </>
        )}
      </div>

      <div className="video-content">
        <div className="canvas-container">
          {videoFile ? (
            <>
              <video
                ref={uploadVideoRef}
                src={videoFile}
                className="video-element"
                controls
                onPlay={handleVideoPlay}
                onPause={handleVideoPause}
                onEnded={() => {
                  onPlayStateChange?.(false);
                  setIsProcessing(false);
                }}
              />
              <canvas
                ref={uploadCanvasRef}
                className="output-canvas"
              />
            </>
          ) : (
            <div className="video-placeholder">
              <img src={uploadIcon} alt="upload" className="upload-icon" />
              <div className="upload-text">No video selected</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
});

VideoUploadPose.displayName = 'VideoUploadPose';

export default VideoUploadPose;
