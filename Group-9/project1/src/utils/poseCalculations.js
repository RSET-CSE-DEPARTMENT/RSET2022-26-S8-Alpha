// Calculate angle between three points with weighted confidence
export const calculateAngle = (a, b, c) => {
  // Check if visibility property exists (some landmarks might not have it)
  const aVis = a.visibility ?? 1.0;
  const bVis = b.visibility ?? 1.0;
  const cVis = c.visibility ?? 1.0;
  
  // Confidence: use minimum value among the 3 points
  const angleConfidence = Math.min(aVis, bVis, cVis);
  
  const radians = Math.atan2(c.y - b.y, c.x - b.x) - Math.atan2(a.y - b.y, a.x - b.x);
  let angle = Math.abs((radians * 180.0) / Math.PI);
  if (angle > 180.0) {
    angle = 360 - angle;
  }
  
  return [Math.round(angle), Math.round(angleConfidence * 100)];
};

// Calculate all joint angles
export const calculateJointAngles = (landmarks) => {
  if (!landmarks || landmarks.length < 33) return {};

  return {
    ls: calculateAngle(landmarks[23], landmarks[11], landmarks[13]),
    le: calculateAngle(landmarks[11], landmarks[13], landmarks[15]),
    lw: calculateAngle(landmarks[13], landmarks[15], landmarks[19]),
    rs: calculateAngle(landmarks[24], landmarks[12], landmarks[14]),
    re: calculateAngle(landmarks[12], landmarks[14], landmarks[16]),
    rw: calculateAngle(landmarks[14], landmarks[16], landmarks[20]),
    lh: calculateAngle(landmarks[11], landmarks[23], landmarks[25]),
    lk: calculateAngle(landmarks[23], landmarks[25], landmarks[27]),
    la: calculateAngle(landmarks[25], landmarks[27], landmarks[31]),
    rh: calculateAngle(landmarks[12], landmarks[24], landmarks[26]),
    rk: calculateAngle(landmarks[24], landmarks[26], landmarks[28]),
    ra: calculateAngle(landmarks[26], landmarks[28], landmarks[32]),
    lsp: calculateAngle(landmarks[11], landmarks[23], landmarks[25]),
    rsp: calculateAngle(landmarks[12], landmarks[24], landmarks[26]),
    n: calculateAngle(landmarks[11], landmarks[0], landmarks[12])
  };
};

// Create combined workout data snapshot
export const createWorkoutDataSnapshot = (trainerAngles, userAngles, gesture, gestureConfidence, timestamp, isPlaying, isCameraOn) => {
  const data = {
    t: timestamp || Date.now()
  };

  // Add trainer angles with tr_ prefix
  if (trainerAngles && Object.keys(trainerAngles).length > 0) {
    Object.entries(trainerAngles).forEach(([key, value]) => {
      data[`tr_${key}`] = value;
    });
  }

  // Add user angles with u_ prefix
  if (userAngles && Object.keys(userAngles).length > 0) {
    Object.entries(userAngles).forEach(([key, value]) => {
      data[`u_${key}`] = value;
    });
  }

  // Add gesture (just the name, no confidence)
  data.gest = gesture || null;
  
  // Add isPlaying state for pause detection
  data.isPlaying = isPlaying;

  // Add isCameraOn state for camera status detection
  data.isCameraOn = isCameraOn;

  return data;
};
