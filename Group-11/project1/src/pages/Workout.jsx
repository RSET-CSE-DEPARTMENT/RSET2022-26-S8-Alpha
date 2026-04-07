import { useState, useRef, useCallback, useEffect } from 'react';
import VideoUploadPose from '../components/VideoUploadPose';
import WebcamLiveFeed from '../components/WebcamLiveFeed';
import DataSender from '../components/DataSender';
import { createWorkoutDataSnapshot } from '../utils/poseCalculations';
import { useWebSocket } from '../context/WebSocketContext';
import '../css/Workout.css';

function Workout() {
  const { sendMessage, isConnected } = useWebSocket();
  const [videoFile, setVideoFile] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isCameraOn, setIsCameraOn] = useState(false);
  const videoUploadRef = useRef(null);
  const videoFileRef = useRef(null);
  const lastTimestampRef = useRef(null);
  const currentTimestampRef = useRef(null);
  
  // Batch storage for frames
  const frameBatchRef = useRef([]);
  const batchIntervalRef = useRef(null);
  const previousCombinedDataRef = useRef(null);
  
  // Store latest angles and gesture data
  const [trainerAngles, setTrainerAngles] = useState({});
  const [userAngles, setUserAngles] = useState({});
  const [currentGesture, setCurrentGesture] = useState(null);
  const [gestureConfidence, setGestureConfidence] = useState(0);
  const [combinedData, setCombinedData] = useState(null);

  // Update video file and ref together
  const handleVideoFileChange = (url) => {
    setVideoFile(url);
    videoFileRef.current = url;
  };

  // Handle trainer video angles update
  const handleTrainerAnglesUpdate = useCallback((angles) => {
    setTrainerAngles(angles);
  }, []);

  // Handle user webcam angles update
  const handleUserAnglesUpdate = useCallback((angles) => {
    setUserAngles(angles);
  }, []);

  // Handle gesture update from webcam
  const handleGestureUpdate = useCallback((gesture, confidence) => {
    setCurrentGesture(gesture);
    setGestureConfidence(confidence);
  }, []);

  // Setup interval to send batched frames every second
  useEffect(() => {
    if (isConnected && (isPlaying || isCameraOn)) {
      // Send batch every 1 second
      batchIntervalRef.current = setInterval(() => {
        if (frameBatchRef.current.length > 0) {
          const batch = {
            frames: frameBatchRef.current,
            frameCount: frameBatchRef.current.length,
            batchTimestamp: Date.now()
          };
          
          sendMessage(JSON.stringify(batch));
          
          // Clear the batch after sending
          frameBatchRef.current = [];
        }
      }, 1000); // Send every 1 second
    } else {
      // Clear interval when disconnected or inactive
      if (batchIntervalRef.current) {
        clearInterval(batchIntervalRef.current);
        batchIntervalRef.current = null;
        // Send any remaining frames before stopping
        if (frameBatchRef.current.length > 0 && isConnected) {
          const batch = {
            frames: frameBatchRef.current,
            frameCount: frameBatchRef.current.length,
            batchTimestamp: Date.now()
          };
          sendMessage(JSON.stringify(batch));
          frameBatchRef.current = [];
        }
      }
    }

    // Cleanup on unmount
    return () => {
      if (batchIntervalRef.current) {
        clearInterval(batchIntervalRef.current);
      }
    };
  }, [isConnected, isPlaying, isCameraOn, sendMessage]);

  // Combine all data whenever any part updates
  useEffect(() => {
    // Only process data when at least one video source is active
    const isActive = isPlaying || isCameraOn;
    
    if (!isActive) {
      // Reset timestamp when both are inactive
      currentTimestampRef.current = null;
      return;
    }
    
    // Check if we have any actual pose data to send
    const hasTrainerData = trainerAngles && Object.keys(trainerAngles).length > 0;
    const hasUserData = userAngles && Object.keys(userAngles).length > 0;
    
    if (!hasTrainerData && !hasUserData) {
      // Don't send empty data when MediaPipe hasn't detected poses yet
      return;
    }
    
    // Update timestamp only when active and have data
    currentTimestampRef.current = Date.now();
    
    const snapshot = createWorkoutDataSnapshot(
      trainerAngles,
      userAngles,
      currentGesture,
      gestureConfidence,
      currentTimestampRef.current,
      isPlaying,
      isCameraOn
    );
    setCombinedData(snapshot);
    
    // Compare with previous data to detect changes
    const currentDataString = JSON.stringify(snapshot);
    const previousDataString = previousCombinedDataRef.current 
      ? JSON.stringify(previousCombinedDataRef.current) 
      : null;
    
    const dataHasChanged = currentDataString !== previousDataString;
    
    if (!dataHasChanged && frameBatchRef.current.length > 0) {
      // Data hasn't changed - send current buffer immediately and stop accumulating
      const batch = {
        frames: frameBatchRef.current,
        frameCount: frameBatchRef.current.length,
        batchTimestamp: Date.now()
      };
      
      if (isConnected) {
        sendMessage(JSON.stringify(batch));
      }
      
      frameBatchRef.current = [];
      lastTimestampRef.current = snapshot.t;
    } else if (dataHasChanged) {
      // Data changed - add to batch
      if (isConnected && snapshot.t !== lastTimestampRef.current) {
        frameBatchRef.current.push(snapshot);
        lastTimestampRef.current = snapshot.t;
      }
    }
    
    // Store current data for next comparison
    previousCombinedDataRef.current = snapshot;
    console.log('Combined Workout Data:', JSON.stringify(snapshot, null, 2));
  }, [trainerAngles, userAngles, currentGesture, gestureConfidence, isConnected, sendMessage, isPlaying, isCameraOn]);

  // Handle gesture control for video playback
  const handleGestureControl = useCallback((gesture) => {
    // Check if video file exists using ref (to avoid stale closure)
    if (!videoFileRef.current) {
      return;
    }
    
    // Get video element from ref
    const videoElement = videoUploadRef.current?.videoElement;
    if (!videoElement) {
      return;
    }
    
    if (gesture === 'Pointing_Up' && videoElement.paused) {
      videoElement.play().then(() => {
        console.log('▶️ Playing video via gesture');
      }).catch(err => console.error('Play error:', err));
    } else if (gesture === 'Victory' && !videoElement.paused) {
      videoElement.pause();
      console.log('⏸️ Pausing video via gesture');
    }
  }, []);

  return (
    <div className="workout-container">
      <VideoUploadPose 
        ref={videoUploadRef}
        videoFile={videoFile}
        onVideoFileChange={handleVideoFileChange}
        onPlayStateChange={setIsPlaying}
        onAnglesUpdate={handleTrainerAnglesUpdate}
      />
      
      <div className="right-column">
        <WebcamLiveFeed 
          onGestureDetected={handleGestureControl}
          onAnglesUpdate={handleUserAnglesUpdate}
          onGestureUpdate={handleGestureUpdate}
          onCameraStateChange={setIsCameraOn}
        />
        
        <DataSender />
      </div>

      {/* Display combined JSON data */}
      {combinedData && (
        <div style={{
          position: 'fixed',
          top: '20px',
          left: '20px',
          background: 'rgba(0,0,0,0.9)',
          color: '#10b981',
          padding: '15px',
          borderRadius: '8px',
          maxWidth: '400px',
          maxHeight: '300px',
          overflow: 'auto',
          fontSize: '10px',
          fontFamily: 'monospace',
          zIndex: 1000
        }}>
          <div style={{ marginBottom: '10px', fontWeight: 'bold', fontSize: '12px' }}>
            Combined Data (Buffered: {frameBatchRef.current?.length || 0} frames):
          </div>
          <pre style={{ margin: 0 }}>{JSON.stringify(combinedData, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

export default Workout;
